# Eight minute demonstration script

This script is rehearsal material. Live attendance, instructor approval and Q&A completion must be recorded after the actual events. Use actual evidence and disclose pending steps; never present a generated template as live proof.

## 0:00 to 1:00 Problem and scope

“We provide image-level coffee roast classification for visual inspection: Dark, Green, Light and Medium. Green is unroasted. We revised the original defect proposal because our supplied Iteration4 model and data classify roast. This does not certify SCA defects or individual beans.” Show one licensed fixture per class. State instructor scope approval status.

## 1:00 to 2:00 Data and reproducibility

Show the DVC pointers, locked environment, source attribution and manifest. “Our audit found that all 400 original test images duplicated original training images. We preserved that checkpoint as a historical baseline. The corrected splits contain 835/178/181 images with no exact duplicates.” Show the clean restoration receipt and both version 1 licensed sources.

## 2:00 to 3:00 Training and model lineage

Show the actual source commit, dataset revision, dependency lock and training history. “Twenty epochs took 22 minutes 26 seconds. We selected epoch 10 by validation loss, compared float and INT8 only on validation, then evaluated the selected release on the test split once.” Show 181/181 correct with the camera/source limitations. Show the reproducible command and separate workflow; use the existing trained release for the demo.

## 3:00 to 4:00 Architecture and release safety

Walk through private Blob DVC, the immutable bundle, Azure ML registry, CI, digest-pinned Container Apps and the workbook. Explain 2 vCPU / 4 GiB, concurrency 2, min 0 / max 2, managed identity and OIDC. Show candidate checks and verified promotion. Open the rollback receipt: previous revision at 100%, rejected candidate inactive.

## 4:00 to 5:00 Live prediction and unexpected inputs

Submit a real coffee PNG to `/predict`, then a base64 JPEG/PNG to `/predict/base64`. Point to four finite probabilities, fixed class IDs and matching version headers. Invite the instructor to provide an unexpected input. Explain415 unsupported image format,413 size limits,400 unreadable bytes and 422 invalid schema. A probability is uncalibrated confidence and arbitrary noncoffee photos can pass the optical guard.

## 5:00 to 6:00 Camera failure and regression defense

Submit black and white RGB frames. Show 422 before inference, rejection logs, anomaly counters and workbook records. Show the real alert and mailbox delivery receipt if verified; trigger ahead of the presentation because evaluation takes five minutes. Show the deliberately failed guard-removal GitHub run and skipped release. “Uniform images must be rejected before the model is called.” Restore a valid image to demonstrate recovery. Keep the isolated missing/corrupt-artifact evidence ready for Q&A.

## 6:00 to 7:00 Performance and cost

Show the actual 1,000-request concurrency 2 warm report, 20 zero-replica cold trials, frozen p95/p99 targets and image bytes separately. Explain client network time versus server scoring time and the fixed GitHub runner boundary. Show cost per 1,000 using deployed allocation and measured duration, with separate storage, registry, monitoring and local training. Discuss the remaining course allowance and 50/80/100% budget notifications. Distinguish estimates from invoices.

## 7:00 to 8:00 Limits and completion

Show the requirement checklist and safe teardown record, with the shared Azure ML workspace preserved. Explain source/camera confounding, uncalibrated confidence, absence of near-duplicate guarantees and limited dataset size. “Another week would buy new independently captured images and calibration, plus broader camera-condition checks.” State any technical evidence still pending and the external academic milestones. Finish before 8:00; reserve5 minutes for Q&A.

## Questions to prepare

- Why does original99.75% accuracy fail to demonstrate generalization? Explain the duplicate audit and original training membership.
- What happens when a model file is missing? Readiness503 and controlled unavailable inference.
- How is rollback different from a successful redeployment? Previous traffic must actually be restored and verified after candidate failure.
- Does min 0 mean every service is free while idle? Serving can reach zero, but registry, monitoring and storage have their own costs.
- Can the alert diagnose every camera fault? No; it detects collapsed dynamic range, not arbitrary blur, color shifts or data drift.
- Can another student reproduce identical numbers? Source/data/dependencies/seed/procedure are recorded; hardware arithmetic can differ.
