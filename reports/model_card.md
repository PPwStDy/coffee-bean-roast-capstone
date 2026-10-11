# Model Card: Coffee Bean Roast Classifier

| Field | Description |
|---|---|
| Model | Iteration4 PretrainedSwinT, 27,551,242 state entries including buffers |
| Class order | 0 Dark; 1 Green; 2 Light; 3 Medium |
| Input | RGB coffee bean image, 224 × 224; ImageNet mean/std |
| Checkpoint | Imported `models/iteration4_swin.pth`; strict state-dictionary loading |
| Runtime | ONNX Runtime CPU with dynamic INT8 dense weights; local TorchScript fallback |
| Dataset | 1,600 source images; 1,194 unique images; license/source unconfirmed |
| Prepared splits | 835 train, 178 validation, 181 test; seed 42; exact-pixel deduplication |
| Lineage | DVC dataset/checkpoint pointers; source manifest; MLflow imported-model registration |
| Maintainers | Peerawat Somsurat and Yongyot, ITCS355 Team Idea |

## Intended use

Classify the visual roast category of a coffee bean image. Green represents an unroasted bean. This model does not establish defect grades, sourness, mold contamination, or compliance with an SCA grading procedure. The optical guard rejects near-uniform images; it does not detect every out-of-distribution input or calibrate confidence.

## Evaluation limitations

The original saved summary reports 99.75% accuracy and macro F1 on 400 test images. **All 400 test images are exact pixel duplicates of images in the original training folder.** That result is contaminated and must not be presented as unbiased test accuracy. The original training code and summary are retained under `provenance/iteration4/`.

The imported checkpoint was not trained on the prepared splits. Creating these new splits cannot repair its learned exposure to the original images. Retrain from ImageNet weights on the prepared train split, or evaluate on genuinely new images, before claiming generalization. Neither has been performed during this migration. Similar views of the same physical bean could remain even after exact-pixel deduplication.

## Export and operations

Initial export: 29.6 MiB quantized ONNX. Nine parity inputs passed with maximum probability difference 0.0087 and identical predicted classes. Local one-thread CPU p50 was 93 ms, p95 185 ms; the 120 ms p95 target was missed. See `reports/model_metadata.json` for hashes and actual runtime versions.

Docker size, cold-start time, deployed latency, cloud cost, and scale-to-zero are unverified. The earlier MobileNet cost and size assumptions need recalculation for Swin-T. Source/license attribution must be established before redistributing the new dataset.
