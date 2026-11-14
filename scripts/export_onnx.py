"""Export trained model to ONNX format and validate parity.

Usage:
    PYTHONPATH=/d /c/Python314/python scripts/export_onnx.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Make repo root importable so `configs` and `src.*` resolve when running
# `python scripts/export_onnx.py` directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from configs import load_config
from src.vision.model import build_model
from src.vision.transforms import eval_transforms

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main():
    cfg = load_config("data")
    tcfg = load_config("train")
    ckpt_path = Path(tcfg["best_checkpoint"])
    out_dir = Path(tcfg["onnx_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "agridoc_cv.onnx"

    classes = json.loads(Path(cfg["classes_manifest"]).read_text(encoding="utf-8"))
    n_classes = len(classes)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    log.info("building model: %s, %d classes", tcfg["backbone"], n_classes)
    model = build_model(backbone=tcfg["backbone"], num_classes=n_classes, pretrained=False)
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model"], strict=False)
    model.to(device)
    model.eval()

    log.info("exporting to ONNX → %s", out_path)
    dummy_input = torch.randn(1, 3, 224, 224, device=device)
    torch.onnx.export(
        model,
        dummy_input,
        str(out_path),
        opset_version=18,
        input_names=["image"],
        output_names=["probabilities"],
        dynamic_axes={
            "image": {0: "batch_size"},
            "probabilities": {0: "batch_size"},
        },
        verbose=False,
    )
    sz = out_path.stat().st_size
    log.info("ONNX model saved (%.1f MB)", sz / 1e6)

    # Validate parity: compare PyTorch softmax vs ONNX output on a test batch
    log.info("validating parity with a test batch...")
    from src.vision.plantvillage import PlantVillageDataset
    from torch.utils.data import DataLoader

    ds = PlantVillageDataset("test", eval_transforms())
    loader = DataLoader(ds, batch_size=16, shuffle=False, num_workers=2)
    x, _ = next(iter(loader))
    x_dev = x.to(device)

    with torch.no_grad():
        py_logits = model(x_dev)
        py_probs = torch.softmax(py_logits, dim=1).cpu().numpy()

    # Run ONNX inference
    import onnxruntime as ort
    sess = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
    onnx_logits = sess.run(None, {"image": x.numpy()})[0]
    onnx_probs = torch.softmax(torch.tensor(onnx_logits), dim=1).numpy()

    diff = np.abs(py_probs - onnx_probs).max()
    top1_match = (py_probs.argmax(axis=1) == onnx_probs.argmax(axis=1)).mean()
    top3_match = ((py_probs.argsort(axis=1)[:, -3:] == onnx_probs.argsort(axis=1)[:, -3:]).any(axis=1)).mean()

    log.info("diff max           : %.6f", diff)
    log.info("top-1 match        : %.4f", top1_match)
    log.info("top-3 match        : %.4f", top3_match)

    if diff > 1e-4:
        log.warning("WARNING: ONNX parity diff %.6f > 1e-4", diff)
    else:
        log.info("parity OK (diff <= 1e-4)")

    # Save metadata
    meta = {
        "backbone": tcfg["backbone"],
        "num_classes": n_classes,
        "classes": classes,
        "checkpoint": str(ckpt_path),
        "input_size": [1, 3, 224, 224],
        "opset_version": 18,
        "model_size_bytes": sz,
        "parity_diff_max": float(diff),
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("metadata saved: %s", meta_path)
    return meta


if __name__ == "__main__":
    main()
