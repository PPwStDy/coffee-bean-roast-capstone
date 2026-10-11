"""Azure implementation of the complete course interface."""
import re
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from cloudlayer.base import CloudAdapter
from cloudlayer.cli import az
from cloudlayer.config import settings


class AzureCloudAdapter(CloudAdapter):
    def __init__(self, config=None):
        self.config = config or settings()
        self.group = self.config["PROJECT_ID"]
        self.workspace = self.config["AZURE_ML_WORKSPACE"]
        self.ml_group = self.config["AZURE_ML_RESOURCE_GROUP"]

    def _blob(self, uri):
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobClient
        if not uri.startswith(self.config["BLOB_URI"].rstrip("/") + "/"):
            raise ValueError("Object is outside the configured storage root")
        return BlobClient.from_blob_url(uri, credential=DefaultAzureCredential())

    def upload(self, local_path, key):
        if key.startswith("/") or ".." in Path(key).parts:
            raise ValueError("Object key must stay inside the storage root")
        uri = self.config["BLOB_URI"].rstrip("/") + "/" + key
        with open(local_path, "rb") as stream:
            self._blob(uri).upload_blob(stream, overwrite=True)
        return uri

    def download(self, uri, local_path):
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            self._blob(uri).download_blob().readinto(stream)

    def push_image(self, local_tag):
        registry = self.config["CONTAINER_REGISTRY"].split("/")[0]
        name = registry.split(".")[0]
        tag = local_tag.rsplit(":", 1)[-1]
        remote = f"{registry}/coffee-roast:{tag}"
        az("acr", "login", "--name", name, parse=False)
        subprocess.run(["docker", "tag", local_tag, remote], check=True)
        subprocess.run(["docker", "push", remote], check=True)
        metadata = az("acr", "repository", "show", "--name", name, "--image", f"coffee-roast:{tag}")
        return f"{registry}/coffee-roast@{metadata['digest']}"

    def submit_training(self, image_uri, args):
        # Inputs must be immutable registered assets or versioned datastore URIs.
        required = {"data_uri", "code", "git_commit", "dataset_revision"}
        if not required <= args.keys():
            raise ValueError(f"Training requires {sorted(required)}")
        import yaml
        spec = {
            "$schema": "https://azuremlschemas.azureedge.net/latest/commandJob.schema.json",
            "type": "command", "display_name": "capstone-roast-training", "code": str(Path(args["code"]).resolve()),
            "command": "python -m src.train --epochs 20 --batch-size 32 --seed 42",
            "environment": {"image": image_uri}, "compute": self.config["TRAINING_TARGET"],
            "inputs": {"data": {"type": "uri_folder", "path": args["data_uri"], "mode": "download"}},
            "environment_variables": {"DATA_DIR": "${{inputs.data}}", "GITHUB_SHA": args["git_commit"],
                                      "DATASET_REVISION": args["dataset_revision"]},
            "outputs": {"release": {"type": "uri_folder", "mode": "upload"}},
            "tags": {"course": "itcs355", "student": "6688218", "lab": "capstone"},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "job.yml"
            path.write_text(yaml.safe_dump(spec))
            result = az("ml", "job", "create", "--file", path, "--workspace-name", self.workspace,
                        "--resource-group", self.ml_group)
        return result["name"]

    def wait_training(self, job_id):
        deadline = time.monotonic() + 6 * 3600
        while time.monotonic() < deadline:
            job = az("ml", "job", "show", "--name", job_id, "--workspace-name", self.workspace,
                     "--resource-group", self.ml_group)
            if job["status"] == "Completed":
                return job
            if job["status"] in {"Failed", "Canceled", "NotResponding"}:
                raise RuntimeError(f"Training {job_id} ended with {job['status']}")
            time.sleep(30)
        raise TimeoutError(f"Training {job_id} exceeded six hours")

    def register_model(self, model_uri, name):
        result = az("ml", "model", "create", "--name", name, "--path", model_uri, "--type", "custom_model",
                    "--workspace-name", self.workspace, "--resource-group", self.ml_group,
                    "--tags", "course=itcs355", "student=6688218", "lab=capstone")
        return result["id"]

    def deploy(self, model_ref, endpoint, instance):
        if instance != "2cpu-4Gi":
            raise ValueError("Approved serving allocation is 2cpu-4Gi")
        if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", model_ref):
            raise ValueError("Deployment requires an immutable image digest")
        from cloudlayer.release import deploy_candidate
        return deploy_candidate(self.config, model_ref, endpoint)

    def invoke(self, endpoint, payload):
        url = endpoint if endpoint.startswith("https://") else self.config["ENDPOINT_URL"]
        with httpx.Client(timeout=180) as client:
            response = client.post(url.rstrip("/") + "/predict/base64", json=payload)
            response.raise_for_status()
            return response.json()

    def emit_metric(self, name, value, unit):
        # Azure Monitor custom metrics REST operation uses an ARM token; no shared key.
        if unit not in {"Count", "Milliseconds", "Seconds", "Bytes"}:
            raise ValueError("Unsupported metric unit")
        from azure.identity import DefaultAzureCredential
        from datetime import datetime, timezone
        resource = self.config["METRICS_RESOURCE_ID"]
        token = DefaultAzureCredential().get_token("https://monitoring.azure.com/.default").token
        body = {"time": datetime.now(timezone.utc).isoformat(), "data": {
            "baseData": {"metric": name, "namespace": self.config["METRICS_NAMESPACE"],
                         "dimNames": ["unit"], "series": [{"dimValues": [unit], "min": value,
                         "max": value, "sum": value, "count": 1}]}}}
        response = httpx.post(f"https://{self.config['REGION']}.monitoring.azure.com{resource}/metrics",
                              headers={"Authorization": f"Bearer {token}"}, json=body, timeout=30)
        response.raise_for_status()

    def teardown(self, tags):
        from cloudlayer.teardown import teardown
        return teardown(self.config, tags)
