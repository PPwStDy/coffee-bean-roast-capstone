import torch
import torch.nn as nn
import torchvision.models as models

class PretrainedViT_B_16(nn.Module):
    """
    Vision Transformer (ViT-B/16) - Top performing architecture in Iteration 3.
    """
    def __init__(self, num_classes=4, fine_tune=True):
        super(PretrainedViT_B_16, self).__init__()
        self.vit = models.vit_b_16(weights=models.ViT_B_16_Weights.DEFAULT)

        if not fine_tune:
            for param in self.vit.parameters():
                param.requires_grad = False
        else:
            # Unfreeze top encoder blocks, layer norm, and head
            for name, param in self.vit.named_parameters():
                if any(x in name for x in ["encoder.layers.10", "encoder.layers.11", "encoder.ln", "heads"]):
                    param.requires_grad = True
                else:
                    param.requires_grad = False

        num_ftrs = self.vit.heads.head.in_features
        self.vit.heads.head = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_ftrs, num_classes)
        )

    def forward(self, x):
        return self.vit(x)

    def get_param_groups(self, backbone_lr=5e-5, head_lr=1e-3, weight_decay=0.01):
        head_params = list(self.vit.heads.head.parameters())
        head_ids = set(id(p) for p in head_params)
        backbone_params = [p for p in self.parameters() if p.requires_grad and id(p) not in head_ids]
        return [
            {'params': backbone_params, 'lr': backbone_lr, 'weight_decay': weight_decay},
            {'params': head_params, 'lr': head_lr, 'weight_decay': weight_decay}
        ]


class PretrainedSwinT(nn.Module):
    """
    Swin Transformer Tiny - Modern hierarchical vision transformer with shifted windows.
    Efficient parameter count (~28M) and excellent spatial-attentive representation.
    """
    def __init__(self, num_classes=4, fine_tune=True):
        super(PretrainedSwinT, self).__init__()
        self.swin = models.swin_t(weights=models.Swin_T_Weights.DEFAULT)

        if not fine_tune:
            for param in self.swin.parameters():
                param.requires_grad = False
        else:
            # Fine-tune later stages, norm, and classification head
            for name, param in self.swin.named_parameters():
                if any(x in name for x in ["features.6", "features.7", "norm", "head"]):
                    param.requires_grad = True
                else:
                    param.requires_grad = False

        num_ftrs = self.swin.head.in_features
        self.swin.head = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_ftrs, num_classes)
        )

    def forward(self, x):
        return self.swin(x)

    def get_param_groups(self, backbone_lr=5e-5, head_lr=1e-3, weight_decay=0.01):
        head_params = list(self.swin.head.parameters())
        head_ids = set(id(p) for p in head_params)
        backbone_params = [p for p in self.parameters() if p.requires_grad and id(p) not in head_ids]
        return [
            {'params': backbone_params, 'lr': backbone_lr, 'weight_decay': weight_decay},
            {'params': head_params, 'lr': head_lr, 'weight_decay': weight_decay}
        ]


class PretrainedEfficientNetV2S(nn.Module):
    """
    EfficientNetV2-S - Fast, progressive training architecture.
    Lightweight (~21M parameters) and exceptionally fast convergence.
    """
    def __init__(self, num_classes=4, fine_tune=True):
        super(PretrainedEfficientNetV2S, self).__init__()
        self.efficientnet = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)

        if not fine_tune:
            for param in self.efficientnet.parameters():
                param.requires_grad = False
        else:
            for name, param in self.efficientnet.named_parameters():
                if any(x in name for x in ["features.6", "features.7", "classifier"]):
                    param.requires_grad = True
                else:
                    param.requires_grad = False

        num_ftrs = self.efficientnet.classifier[1].in_features
        self.efficientnet.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_ftrs, num_classes)
        )

    def forward(self, x):
        return self.efficientnet(x)

    def get_param_groups(self, backbone_lr=1e-4, head_lr=1e-3, weight_decay=0.01):
        head_params = list(self.efficientnet.classifier.parameters())
        head_ids = set(id(p) for p in head_params)
        backbone_params = [p for p in self.parameters() if p.requires_grad and id(p) not in head_ids]
        return [
            {'params': backbone_params, 'lr': backbone_lr, 'weight_decay': weight_decay},
            {'params': head_params, 'lr': head_lr, 'weight_decay': weight_decay}
        ]


class PretrainedConvNeXtTiny(nn.Module):
    """
    ConvNeXt Tiny - Pure convolutional architecture with transformer-like design.
    Note: On macOS MPS backend, ConvNeXt may require CPU or CUDA due to MPS non-contiguous view kernel.
    """
    def __init__(self, num_classes=4, fine_tune=True):
        super(PretrainedConvNeXtTiny, self).__init__()
        self.convnext = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)

        if not fine_tune:
            for param in self.convnext.parameters():
                param.requires_grad = False
        else:
            for name, param in self.convnext.named_parameters():
                if any(x in name for x in ["features.6", "features.7", "classifier"]):
                    param.requires_grad = True
                else:
                    param.requires_grad = False

        num_ftrs = self.convnext.classifier[2].in_features
        self.convnext.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_ftrs, num_classes)
        )

    def forward(self, x):
        return self.convnext(x)

    def get_param_groups(self, backbone_lr=5e-5, head_lr=1e-3, weight_decay=0.01):
        head_params = list(self.convnext.classifier.parameters())
        head_ids = set(id(p) for p in head_params)
        backbone_params = [p for p in self.parameters() if p.requires_grad and id(p) not in head_ids]
        return [
            {'params': backbone_params, 'lr': backbone_lr, 'weight_decay': weight_decay},
            {'params': head_params, 'lr': head_lr, 'weight_decay': weight_decay}
        ]
