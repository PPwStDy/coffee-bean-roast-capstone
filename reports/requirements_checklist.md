# ITCS355 requirement to evidence checklist

Updated during implementation. A check is complete only when its successful evidence exists. The original Iteration4 checkpoint is a historical baseline with source-split contamination.

| Course component | Completion evidence | Current status |
|---|---|---|
| 1 Versioned data and code | Independent private Git root; DVC pointers; source attribution and manifest; shared remote and clean restoration | Private repository created, Blob upload complete; clean restoration pending |
| 2 Reproducible automated training | Locked isolated environment; ImageNet initialization; corrected 835/178/181 splits; seed, commit, dependencies and full history | Clean run in progress, batch8 on MPS |
| 3 Model registry and lineage | Versioned bundle with checkpoint, ONNX, hashes, metadata, evaluation and model card; Azure ML registration receipt | Pending completed clean release |
| 4 Deployed inference endpoint | Digest, Container Apps revision and endpoint checks; finite four-class probabilities and consistent headers | Foundation deployed; baseline container integration passed; clean production release pending |
| 5 CI and CD that can fail | Passing GitHub Actions links; deliberate failed change; skipped release; candidate promotion and rollback evidence | Workflows implemented; remote runs pending |
| 6 Operational dashboard | Local Grafana/Prometheus evidence plus deployed workbook capture and structured logs | Local stack retained; Azure workbook deployed; data/captures pending |
| 7 Working alert | Black/white 422, rejection event and counters, fired rule, delivery receipt to signed-in email | Five-minute Azure log alert and email group deployed; actual delivery pending |
| 8 Cost per 1000 predictions | Actual deployed allocation and duration; separate serving/storage/registry/monitoring/training costs; billing evidence | Regional prices and prior spending captured; budget forecast passed; serving benchmark pending |
| 9 One-page model card | One-page PDF with clean test results, intended use, limitations, license and lineage | Markdown draft exists; final release/PDF pending |
| 10 Engineered failure and regression defense | Failure injection, observed telemetry and alert, guard removal causes CI test failure | Local isolated guard mutation caught; deployed/email/remote CI evidence pending |

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
- [ ] Clean checkout restores data and release from shared DVC remote.
- [ ] Completed fresh training and best validation-loss checkpoint.
- [ ] Float and INT8 validation comparison and eligible fastest export.
- [ ] Selected release evaluated on the test split exactly once.
- [ ] Azure ML release registration.
- [ ] Remote passing CI, explicit bad-change failure and release prevention.
- [ ] Digest-pinned deployed candidate checks, promotion and rollback exercise.
- [ ] 1000 warm requests at concurrency2 and 20 verified scale-to-zero cold starts.
- [ ] Initial measured p95/p99 targets frozen with 20% margin; subsequent runs enforce them.
- [ ] Deployed logs, workbook and actual alert email delivery evidence.
- [ ] Cost per1000 from measured deployment, component costs and budget alerts.
- [ ] Scoped teardown removes capstone resources and verifies shared workspace preservation.
- [ ] Revised proposal, comprehensive report, slides and eight-minute demo script.

## External academic steps

- [ ] Instructor approval of revised roast scope.
- [ ] Session5 architecture review.
- [ ] Live eight-minute presentation and five-minute Q&A.
- [ ] Final repository submission within the course deadline.

Group Idea: 6688218 Peerawat and 6688230 Yongyot, as recorded in the supplied proposal. Actual team contributions and academic attendance must be recorded by the team.
