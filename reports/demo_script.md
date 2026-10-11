# Eight minute demonstration script

This script is rehearsal material. Live attendance, instructor approval and Q&A completion must be recorded after the actual events. Use actual evidence and disclose pending steps; never present a generated template as live proof.

## 0:00 to 1:00 Problem and scope

“We provide image-level coffee roast classification for visual inspection: Dark, Green, Light and Medium. Green is unroasted. We revised the original defect proposal because our supplied Iteration4 model and data classify roast. This does not certify SCA defects or individual beans.” Show one licensed fixture per class. State instructor scope approval status.

## 1:00 to 2:00 Data and reproducibility

Show the DVC pointers, locked environment, source attribution and manifest. “Our audit found that all400 original test images duplicated original training images. We preserved that checkpoint as a historical baseline. The corrected splits contain835/178/181 images with no exact duplicates. The release records its actual Git commit, seed, initialization, parameters, dependencies and hashes.” Show clean restoration evidence and the training command; do not start20epoch training during the demo.

## 2:00 to 3:00 Architecture and release safety

Walk through private Blob DVC storage, automated training, Azure ML registration, CI, digest-pinned Container Apps and the Azure workbook. Explain2vCPU/4GiB, bounded concurrency2, min0/max2, managed identity and OIDC. Show the release's candidate checks and promotion receipt or clearly state if pending.

## 3:00 to 4:00 Live prediction and unexpected inputs

Submit a real coffee PNG to `/predict`, then a base64 JPEG/PNG to `/predict/base64`. Point to four finite probabilities, fixed class IDs and matching version headers. Invite the instructor to provide an unexpected input. Explain415 unsupported image format,413 size limits,400 unreadable bytes and422 invalid schema. A probability is uncalibrated confidence and arbitrary noncoffee photos can pass the optical guard.

## 4:00 to 5:00 Deliberate camera failure

Submit black and white frames. Show422 before inference, the structured rejection log, anomaly counter and workbook records. Explain that the failure models a covered or overexposed camera. Show the real fired Azure alert and delivered email receipt when available; five-minute evaluation and delivery can exceed the remaining demo time, so trigger ahead and retain timestamped evidence. Restore a valid image and show recovery.

## 5:00 to 6:00 Regression and rollback

Show the isolated optical guard mutation and the deliberately failed GitHub CI run, plus evidence that release was skipped. Show the candidate rollback receipt if exercised. “The failure informed a regression assertion: uniform images must be rejected before the model is called.” Show failed readiness for a missing/corrupt artifact using isolated evidence; do not damage the production bundle during presentation.

## 6:00 to 7:00 Performance and cost

Show the actual1,000-request concurrency2 warm report,20 zero-replica cold trials, frozen p95/p99 targets and image bytes separately. Explain client network latency versus server scoring latency. Show cost/1,000 using deployed allocation and measured duration, with separate storage, registry, monitoring and local training. Discuss remaining800THB allowance and50/80/100% budget notifications. State estimates versus invoiced charges clearly.

## 7:00 to 8:00 Limits and completion

Show the requirement checklist and safe teardown record, with the shared Azure ML workspace preserved. Explain source/camera confounding, uncalibrated confidence, absence of near-duplicate guarantees and limited dataset size. “Another week would buy new independently captured images and calibration, plus broader camera-condition checks.” State any technical evidence still pending and the external academic milestones. Finish before8:00; reserve5minutes for Q&A.

## Questions to prepare

- Why does original99.75% accuracy fail to demonstrate generalization? Explain the duplicate audit and original training membership.
- What happens when a model file is missing? Readiness503 and controlled unavailable inference.
- How is rollback different from a successful redeployment? Previous traffic must actually be restored and verified after candidate failure.
- Does min0 mean every service is free while idle? Serving can reach zero, but registry, monitoring and storage have their own costs.
- Can the alert diagnose every camera fault? No; it detects collapsed dynamic range, not arbitrary blur, color shifts or data drift.
- Can another student reproduce identical numbers? Source/data/dependencies/seed/procedure are recorded; hardware arithmetic can differ.
