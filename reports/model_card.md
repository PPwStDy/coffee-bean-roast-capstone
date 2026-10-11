# Model card: roast-swin-retrained-v1

Swin-T; Dark, Green, Light, Medium. RGB224, ImageNet normalization.

Training: 763915a0b9d05af803194239a3601a4a15dfa08f; dataset d241ed318d2c1d8672d939938d3b71be.dir; seed 42, ImageNet initialization.

Selected export: dynamic_int8_dense_weights; held-out test n=181, accuracy=1.0000, macro-F1=1.0000.

Intended use: educational image-level roast classification, never individual-bean defect grading. CC BY-SA 4.0 dataset; see DATA_LICENSE.md. Different origins and camera conditions can confound labels. Confidence is uncalibrated. Solid frames rejected optically; arbitrary out-of-domain images can pass. Original Iteration4 baseline saw all original test images and is unsuitable for generalization claims.
