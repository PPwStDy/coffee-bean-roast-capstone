# Coffee bean roast capstone Azure implementation

Status: Deployed and validated; warm/cold benchmarks and actual camera-alert email delivery recorded. Full teardown is retained until October 18.

The user approved this plan on 2026-10-11. This file records execution; completion requires successful evidence.

## Context and decisions

- Modify the existing FastAPI / Iteration4 Swin-T project; class order Dark, Green, Light, Medium.
- Private repository: PPwStDy/coffee-bean-roast-capstone, independent of the surrounding lab repository.
- Subscription: Azure for Students, 6638a4ea-96da-4326-969a-2e40305cfc83.
- Region: eastasia. Dedicated group: rg-itcs355-6688218-capstone.
- Tags: course=itcs355, student=6688218, lab=capstone.
- Recipe: Bicep with Azure CLI; retain the existing lab tooling.
- Container Apps consumption: Linux digest-pinned image, 2 vCPU / 4 GiB, min 0 / max 2 replicas, HTTP concurrency 2.
- Blob Storage for DVC; Basic ACR; managed identity for image pulls; GitHub OIDC for CI.
- Log Analytics, Azure Monitor workbook, camera occlusion log alert and email action group.
- Alert recipient: peerawat.son@student.mahidol.ac.th (the approved signed-in Azure user).
- Reuse Azure ML workspace itcs355-6688218 in group itcs355-6688218; never remove shared resources.
- Budget cap: remaining course allowance, maximum 800 THB. Read spending and block deployments whose forecast exceeds the remaining amount.

## Architecture

Git/DVC → reproducible ImageNet training → validation-only export selection → immutable release → Azure ML registration → ACR → Container Apps. Console JSON logs flow to Log Analytics and its workbook / email alert. Local Prometheus / Grafana / Alertmanager remain available.

## Resource inventory and preflight

The subscription and user have been verified with Azure CLI. The dedicated capstone foundation has been deployed; the trained release is deployed and its frozen warm performance gates have passed. Owner permission is confirmed. At preflight, East Asia allowed one Container Apps environment with zero used; the capstone environment now occupies that slot. Registered regional quota evidence, year-to-date spending, retail prices and dated ECB exchange rates are captured under reports/evidence. The private GitHub repository has been created. The forecast for seven days, three active hours at two replicas, and 0.1 GB/day logs is 239.09 THB including 25% margin; conservative remaining allowance is 634.59 THB.

## Execution checklist

- [x] Isolated environment, locked dependencies, independent Git root.
- [x] API hardening, complete cloud contract, input / artifact / optical regression checks.
- [x] Dataset attribution, DVC remote, clean-checkout restoration.
- [x] ImageNet training, validation selection, single selected-release test evaluation, Azure ML registry.
- [x] Bicep validation, permission / quota / budget evidence.
- [x] Digest image deployment, OIDC, candidate promotion / verified rollback.
- [x] Deployed structured logs and populated Azure workbook captures.
- [x] Email receiver verified; camera rule fired and notification action executed.
- [x] Fired camera-warning email observed in authenticated Outlook; diagnostic query window labeled.
- [x] 1,000 warm requests (concurrency 2), 20 natural cold starts, frozen SLOs.
- [x] Failure drill, failed CI/release prevention, actual email delivery and measured cost estimate.
- [ ] Full scoped teardown verification: pending until the user-approved October 18 cleanup, due at 20:17 Bangkok subject to scheduling delay.
- [ ] Revised proposal, model card, report, slides, demo script, evidence checklist.

## Validation and deployment proof

Azure Validate completed on 2026-10-11 for the foundation. Bicep compiled main/app/budget, ARM subscription validation returned Succeeded, and What-if returned Succeeded with no deletions. Owner RBAC, service registration, one available East Asia environment, Storage quota and policy assignments were inspected. The local Linux baseline container passed readiness, four-class predictions, controlled malformed input, optical rejection and telemetry checks. API/data contract tests: 29 passed; cloud contract tests: 4 passed; model behavior tests: 3 passed. Evidence is under reports/evidence. The clean release is registered as Azure ML version 1 and passes 52 local checks. GitHub CI 38160514077 passed 52 checks plus Linux container integration. The environment uses WorkloadProfiles; a digest-pinned candidate was promoted after endpoint checks and 1,000-request fixed-target validation (candidate-deployment.json). Initial performance targets are frozen; later release validation passed warm p95/p99 240.78/249.90 ms against the unchanged 289/301 ms limits.

Azure Deploy provisioned only the dedicated capstone group using infra/main.bicep. The shared ML workspace and existing resources are preserved.

## External completion steps

Instructor approval, architecture review, live presentation/Q&A and final submission remain pending until they occur.
