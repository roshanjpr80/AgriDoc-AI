"""Grad-CAM overlay rendering for the API.

Loads the PyTorch checkpoint (only needed at export/overlay time; the runtime
serves ONNX), computes a class-activation map over the predicted class, and
returns a PNG of the original image with the heatmap burned in. Farmers trust
a diagnosis more when they can see *which part of the leaf* the model looked at.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from configs import load_config
from src.vision.model import build_model, GradCAM
from src.vision.transforms import eval_transforms, denormalize

_dcfg = load_config("data")
_tcfg = load_config("train")
_ck_path = Path(_tcfg["best_checkpoint"])
_SIZE = int(_dcfg["image_size"])

_model = None
_cam = None


def _ensure():
    global _model, _cam
    if _model is not None:
        return
    import json
    classes = json.loads(Path(_dcfg["classes_manifest"]).read_text(encoding="utf-8"))
    ck = torch.load(_ck_path, map_location="cpu", weights_only=True)
    state = ck["model"] if isinstance(ck, dict) and "model" in ck else ck
    model = build_model(backbone=_tcfg["backbone"], num_classes=len(classes), pretrained=False)
    model.grad_cam_target = model.features[-1]
    model.load_state_dict(state, strict=False)
    model.eval()
    _model = model
    _cam = GradCAM(model, model.grad_cam_target)


def overlay_png(image: Image.Image, class_label: str) -> str:
    """Return base64 PNG of the image with the Grad-CAM heatmap burned in."""
    _ensure()
    import json
    classes = json.loads(Path(_dcfg["classes_manifest"]).read_text(encoding="utf-8"))
    idx = classes.index(class_label)
    x = eval_transforms()(image).unsqueeze(0)
    cam = _cam(x, idx).reshape(_SIZE, _SIZE)
    heatmap = _apply_heatmap(image, cam)
    buf = io.BytesIO()
    heatmap.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _apply_heatmap(image: Image.Image, cam: np.ndarray) -> Image.Image:
    """Burn a jet colormap heatmap over the original image at 50% alpha."""
    base = image.convert("RGB").resize((_SIZE, _SIZE))
    arr = np.asarray(base).astype(np.float32)
    cmap = _jet(cam)
    blended = (0.55 * arr + 0.45 * cmap).clip(0, 255).astype(np.uint8)
    return Image.fromarray(blended)


def _jet(cam: np.ndarray) -> np.ndarray:
    """8-bit jet colormap applied to a normalised [0,1] map -> (H,W,3) uint8."""
    c = np.clip(cam, 0, 1)
    r = np.clip((1.5 - 2.0 * c) * 255, 0, 255)
    g = np.clip((2.0 * c - 0.5) * 255, 0, 255)
    b = np.clip((2.0 * c - 1.5) * 255, 0, 255)
    h, w = c.shape
    return np.stack([r, g, b], axis=-1)