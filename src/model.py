"""Iteration4's Swin-T wrapper, preserving the checkpoint's state-dictionary keys."""
from __future__ import annotations

import torch.nn as nn
from torchvision.models import Swin_T_Weights, swin_t
from src.config import NUM_CLASSES


class PretrainedSwinT(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES, pretrained=False, fine_tune=True):
        super().__init__()
        self.swin = swin_t(weights=Swin_T_Weights.DEFAULT if pretrained else None)
        for name, parameter in self.swin.named_parameters():
            parameter.requires_grad = fine_tune and any(
                stage in name for stage in ("features.6", "features.7", "norm", "head")
            )
        self.swin.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(self.swin.head.in_features, num_classes))

    def forward(self, x):
        return self.swin(x)

    def get_param_groups(self, backbone_lr=5e-5, head_lr=1e-3, weight_decay=0.01):
        head = list(self.swin.head.parameters())
        head_ids = {id(p) for p in head}
        backbone = [p for p in self.parameters() if p.requires_grad and id(p) not in head_ids]
        return [{"params": backbone, "lr": backbone_lr, "weight_decay": weight_decay},
                {"params": head, "lr": head_lr, "weight_decay": weight_decay}]


def build_model(num_classes=NUM_CLASSES, pretrained=False):
    """Existing checkpoints load without downloading ImageNet weights."""
    return PretrainedSwinT(num_classes=num_classes, pretrained=pretrained)
