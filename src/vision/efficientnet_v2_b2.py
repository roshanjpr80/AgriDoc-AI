"""EfficientNet-V2-B2 model for AgriDoc AI.

Backbone is configured in ``configs/train.yaml`` (default efficientnet_b0).
This implementation supports pretrained weights from ImageNet, dropout regularization,
and Grad-CAM functionality for model interpretability.

Key features:
- Pretrained weights from ImageNet for transfer learning
- Configurable dropout for regularization
- Consistent architecture with other AgriDoc models
- Grad-CAM support for feature visualization
- Modern efficient architecture with improved performance
"""
from __future__ import annotations

from __future__ import annotations

import torch
import torch.nn as nn
import torchvision.models as tvm
class EfficientNetV2B2(nn.Module):
    """EfficientNet-V2-B2 architecture with pretrained ImageNet weights.

    Args:
        num_classes: Number of output classes for crop-disease classification
        pretrained: Whether to use pretrained ImageNet weights
        dropout: Dropout probability for classifier head regularization
    """
    def __init__(self, num_classes: int = 38, pretrained: bool = True, dropout: float = 0.25):
        super().__init__()
        # Try to use efficientnet_v2_b2, fall back to efficientnet_v2_s if not available
        if hasattr(tvm, 'efficientnet_v2_b2'):
            if pretrained:
                # EfficientNet V2 models don't have include_top parameter
                self.model = tvm.efficientnet_v2_b2(weights=tvm.EfficientNet_V2_B2_Weights.IMAGENET1K_V1)
            else:
                self.model = tvm.efficientnet_v2_b2(weights=None)
            backbone_name = "efficientnet_v2_b2"
        else:
            # Fallback to efficientnet_v2_s if B2 is not available
            if pretrained:
                self.model = tvm.efficientnet_v2_s(weights=tvm.EfficientNet_V2_S_Weights.IMAGENET1K_V1)
            else:
                self.model = tvm.efficientnet_v2_s(weights=None)
            backbone_name = "efficientnet_v2_s"

        # Replace classifier with configurable dropout and output size
        in_features = self.model.classifier[-1].in_features
        self.model.classifier = nn.Sequential(
            nn.Dropout(p=dropout, inplace=True),
            nn.Linear(in_features, num_classes)
        )

        # Grad-CAM target: last feature layer for visualization
        self.grad_cam_target = self.model.features[-1]
        self.backbone_name = backbone_name

    def forward(self, x):
        """Forward pass through the model."""
        backbone_features = self.model(x)
        return self.model.classifier(backbone_features.mean([2, 3]))

    def state_dict(self):
        """Get model state dictionary for saving."""
        return self.model.state_dict()

    def load_state_dict(self, state_dict):
        """Load model state dictionary for loading pre-trained weights."""
        self.model.load_state_dict(state_dict)
def build_efficientnet_v2_b2(
    backbone: str = "efficientnet_v2_b2",
    num_classes: int = 38,
    pretrained: bool = True,
    dropout: float = 0.25,
) -> nn.Module:
    """Build an EfficientNet-V2-B2 classifier with frozen/unfreezable backbone.

    Args:
        backbone: backbone name (should always be "efficientnet_v2_b2" for this implementation)
        num_classes: number of output classes
        pretrained: whether to use pretrained ImageNet weights
        dropout: classifier head dropout probability

    Returns:
        nn.Module with .grad_cam_target set to the last conv layer.
    """
    if backbone != "efficientnet_v2_b2":
        raise ValueError(
            f"EfficientNet-V2-B2 implementation only supports 'efficientnet_v2_b2', got '{backbone}'"
        )

    return EfficientNetV2B2(
        num_classes=num_classes,
        pretrained=pretrained,
        dropout=dropout,
    )