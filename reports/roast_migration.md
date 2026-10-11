# Roast classification migration

The user approved changing the capstone scope from defect grading to roast classification using Iteration4.

## Inspection

- Source dataset: 1,600 RGB images, all 224 × 224. CSV paths, labels, class indices, and file inventory agree.
- Classes: Dark (0), Green (1), Light (2), Medium (3).
- Source train: 300 per class. Source test: 100 per class.
- Unique images: Dark 295, Green 299, Light 300, Medium 300; total 1,194.
- Removed duplicate copies: 406. All 400 test images occur in the source train folder.
- Original checkpoint: Swin-T state dictionary, four-output head. ViT checkpoint also exists but is not the selected capstone model.
- Original 99.75% accuracy is recorded as a contaminated historical result.
- No roast-dataset license or attribution file was found.

## Changes implemented

The API, schemas, dataset loader, augmentation, architecture, export, Make targets, CI references, dashboard titles, and model card now use roast classification. The imported checkpoint retains Iteration4's `swin.*` key layout and requires no pretrained download for inference.

Source files are retained in `provenance/iteration4/`. DVC pointers version the imported checkpoint and prepared dataset. The prepared manifest preserves original-to-new file mapping and content hashes. Future training begins from ImageNet weights rather than the imported model.

Serving checks a metadata contract and artifact hashes so an old five-class defect artifact cannot be paired with the new labels. Existing data contracts now check pixel hashes rather than only filenames.

## Outstanding tasks

1. Update the submitted proposal and confirm the scope change with the instructor.
2. Establish the new dataset's source and license.
3. Retrain Swin-T on the clean split or collect independent evaluation images.
4. Run the regression suite and service load benchmark.
5. Address the initial local CPU p95 of 185 ms against the 120 ms objective.
6. Measure Docker size and cold start; revise the proposal's under-250 MB and under-2 s goals if needed.
7. Configure/push the shared DVC remote and demonstrate CI from a clean checkout.
8. Deploy to the chosen provider, verify the monitoring/alert loop, and record actual cost/teardown evidence.
9. Revise the historical presentation and comprehensive report for the new task and measured results.

## Work performed in this migration

The dataset was audited and materialized into disjoint exact-pixel splits. The checkpoint was imported, loaded strictly, exported, and registered in the local MLflow registry as coffee-bean-roast-classifier version 2. Export parity and an in-process CPU benchmark were performed by the exporter. The pytest suite, service load test, Docker build, full training, and cloud deployment were not run.
