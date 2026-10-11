# Coffee Bean Roast Capstone Report

This report records the operational system built for Group Idea and distinguishes successful evidence from remaining work. The project owner approved changing the supplied defect proposal to roast classification. Instructor approval of the revised scope, the Session 5 clinic, live presentation/Q&A and submission remain external events.

The service classifies an entire coffee image into Dark, Green, Light or Medium using Iteration4 Swin-T. Green is unroasted. Results support educational visual inspection; they do not establish individual-bean defects, roast chemistry or SCA compliance.

A clean 20-epoch run completed in 22.44 minutes on the 8 GiB M1. Its selected INT8 export correctly classified 181/181 test images. All 52 local tests and Linux container integration passed. The historical 99.75% baseline is preserved with a contamination warning.

The ten course components are versioned code/data, automated reproducible training, registered lineage, deployed inference, CI/CD that can fail, a dashboard, a working alert, cost/1000 predictions, a one-page model card and an engineered failure. Model accuracy itself carries no marks. The repository checklist is the source of current acceptance status.

Evidence files include timestamps, resource IDs, Git/DVC revisions and raw provider responses. Configuration or a generated script is not counted as proof of successful live execution. Failed attempts are preserved alongside their fixes.

# Dataset audit and attribution

The supplied data has 1600 readable images: 1200 in the original training folder and 400 in its test folder. All 400 original test images have exact pixel duplicates in original training. There are 1194 unique images and no conflicting labels. Removing 406 copies and seed 42 stratified splitting yields 835/178/181.

The manifest retains original names, file SHA-256, normalized pixel hashes, duplicate groups, labels and final assignments. Data contracts verify class order, counts, 224 px RGB integrity, manifest coverage, original hash consistency and zero exact duplicates both within and between splits. Exact-pixel deduplication does not establish independence of near duplicates or photographs of the same beans.

The verified primary sources are Gerry's resized version 1 dataset and Sakdipat Ontoum's version 1 dataset on Kaggle, both CC BY-SA 4.0. DATA_LICENSE.md records creators, links, license, the removal/resplit/renaming modifications and Ontoum et al.(2022), Coffee Roast Intelligence, arXiv 2206.01841. Small test fixtures are attributed separately.

Data, historical weights and the clean release use DVC pointers with a shared private Azure Blob remote. A fresh checkout restored 1197 historical data/model objects and passed the full data contract; the clean release has its own pointer and upload receipt. Azure CLI/OIDC credentials stay outside source control.

# Reproducible training and export selection

The actual training source commit is 763915a0b9d05af803194239a3601a4a15dfa08f; dataset DVC revision is d241ed318d2c1d8672d939938d3b71be.dir. The dependency lock SHA-256 is 51616381f32a57131c7a4fb27d694b819edfde071519a124ad54195d9ddd99d5. Check out that exact commit and lock to reproduce the recorded procedure rather than silently using newer dependencies.

The isolated Python 3.12 environment does not inherit machine site-packages. ImageNet Swin-T initialization replaces the contaminated coffee checkpoint. Seed 42 is recorded with 20 epochs, batch 8, backbone LR 5e-5, head LR 1e-3, AdamW weight decay 0.01, label smoothing 0.05, OneCycleLR and pct_start 0.2. MPS numerical behavior can differ between machines; the procedure is reproducible without promising bitwise identity.

The best validation-loss checkpoint was epoch 10 with loss 0.203336. No test images were evaluated during training. Local MLflow records actual parameters, dependencies, history and checkpoint. A batch 32 attempt caused memory pressure while Docker was running; it was stopped before completing an epoch. Batch 8 with Docker stopped completed successfully.

Float 32 and dynamic INT8 dense-weight exports use ONNX Runtime CPU, one thread, five warmups and all 178 validation images. Selection chooses the fastest median candidate whose macro-F1 falls by no more than 0.01 and whose sampled probability error is at most 0.05. Both validation F1 values were 1.0. INT8 was 64.3 ms versus float 130.2 ms median and shrank 107.4 MiB to 29.6 MiB.

The selected INT8 release was evaluated on 181 test images exactly once: accuracy 1.0, macro-F1 1.0. A marker is written before test evaluation and repeat attempts for the same bundle are refused. Checkpoint, ONNX, TorchScript, metadata, history, evaluation, model card and hash manifest are stored together. Azure ML registry version 1 preserves the semantic release version in tags and the complete metadata bundle.

# Serving contract and release safety

FastAPI preserves /predict,/predict/base64,/health,/ready and /metrics. Raw JPEG/PNG and multipart file uploads are documented in OpenAPI; strict base64 JSON is supported. Returned fields include predicted_class, predicted_class_id, confidence, four probabilities, quality measurements, latency and model_version. X-Model-Version must agree with the body.

Input handling checks actual format, decoded size at most 5 MiB and dimensions at most 20 megapixels before image loading. Controlled errors distinguish malformed or unreadable bytes 400, unsupported image format 415, oversized payload 413, schema/optical rejection 422 and unavailable/busy inference 503. Inference runs outside the asynchronous request loop with concurrency 2 and bounded waiting.

Readiness checks architecture, class order, input layout, ImageNet preprocessing, mandatory model/version hashes, output shape and finite outputs. Missing, corrupted and incompatible artifacts produce failed readiness and controlled 503 predictions. Liveness remains available to diagnose the process.

CI restores the selected immutable bundle without retraining, checks lint and provider portability, executes data/model/API/cloud contracts, verifies export gates, mutates the optical guard in an isolated copy and runs Linux container integration. The full-training workflow is separate. Successful main CI triggers release; failed CI cannot trigger deployment.

Deployment captures previous traffic, validates a digest-pinned zero-traffic candidate when an existing revision is present, executes endpoint checks and frozen latency gates, then promotes 100% traffic. Candidate validation failure restores previous traffic, verifies it and deactivates the rejected candidate. Promotion/rollback evidence must reflect live provider results.

# Azure architecture and observability

The approved Azure for Students subscription is in East Asia. Only rg-itcs355-6688218-capstone is owned by this capstone, with course=itcs355, student=6688218 and lab=capstone tags. Infrastructure uses Bicep validation and What-if after checking permissions, region policy, quota, provider registration and budget. The existing shared Azure ML workspace is retained.

Private Blob storage provides DVC; Basic ACR stores images; a runtime managed identity pulls artifacts; GitHub OIDC provides short-lived deployment credentials. Read-only PR credentials are separate from main deployment credentials. Immutable GitHub owner/repository IDs are included in federation trust; a prior name-only trust failed and was corrected using the actual issuer/audience/subject.

Container Apps uses 2 vCPU/4 GiB, HTTP concurrency 2, min 0/max 2, managed identity and a Linux image digest. A 30 second configured cooldown is recorded in Bicep; actual zero-replica checks determine cold-trial eligibility. No polling of the HTTP endpoint occurs between cold trials. Storage, registry and monitoring costs persist when serving reaches zero.

Local Prometheus, Grafana and Alertmanager expose class counts, latency and camera anomaly counters. Structured JSON application logs reach Azure Log Analytics. The deployed workbook shows request status volume, server p50/p95/p99 and optical rejection events. Foundation provisioning skips query validation before the log table exists; after ingestion, the actual five-minute production query was validated successfully. Failed provisioning and notification attempts were retained.

The engineered failure is collapsed dynamic range: black and white frames return 422 before model invocation. Logs and metrics name occlusion_guard_rejection. The student's email receiver was verified in Azure. A real camera warning reached the student's mailbox. The receipt records the subject, alert ID, resource, rule and time; the screenshot shows filtered mailbox results. The delivery verification used a 30-minute query window over real camera faults. The production rule uses a five-minute window and evaluation interval. Azure separately recorded successful Email transport from the production five-minute rule.

# Measured performance and operating costs

Warm benchmark: 1000 requests, concurrency 2, p95 240.64 ms, p99 250.66 ms; wall time 113.8s.

Cold benchmark from the Bangkok Mac: 20 trials with verified zero replicas, p95 28950.42 ms, p99 28994.38 ms.

Frozen targets: Fixed warm p95/p99: 289/301 ms; cold p95/p99: 34741/34794 ms. Warm client: github-actions-ubuntu. Image size is reported separately: initial 164,650,776 bytes. Future releases enforce the fixed latency targets.

Latest Linux container: 387,476,528 uncompressed bytes, linux/amd64, source 751601c9214bbc96aba853dbeed00cb9cee4e358. This current build is recorded separately from the immutable initial image measurement.

Conservative remaining course allowance: 634.59 THB after prior subscription spending. Seven-day forecast: 239.09 THB including 25% margin. Primary East Asia retail rates and dated ECB USD/THB exchange evidence are captured. Free grants are excluded; these are estimates, not final invoices.

Serving cost per 1,000: At most USD 0.014056 / 0.4713 THB per 1,000 predictions, using 113.80 measured seconds, 2 vCPU / 4 GiB per replica and at most two replicas active throughout. This is a conservative allocation bound, not an invoice; exact replica-seconds and free-grant deductions are unmeasured.

Storage, registry, log ingestion/alerts and training are reported separately in cost_report.md. Local MPS training incurs zero Azure compute charge; device and electricity costs are unmeasured. One-time DVC downloads and other network transfer are not itemized in the allocation estimate; billing evidence may lag. Budget notifications at 50/80/100% of an 18 USD remaining-allowance budget are alerts, not a shutdown. A forecast gate blocks over-budget deployments. Scoped teardown and scheduled seven-day retention remove chargeable owned resources.

# Acceptance evidence and academic completion

Remote CI: https://github.com/PPwStDy/coffee-bean-roast-capstone/actions/runs/38160514077; result: success. Azure ML registered coffee-bean-roast-classifier version 1. Deployed candidate promoted: True. Teardown verified: pending.

The detailed requirement-to-evidence checklist records every acceptance scenario separately. It includes actual CI links, lineage, endpoint results, export parity, image size, warm/cold reports, dashboard captures, delivered email, cost and teardown. Historical container tests and generated templates cannot stand in for final deployed evidence.

At the user's request, the live API and DVC remote remain available until the scheduled October 18 cleanup (due at 20:17 Bangkok, subject to scheduler delay). Actual deletion verification is pending. Teardown requires exact capstone group ownership and checks all resource tags. It verifies group absence and preservation of the existing shared workspace. The subscription owner separately removes only the exact capstone budget and two recorded external role assignments. Shared Azure ML model history and unrelated laboratory resources are preserved.

Proposed responsibility split: Peerawat owns data/model lineage and deployment; Yongyot owns monitoring, failure demonstration and presentation. Actual contributions need team confirmation. The presentation script allocates one minute each to problem, data, training, architecture, live prediction, failure and regression, performance and cost, and limitations. Live timing, unexpected input and five-minute Q&A are external demonstration requirements.

Instructor approval of the changed scope, Session 5 architecture review, live presentation/Q&A and final repository submission remain pending. Do not mark the project fully complete until all applicable technical evidence exists and academic events are recorded. A further week should focus on independently captured images, camera/source separation, confidence calibration and broader operating-condition checks.

Sources: Kaggle gpiosenka/coffee-bean-dataset-resized-224-x-224 and sot2542/coffee-bean-dataset-v1; creativecommons.org/licenses/by-sa/4.0/; arxiv.org/abs/2206.01841; learn.microsoft.com/azure/container-apps/scale-app; learn.microsoft.com/azure/container-apps/log-monitoring; prices.azure.com/api/retail/prices; ECB daily exchange rates. Course requirements: local public_teaching_mlaiops/course/project/project-brief.md and the course specification.
