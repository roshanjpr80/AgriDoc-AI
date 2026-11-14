"""EfficientNet, MobileNetV3, and EfficientNet-V2 model factory for AgriDoc AI.

Backbone is configurable in ``configs/train.yaml`` (default EfficientNet-B0).
The classifier head is replaced with a fresh dropout + linear layer so the
pretrained ImageNet features are kept and only the task head is trained at
first; the backbone is unfrozen later for fine-tuning.

Grad-CAM needs the last convolutional layer. For each architecture:
- EfficientNet: ``model.features[-1]`` (the final MBConv block)
- MobileNetV3: ``model.features[-1]`` (the final feature block)
- EfficientNet-V2: ``model.features[-1]`` (the final MBConv block)
and it is exposed as ``model.grad_cam_target`` so the explain module does not need to
know the architecture.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tvm

# Import MobileNetV3 and EfficientNet-V2-B2 implementations
from .mobilenet_v3 import build_mobilenet_v3
from .efficientnet_v2_b2 import build_efficientnet_v2_b2
from configs import load_config

# Map of backbone name -> torchvision builder. All are EfficientNet variants;
# EfficientNetV2-S is the one backend/config.py already defaults to.
_BACKBONES = {
    "efficientnet_b0": tvm.efficientnet_b0,
    "efficientnet_b1": tvm.efficientnet_b1,
    "efficientnet_b2": tvm.efficientnet_b2,
    "efficientnet_b3": tvm.efficientnet_b3,
    "efficientnet_v2_s": tvm.efficientnet_v2_s,
    "efficientnet_v2_m": tvm.efficientnet_v2_m,
}

# Add MobileNetV3 and EfficientNet-V2-B2 to the model factory
_BACKBONES["mobilenet_v3"] = build_mobilenet_v3
_BACKBONES["efficientnet_v2_b2"] = build_efficientnet_v2_b2
def build_model(
    backbone: str = "efficientnet_b0",
    num_classes: int = 38,
    pretrained: bool = True,
    dropout: float = 0.35,
) -> nn.Module:
    """Build a classifier with a frozen/unfreezable backbone.

    Args:
        backbone: key into _BACKBONES (from configs/train.yaml).
        num_classes: number of output classes (from classes.json).
        pretrained: download ImageNet weights on first run.
        dropout: classifier-head dropout for regularisation.

    Returns:
        nn.Module with ``.grad_cam_target`` set to the last conv layer.
    """
    # Normalize backbone names: configs may use "efficientnet_v2b0" (no underscore)
    # while torchvision uses "efficientnet_v2_b0". Accept both forms.
    key = backbone.replace("v2", "v2_") if backbone.startswith("efficientnet_v2") else backbone
    if key not in _BACKBONES:
        raise ValueError(
            f"Unknown backbone '{backbone}'. Choose from {sorted(_BACKBONES)}"
        )
    builder = _BACKBONES[key]

    # For MobileNetV3 and EfficientNet-V2-B2, the builder is already the build function
    if backbone in ["mobilenet_v3", "efficientnet_v2_b2"]:
        return builder(backbone=backbone, num_classes=num_classes, pretrained=pretrained, dropout=dropout)

    # For EfficientNet variants, use the standard torchvision builder
    # torchvision's verify() requires the full weights-enum name, not "IMAGENET".
    weights = "IMAGENET1K_V1" if pretrained else None
    model = builder(weights=weights)

    # Replace the classifier head. EfficientNet heads end in a Linear(1280 -> C);
    # we rebuild it with configurable dropout so the head capacity matches the
    # task and the dropout value is a real hyperparameter.
    in_features = model.classifier[-1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout, inplace=True),
        nn.Linear(in_features, num_classes),
    )

    # Grad-CAM target: last conv layer of the feature extractor.
    model.grad_cam_target = model.features[-1]
    model.backbone_name = backbone
    return model
def param_groups(model: nn.Module, backbone_lr_scale: float = 0.1) -> List[Dict]:
    """Split model params into head and backbone groups.

    The head is trained at the base learning rate; the backbone at
    ``backbone_lr_scale * base_lr`` once it is unfrozen. This matches the
    common transfer-learning pattern: the randomly initialised head needs to
    move fast, the pretrained backbone needs to move slowly.
    """
    head_params: List[nn.Parameter] = []
    backbone_params: List[nn.Parameter] = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if name.startswith("classifier"):
            head_params.append(p)
        else:
            backbone_params.append(p)
    return [
        {"params": head_params, "lr_scale": 1.0},
        {"params": backbone_params, "lr_scale": backbone_lr_scale},
    ]
def freeze_backbone(model: nn.Module) -> None:
    """Stop gradients flowing through the feature extractor."""
    for name, p in model.named_parameters():
        if not name.startswith("classifier"):
            p.requires_grad = False
def unfreeze_backbone(model: nn.Module) -> None:
    """Allow the whole model to train."""
    for p in model.parameters():
        p.requires_grad = True
def count_trainable(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# --------------------------------------------------------------------------- #
# Grad-CAM
# --------------------------------------------------------------------------- #

class GradCAM:
    """Gradient-weighted Class Activation Mapping.

    Highlights the leaf regions that drove the prediction -- the Subramaniam &
    Pillai (2024) finding is that visual explanations materially increase
    farmer trust in AI diagnostics.
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients: torch.Tensor | None = None
        self.activations: torch.Tensor | None = None
        target_layer.register_forward_hook(self._save_activations)
        target_layer.register_full_backward_hook(self._save_gradients)

    def _save_activations(self, _module, _input, output):
        self.activations = output.detach()

    def _save_gradients(self, _module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def __call__(self, input_tensor: torch.Tensor, class_idx: int) -> np.ndarray:
        self.model.zero_grad()
        logits = self.model(input_tensor)
        if logits.ndim == 1:
            logits = logits.unsqueeze(0)
        target = torch.zeros_like(logits)
        target[0, class_idx] = 1.0
        logits.backward(target)
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = cam / (cam.max() + 1e-8)
        cam = torch.nn.functional.interpolate(
            cam, size=(224, 224),
            mode="bilinear", align_corners=False,
        )
        return cam.squeeze().cpu().numpy()


def _find_target_layer(model: nn.Module) -> nn.Module:
    """Last convolutional block of EfficientNet."""
    return model.features[-1]