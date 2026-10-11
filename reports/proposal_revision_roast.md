# Draft revised ITCS355 capstone proposal

**Title:** Automated Coffee Bean Roast Classification API  
**Team:** Peerawat Somsurat and Yongyot — Team Idea  
**Status:** Scope revision approved by the project owner; instructor approval still required.

## Problem and output

Provide a synchronous API that classifies a coffee bean image into Dark, Green, Light, or Medium. Green is the unroasted category. The result supports visual roast inspection and does not certify coffee defects or SCA grades.

## Data and model

Use the supplied DL_FinalProject dataset and Iteration4 Swin-T architecture. The original dataset has 1,600 RGB images at 224 × 224, but all 400 original test images also occur in its training folder. Exact pixel deduplication produces 1,194 unique images. The prepared stratified split uses seed 42 and contains 835 training, 178 validation, and 181 test images.

The imported Swin checkpoint is used for the serving prototype. Its recorded 99.75% accuracy is contaminated and is not an acceptance result. A model initialized from ImageNet weights will be trained on the prepared train split and selected on validation loss before evaluating the held-out test split. Near-duplicate or shared-bean correlations remain a dataset limitation. Confirm the dataset source and redistribution license before publishing images.

## Reproducibility and lineage

Version the dataset and checkpoint with DVC; use a shared S3 or GCS remote. Record the split manifest, data hash, code revision, seed, architecture, parameters, runtime versions, evaluation metrics, and model artifacts in MLflow. Register the model and tie serving artifacts to the checkpoint with metadata and SHA-256 hashes.

## Serving and portability

Serve quantized ONNX using FastAPI in a non-root Docker container. Keep inference and training code independent of the cloud provider. Select one provider for actual deployment and document environment configuration, tagged resources, budget alerts, teardown, and actual cost evidence.

Retain the original operational objectives of p95 ≤ 120 ms and p99 ≤ 250 ms. The initial local CPU export benchmark measured p95 about 185 ms, so optimization or an agreed revision is required. Container size under 250 MB and cold start under 2 seconds are provisional goals that must be measured for Swin-T.

## Failure demonstration and observability

Inject covered-camera and overexposed frames. Reject near-uniform frames with HTTP 422 before inference, log the rejection, increment the anomaly metric, and demonstrate delivery of the CameraSensorOcclusionWarning alert. Retain regression checks so removal of the guard causes CI to fail.

Provide a dashboard for prediction counts by roast class, inference latency, and rejected images. Demonstrate the actual monitoring and alert loop during the final presentation.

## Delivery and acceptance

Submit runnable code, a clean-checkout setup guide, DVC restoration instructions, the reproducible training pipeline, registered model lineage, deployed inference evidence, CI/CD evidence, dashboard and delivered-alert evidence, cost per 1,000 predictions, a one-page model card, failure injection evidence and regression checks, presentation materials, and teardown evidence.

Model accuracy will be reported honestly on the corrected evaluation protocol. Historical MobileNet cost estimates cannot substantiate Swin deployment costs; use measured active duration, memory, provider rates, and billing records.
