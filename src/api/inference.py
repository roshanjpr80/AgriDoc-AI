"""ONNX-backed inference for the crop-disease classifier.

Loads models/artifacts/agridoc_cv.onnx + agridoc_cv.onnx.json once at startup
and serves top-k predictions with confidence scores. Runs on CPU, in the
browser via ONNX Runtime Web, or on the desktop — no PyTorch needed at runtime.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

from configs import load_config
from src.vision.transforms import eval_transforms

_cfg = load_config("data")
_SIZE = int(_cfg["image_size"])
_FLOOR = float(_cfg["confidence_floor"])
_TOP_K = int(_cfg["top_k"])

from configs import PKG_ROOT

_model_path = PKG_ROOT / load_config("advice")["onnx_model"]
_labels_path = PKG_ROOT / load_config("advice").get("onnx_labels", "models/artifacts/agridoc_cv.onnx.json")

_session = None
_LABELS: List[str] = []


def _ensure_model_available():
    """Download model from HuggingFace if not present locally."""
    if _model_path.exists():
        return True

    # Try downloading from HuggingFace
    hf_url = "https://huggingface.co/roshanjpr80/agridoc-model/resolve/main/agridoc_cv.onnx"
    print(f"[AgriDoc] Downloading model from {hf_url}...")

    try:
        import requests
        response = requests.get(hf_url, timeout=120, stream=True)
        response.raise_for_status()
        _model_path.parent.mkdir(parents=True, exist_ok=True)

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(_model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        print(f"[OK] Model downloaded: {_model_path.stat().st_size / 1024:.1f} KB")
        return True
    except Exception as e:
        print(f"[ERROR] Could not download model: {e}")
        return False


def _load():
    global _session, _LABELS
    if _session is not None:
        return

    # Ensure model exists
    if not _ensure_model_available():
        raise RuntimeError(
            f"Model not found at {_model_path} and could not download from HuggingFace.\n"
            "Run: python scripts/download_model.py\n"
            "Or upload the model to https://huggingface.co/ and provide URL."
        )

    import onnxruntime as ort
    _session = ort.InferenceSession(str(_model_path), providers=["CPUExecutionProvider"])
    if _labels_path.exists():
        _LABELS = json.loads(_labels_path.read_text(encoding="utf-8"))
    else:
        _LABELS = json.loads(Path(_cfg["classes_manifest"]).read_text(encoding="utf-8"))


def _preprocess(img) -> np.ndarray:
    """Resize + ImageNet normalise using PIL + numpy (no torch dependency).

    Returns a (1, 3, H, W) float32 array ready for ONNX inference.
    """
    img = img.resize((_SIZE, _SIZE), Image.BILINEAR)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    # HWC -> CHW
    arr = arr.transpose(2, 0, 1)
    # ImageNet normalisation
    arr[0] = (arr[0] - _IMAGENET_MEAN[0]) / _IMAGENET_STD[0]
    arr[1] = (arr[1] - _IMAGENET_MEAN[1]) / _IMAGENET_STD[1]
    arr[2] = (arr[2] - _IMAGENET_MEAN[2]) / _IMAGENET_STD[2]
    return arr[None, ...]


# ImageNet stats (matches transforms.py)
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


def predict(image_bytes: bytes, top_k: int = _TOP_K) -> dict:
    """Run inference on raw image bytes -> {predictions, confidence, uncertain}."""
    _load()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x = _preprocess(img)
    logits = _session.run(None, {"image": x})[0][0]
    probs = _softmax(logits)
    order = np.argsort(probs)[::-1]
    k = min(top_k, len(_LABELS))
    preds = [
        {"class": _LABELS[int(order[i])], "confidence": float(probs[int(order[i])])}
        for i in range(k)
    ]
    top = preds[0]["confidence"]
    return {
        "predictions": preds,
        "confidence": top,
        "uncertain": top < _FLOOR,
        "confidence_floor": _FLOOR,
    }


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def model_info() -> dict:
    _load()
    return {
        "model": _model_path.name,
        "size_mb": round(_model_path.stat().st_size / 1e6, 1),
        "classes": len(_LABELS),
        "runtime": "onnxruntime",
        "confidence_floor": _FLOOR,
    }