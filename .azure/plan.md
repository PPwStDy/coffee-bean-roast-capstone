# Coffee bean roast capstone Azure implementation

Status: Approved — Executing

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

The subscription and user have been verified with Azure CLI. No new paid resources have been created. Actual RBAC, regional quotas, spending and price checks must be captured before provisioning. GitHub CLI authentication is currently missing; repository creation and remote CI depend on it.

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

Pending. Update status to Ready for Validation before invoking azure-validate; record successful validation before deployment through azure-deploy.

## External completion steps

Instructor approval, architecture review, live presentation/Q&A and final submission remain pending until they occur.
