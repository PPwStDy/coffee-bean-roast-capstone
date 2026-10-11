# Coffee bean roast capstone Azure implementation

Status: Validated — foundation; application release pending

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

The subscription and user have been verified with Azure CLI. No new paid resources have been created. Owner permission is confirmed. East Asia allows one Container Apps environment with zero currently used. Registered regional quota evidence, year-to-date spending, retail prices and dated ECB exchange rates are captured under reports/evidence. The private GitHub repository has been created. The forecast for seven days, three active hours at two replicas, and 0.1 GB/day logs is 253.76 THB including 25% margin; conservative remaining allowance is 635.98 THB.

## Execution checklist

- [ ] Isolated environment, locked dependencies, independent Git root.
- [ ] API hardening, complete cloud contract, input / artifact / optical regression checks.
- [ ] Dataset attribution, DVC remote, clean-checkout restoration.
- [ ] ImageNet training, validation selection, single selected-release test evaluation, Azure ML registry.
- [ ] Bicep validation, permission / quota / budget evidence.
- [ ] Digest image deployment, OIDC, candidate promotion / rollback.
- [ ] Deployed logs / workbook / delivered email alert.
- [ ] 1,000 warm requests (concurrency 2), 20 cold starts, frozen SLOs.
- [ ] Failure drill, CI failure evidence, costs, scoped teardown verification.
- [ ] Revised proposal, model card, report, slides, demo script, evidence checklist.

## Validation and deployment proof

Azure Validate completed on 2026-10-11 for the foundation. Bicep compiled main/app/budget, ARM subscription validation returned Succeeded, and What-if returned Succeeded with no deletions. Owner RBAC, service registration, one available East Asia environment, Storage quota and policy assignments were inspected. The local Linux baseline container passed readiness, four-class predictions, controlled malformed input, optical rejection and telemetry checks. API/data contract tests: 29 passed; cloud contract tests: 4 passed; model behavior tests: 3 passed. Evidence is under reports/evidence. The clean trained model and its application revision still need release validation before application deployment.

Azure Deploy will provision only the dedicated capstone group using infra/main.bicep. The shared ML workspace and existing resources are preserved.

## External completion steps

Instructor approval, architecture review, live presentation/Q&A and final submission remain pending until they occur.
