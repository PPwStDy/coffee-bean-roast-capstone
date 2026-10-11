# ITCS355 requirement to evidence checklist

Updated during implementation. A check is complete only when its successful evidence exists. The original Iteration4 checkpoint is a historical baseline with source-split contamination.

| Course component | Completion evidence | Current status |
|---|---|---|
| 1 Versioned data and code | Independent private Git root; DVC pointers; source attribution and manifest; shared remote and clean restoration | Complete: private repository; Blob data/release push; clean data and release restoration receipts |
| 2 Reproducible automated training | Locked isolated environment; ImageNet initialization; corrected 835/178/181 splits; seed, commit, dependencies and full history | Complete: 20 epochs, batch 8 MPS, 22 min 26 sec; actual Git/DVC/seed/lock/history |
| 3 Model registry and lineage | Versioned bundle with checkpoint, ONNX, hashes, metadata, evaluation and model card; Azure ML registration receipt | Complete: immutable clean bundle, Azure ML coffee-bean-roast-classifier version 1 |
| 4 Deployed inference endpoint | Digest, Container Apps revision and endpoint checks; finite four-class probabilities and consistent headers | Complete: clean release promoted; candidate-deployment.json and deployed-endpoint-checks.json |
| 5 CI and CD that can fail | Passing GitHub Actions links; deliberate failed change; skipped release; candidate promotion and rollback evidence | Complete: passing CI 38155673260; guard removed failed CI 38153979754; release 38154153512 skipped; verified live rollback |
| 6 Operational dashboard | Local Grafana/Prometheus evidence plus deployed workbook capture and structured logs | Complete: populated local Grafana, Azure workbook screenshots and actual structured log summary |
| 7 Working alert | Black/white 422, rejection event and counters, fired rule, delivery receipt to signed-in email | Complete: actual fired camera-warning email observed in authenticated Outlook; provider delivery succeeded. Diagnostic window and production five-minute rule are recorded |
| 8 Cost per 1000 predictions | Actual deployed allocation and duration; separate serving/storage/registry/monitoring/training costs; billing evidence | Complete estimate: 113.80 measured seconds; <=0.4713 THB per 1000 at the maximum two-replica allocation; component rates and budget receipts captured; invoice may lag |
| 9 One-page model card | One-page PDF with clean test results, intended use, limitations, license and lineage | Complete: deliverables/model_card.pdf (one page), release metadata and model card |
| 10 Engineered failure and regression defense | Failure injection, observed telemetry and alert, guard removal causes CI test failure | Complete: real black/white rejection, delivered camera alert and guard removal causing remote CI failure |

## Detailed acceptance scenarios

- [x] Dataset class order, integrity, hash consistency and zero exact-pixel duplicates.
- [x] License CC BY-SA 4.0, both version1 sources and requested paper citation recorded.
- [x] Isolated Python 3.12 environment and cross-platform dependency lock.
- [x] JPEG/PNG payload handling, 5 MiB and 20 megapixel limits, malformed base64 and controlled errors.
- [x] Missing, corrupted, wrong-class, wrong-preprocessing and wrong-version artifacts fail readiness.
- [x] Black and white frames return 422 before inference; local logs and metrics recorded.
- [x] Local concurrent requests and matching model-version headers.
- [x] Baseline Linux container startup and API integration.
- [x] Azure subscription, permission, quota, policy, price and budget preflight.
- [x] Shared Azure ML workspace retained and dedicated capstone ownership tags applied.
- [x] Clean checkout restores data and release from shared DVC remote.
- [x] Completed fresh training and best validation-loss checkpoint.
- [x] Float and INT8 validation comparison and eligible fastest export.
- [x] Selected release evaluated on the test split exactly once.
- [x] Azure ML release registration.
- [x] Remote passing CI, explicit bad-change failure and release prevention.
- [x] Digest-pinned deployed candidate checks, promotion and rollback exercise.
- [x] 1000 warm requests at concurrency 2 from the GitHub release runner environment.
- [x] 20 natural scale-to-zero cold starts, each with management-plane zero-replica evidence.
- [x] Fixed warm p95/p99 289/301 ms and cold p95/p99 34741/34794 ms, measured plus 20% rounded upward; final release enforcement pending.
- [x] Deployed structured logs and populated Azure workbook screenshots.
- [x] Azure notification recipient verified; camera rule fired and action group executed.
- [x] Actual fired camera-warning email delivered to the recipient's mailbox; diagnostic 30-minute replay explicitly labeled.
- [x] Cost per 1000 from measured deployment, component costs and budget alerts.
- [ ] Scoped teardown removes capstone resources and verifies shared workspace preservation.
- [ ] Revised proposal, comprehensive report, slides and eight-minute demo script.

## External academic steps

- [ ] Instructor approval of revised roast scope.
- [ ] Session5 architecture review.
- [ ] Live eight-minute presentation and five-minute Q&A.
- [ ] Final repository submission within the course deadline.

Group Idea: 6688218 Peerawat and 6688230 Yongyot, as recorded in the supplied proposal. Actual team contributions and academic attendance must be recorded by the team.

## Successful release evidence

- [Passing GitHub CI, 50 checks](https://github.com/PPwStDy/coffee-bean-roast-capstone/actions/runs/38155673260).
- [Deliberately broken guard failed CI](https://github.com/PPwStDy/coffee-bean-roast-capstone/actions/runs/38153979754); [release skipped](https://github.com/PPwStDy/coffee-bean-roast-capstone/actions/runs/38154153512).
- [Successful release promotion](https://github.com/PPwStDy/coffee-bean-roast-capstone/actions/runs/38155890840).
- [Initial 1000-request performance workflow](https://github.com/PPwStDy/coffee-bean-roast-capstone/actions/runs/38155675153).
- `evidence/rollback-drill.json`: rejected candidate inactive and previous revision retained at 100% traffic.
- `evidence/azure-workbook.png` and `azure-workbook-details.png`: actual request, latency and optical failure data.
- `evidence/deployed-alerts.json` and `azure-alert-history.json`: actual rule firing and action group execution. Mailbox evidence is recorded separately in azure-email-delivery.json and azure-email-search.png.
- `evidence/clean-restoration.json` and `evidence/clean-release-restoration.json`: independent checkout restoration and integrity.
- `training_history.json` and immutable release metadata: epoch 10 validation selection; all 20 epochs recorded.
- `model_metadata.json`: full validation comparison; single selected release test evaluation, 181/181 correct.
- `evidence/azure-ml-release.json`: real registry version 1.
- `evidence/final-tests.xml`: 52 passing local checks, including fixed-target validation and refusal to recalibrate.
- `evidence/local-alert-delivery.log`: actual Alertmanager firing webhook delivery.

- `evidence/initial-warm.json`, `initial-cold.json`, `initial-container-image.json` and `monitoring/slo.json`: immutable initial measurement and fixed targets.
