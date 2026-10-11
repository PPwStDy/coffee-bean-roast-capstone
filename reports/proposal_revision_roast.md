# Draft revised ITCS355 capstone proposal

**Title:** Automated Coffee Bean Roast Classification API  
**Team:** Peerawat Somsurat and Yongyot — Team Idea  
**Status:** Scope revision approved by the project owner; instructor approval still required.

## Problem and output

Provide a synchronous API that classifies a coffee bean image into Dark, Green, Light, or Medium. Green is the unroasted category. The result supports visual roast inspection and does not certify coffee defects or SCA grades.

## Data and model

Use the supplied DL_FinalProject dataset and Iteration4 Swin-T architecture. The original dataset has 1,600 RGB images at 224 × 224, but all 400 original test images also occur in its training folder. Exact pixel deduplication produces 1,194 unique images. The prepared stratified split uses seed 42 and contains 835 training, 178 validation, and 181 test images.

The imported Swin checkpoint is preserved as a historical baseline. Its recorded 99.75% accuracy is contaminated and is not an acceptance result. Fresh ImageNet training uses the prepared split; checkpoint selection uses validation loss and export selection uses validation macro-F1 and median latency. The selected release is evaluated on the test split once. Near-duplicate or shared-bean correlations remain a dataset limitation. Both verified version1 Kaggle sources use CC BY-SA4.0; see DATA_LICENSE.md for attribution, modifications and the Ontoum et al.2022 research citation.

## Reproducibility and lineage

Version the dataset and checkpoint with DVC backed by private Azure Blob storage. Record the split manifest, data hash, actual Git revision, seed, architecture, parameters, dependency lock, evaluation metrics and artifacts in MLflow. Register the immutable release bundle in the existing Azure ML workspace and tie serving artifacts to its checkpoint with mandatory metadata and SHA-256 hashes.

## Serving and portability

Serve the validation-selected ONNX using FastAPI in a non-root Docker container. Keep core inference and training independent of Azure behind the course CloudAdapter. Use the Azure for Students subscription in East Asia, a dedicated tagged capstone group, managed identity and GitHub OIDC. Container Apps starts at2vCPU/4GiB with minimum0 and maximum2 replicas. JPEG/PNG requests are limited to5MiB decoded and20megapixels; inference concurrency is bounded at2.

Replace the original unmeasured performance claims with a defined acceptance procedure:1,000 warm requests at concurrency2 and20 cold-start trials with zero replicas verified before each request. Freeze initial p95/p99 at the measured value plus20%, rounded upward. Later CI/deployment runs enforce the same targets. Record image size separately. Requests use the current immutable model version; model freshness follows an explicitly validated release rather than time-based retraining.

## Failure demonstration and observability

Inject covered-camera and overexposed frames. Reject near-uniform frames with HTTP 422 before inference, log the rejection, increment the anomaly metric, and demonstrate delivery of the CameraSensorOcclusionWarning alert. Retain regression checks so removal of the guard causes CI to fail.

Provide a dashboard for prediction counts by roast class, inference latency, and rejected images. Demonstrate the actual monitoring and alert loop during the final presentation.

## Delivery and acceptance

Submit runnable code, a clean-checkout setup guide, DVC restoration instructions, the reproducible training pipeline, registered model lineage, deployed inference evidence, CI/CD evidence, dashboard and delivered-alert evidence, cost per 1,000 predictions, a one-page model card, failure injection evidence and regression checks, presentation materials, and teardown evidence.

Model accuracy will be reported honestly on the corrected evaluation protocol. Historical MobileNet cost estimates cannot substantiate Swin deployment costs; use measured active duration, memory, provider rates, and billing records.

## Budget and proposed team ownership

The course allowance is800THB per student. Captured year-to-date subscription spending is charged conservatively against it. Budget notifications use50/80/100% of the remaining allowance; deployment is blocked when a seven-day forecast with25% margin exceeds that remainder. Registry and monitoring remain chargeable during serving scale-to-zero. Local training incurs no Azure compute charge; electricity and device costs are unmeasured.

Proposed responsibilities for team confirmation: Peerawat owns model/data lineage and deployment; Yongyot owns monitoring, incident demonstration and presentation. Record actual contributions before submission. Revised instructor approval, the Session5 architecture review, live presentation/Q&A and final repository submission remain pending.
