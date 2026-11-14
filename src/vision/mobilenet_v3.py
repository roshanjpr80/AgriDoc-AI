"""MobileNetV3 model for AgriDoc AI.

Backbone is configured in ``configs/train.yaml`` (default efficientnet_b0).
This implementation supports pretrained weights from ImageNet, dropout regularization,
and Grad-CAM functionality for model interpretability.

Key features:
- Pretrained weights from ImageNet for transfer learning
- Configurable dropout for regularization
- Consistent architecture with other AgriDoc models
- Grad-CAM support for feature visualization
- Efficient architecture suitable for resource-constrained environments
"""
from __future__ import annotations

from __future__ import annotations

import torch
import torch.nn as nn
import torchvision.models as tvm
class MobileNetV3Small(nn.Module):
    """MobileNetV3 Small architecture with pretrained ImageNet weights.

    Args:
        num_classes: Number of output classes for crop-disease classification
        pretrained: Whether to use pretrained ImageNet weights
        dropout: Dropout probability for classifier head regularization
    """
    def __init__(self, num_classes: int = 38, pretrained: bool = True, dropout: float = 0.35):
        super().__init__()
        if pretrained:
            self.model = tvm.mobilenet_v3_small(weights=tvm.MobileNet_V3_Small_Weights.IMAGENET1K_V1, include_top=False)
        else:
            self.model = tvm.mobilenet_v3_small(weights=None, include_top=False)

        # Replace classifier with configurable dropout and output size
        # MobileNetV3 classifier is a Sequential, get in_features from the Linear layer
        # Find the Linear layer in the classifier Sequential
        linear_layer = None
        for layer in self.model.classifier:
            if isinstance(layer, nn.Linear):
                linear_layer = layer
                break

        if linear_layer is None:
            # Fallback for MobileNetV3 architecture
            in_features = self.model.classifier[-1].in_features
        else:
            in_features = linear_layer.in_features

        # Rebuild classifier with configurable dropout and output size
        self.model.classifier = nn.Sequential(
            nn.Dropout(p=dropout, inplace=True),
            nn.Linear(in_features, num_classes)
        )

        # Grad-CAM target: last feature layer for visualization
        self.grad_cam_target = self.model.features[-1]
        self.backbone_name = "mobilenet_v3"

    def forward(self, x):
        """Forward pass through the model."""
        features = self.model(x)
        return self.model.classifier(features.mean([2, 3]))

    def state_dict(self):
        """Get model state dictionary for saving."""
        return self.model.state_dict()

    def load_state_dict(self, state_dict):
        """Load model state dictionary for loading pre-trained weights."""
        self.model.load_state_dict(state_dict)
def build_mobilenet_v3(
    backbone: str = "mobilenet_v3",
    num_classes: int = 38,
    pretrained: bool = True,
    dropout: float = 0.35,
) -> nn.Module:
    """Build a MobileNetV3 classifier with frozen/unfreezable backbone.

    Args:
        backbone: backbone name (should always be "mobilenet_v3" for this implementation)
        num_classes: number of output classes
        pretrained: whether to use pretrained ImageNet weights
        dropout: classifier head dropout probability

    Returns:
        nn.Module with .grad_cam_target set to the last conv layer.
    """
    if backbone != "mobilenet_v3":
        raise ValueError(
            f"MobileNetV3 implementation only supports 'mobilenet_v3', got '{backbone}'"
        )

    return MobileNetV3Small(
        num_classes=num_classes,
        pretrained=pretrained,
        dropout=dropout,
    )