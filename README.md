# ITCS355 Capstone: Coffee Bean Roast Classification API

The capstone now uses **Iteration4 Swin-T** and predicts **Dark, Green, Light, Medium**, in that exact class order. Input is an RGB coffee bean image resized to 224 × 224 with ImageNet normalization. The API retains the optical glare/occlusion guard, Prometheus metrics, and local monitoring stack.

This is a change from the submitted defect-grading proposal. A [revised proposal draft](reports/proposal_revision_roast.md) is included; obtain the instructor's approval for the roast-classification scope. The original proposal and previously generated presentation/report files describe the earlier scope.

## Dataset audit

The supplied dataset has 1,600 readable RGB PNGs: 1,200 train and 400 test, balanced across four classes. **Every one of the 400 test images is an exact pixel duplicate of an image in the original training folder.** There are only 1,194 unique images, with no conflicting labels.

The saved 99.75% accuracy and macro F1 are historical results from that overlapping split. They cannot establish performance on unseen images. Splitting the images again does not remove contamination from the already trained checkpoint.

The prepared DVC dataset removes 406 duplicate copies and uses seeded, stratified 70/15/15 splits:

| Split | Images |
|---|---:|
| Train | 835 |
| Validation | 178 |
| Test | 181 |

The seed, all original filenames, content hashes, duplicate groups, and new split assignments are in `data/coffee_bean_roast/manifest.json`. An audit copy is in `reports/dataset_audit.json`. The loader rejects duplicate pixels within or across splits.

**The new dataset's source and license are unconfirmed.** The old Roboflow CC BY 4.0 attribution does not apply to this dataset. Confirm its license before redistribution.

## Restore and use the imported model

The local checkpoint is `models/iteration4_swin.pth`; its DVC pointer is checked in alongside the prepared dataset pointer. Original Iteration4 training code and its saved evaluation summary are retained under `provenance/iteration4/`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.in
# Configure your shared DVC remote and credentials, then:
make dvc-pull
python -m src.import_iteration4 --register
make export
make serve
```

No shared DVC remote has been configured or pushed by this local migration. CI needs `DVC_REMOTE_URL` and matching credentials. For S3, provide `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`; for GCS, provide `GCP_SERVICE_ACCOUNT_JSON`. Push both the dataset and model pointers to the chosen remote before running CI.

To import from your own source paths:

```bash
python -m src.prepare_roast_data --source /path/to/DL_FinalProject/dataset
python -m src.import_iteration4 --source-dir /path/to/DL_FinalProject/Iteration4
dvc add data/coffee_bean_roast models/iteration4_swin.pth
python -m src.import_iteration4 --register
make export
```

Preparation refuses to overwrite an existing dataset. Use the existing DVC data or specify a new `--destination`. The original deep-learning project is not modified.

## Retrain for an independent evaluation

```bash
make train EPOCHS=20
```

This starts Swin-T from ImageNet weights, uses the corrected splits, color-preserving Iteration4 augmentation, label smoothing, AdamW, and OneCycleLR. It **does not initialize from the contaminated imported checkpoint**. It logs the seed, library versions, DVC hash, metrics, checkpoint, and registered model to MLflow.

Retraining has not been run during this migration. The prepared holdout is independent of this future training run, subject to unmeasured near-duplicate or shared-source correlations.

## Serving and monitoring

```bash
make monitor-up
make trigger-alert
docker compose logs -f webhook-sink
make monitor-down
```

API: [http://localhost:8080/docs](http://localhost:8080/docs). Grafana: [http://localhost:3000](http://localhost:3000). Prometheus: [http://localhost:9090](http://localhost:9090).

- `POST /predict`: raw image bytes.
- `POST /predict/base64`: JSON with an `image_base64` field.
- `GET /health`, `GET /ready`, `GET /metrics`: operational endpoints.
- Near-uniform frames return 422 and increment `coffee_anomaly_frames_total`.

The runtime verifies artifact hashes, architecture, preprocessing, and class order against `reports/model_metadata.json`; stale defect artifacts cannot be served with roast labels. Docker serves quantized ONNX on CPU; TorchScript is available locally when PyTorch is installed.

## Measured export and remaining requirements

The initial local export produced a 29.6 MiB ONNX model. TorchScript parity and ONNX probability/class parity passed on nine inputs; maximum probability difference was 0.0087. The CPU benchmark measured p50 93 ms and p95 185 ms using one thread on this machine. **The p95 ≤ 120 ms target was not met.** These are export measurements, not a deployed-service benchmark.

`make test` and `make loadtest` remain the regression and latency gates; they were not run during this migration. Docker size, cold start, cloud deployment, scale-to-zero, actual costs, and alert delivery still require measurement. CI restores and registers the imported model; training is a separate command. The workflow currently provides validation, not cloud deployment.

See [model card](reports/model_card.md), [migration notes](reports/roast_migration.md), and [cost assumptions](reports/cost_report.md). Historical defect slides and reports must be revised before submission.
