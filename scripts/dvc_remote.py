"""Configure the shared DVC remote using the environment contract and identity authentication."""
import subprocess
from urllib.parse import urlsplit

from cloudlayer.config import settings


def main():
    config = settings()
    parsed = urlsplit(config["BLOB_URI"])
    if parsed.scheme != "https" or not parsed.netloc.endswith(".blob.core.windows.net"):
        raise ValueError("BLOB_URI must be an Azure Blob HTTPS container root")
    account = parsed.netloc.split(".")[0]
    remote = "azure://" + parsed.path.strip("/") + "/dvc"
    for args in [
        ["remote", "add", "--force", "--default", "shared", remote],
        ["remote", "modify", "shared", "account_name", account],
        ["remote", "modify", "shared", "allow_anonymous_login", "false"],
    ]:
        subprocess.run([".venv/bin/dvc", *args], check=True)


if __name__ == "__main__":
    main()
