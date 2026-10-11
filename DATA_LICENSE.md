# Dataset attribution and modifications

Prepared images and the small image fixtures are licensed under **CC BY-SA 4.0**. License: https://creativecommons.org/licenses/by-sa/4.0/ . Preserve this attribution and share adapted dataset material under the same license; the data license does not automatically determine a model-weight license.

Sources, both version 1 (primary Kaggle API metadata captured in `provenance/dataset_sources.json`):

1. Gerry (gpiosenka), *Coffee Bean Dataset Resized (224 X 224)*: https://www.kaggle.com/datasets/gpiosenka/coffee-bean-dataset-resized-224-x-224
2. Sakdipat Ontoum (sot2542), *Coffee Bean Dataset Version1*: https://www.kaggle.com/datasets/sot2542/coffee-bean-dataset-v1

Requested research citation: Ontoum, S., Khemanantakul, T., Sroison, P., Triyason, T., & Watanapa, B. (2022). *Coffee Roast Intelligence*. arXiv:2206.01841. https://doi.org/10.48550/arXiv.2206.01841

Modifications by Peerawat Somsurat, student 6688218: exact-pixel deduplication, content-hash filenames, deterministic stratified resplitting with seed 42, and a provenance manifest. No image pixel changes were made. The provided resized dataset has 1,600 entries and 1,194 unique images. Removed 406 duplicate copies; new train/validation/test sizes are 835/178/181. The source's entire 400-image test split duplicated source training images. Imported Iteration4 results are a contaminated historical baseline.

Different coffee origins associated with roast labels may confound learning. Random image splits do not establish generalization to new farms, cameras, batches, or controlled roasting experiments.
