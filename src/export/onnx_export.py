"""Export the trained classifier to ONNX and validate parity.

The ONNX model is the *runtime* artifact: it decouples inference from the
training framework and runs on CPU, on the desktop, and in the browser via
ONNX Runtime Web. The PyTorch checkpoint is kept for retraining only.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import torch

from configs import load_config, PKG_ROOT
from src.vision.model import build_model
from src.vision.transforms import eval_transforms
from src.vision.plantvillage import PlantVillageDataset

logger = logging.getLogger(__name__)

_dcfg = load_config("data")
_tcfg = load_config("train")
_LABELS = Path(_dcfg["classes_manifest"])
_SIZE = int(_dcfg["image_size"])


def _load_state(path: Path) -> dict:
    # weights_only=True: the checkpoint is tensors + metadata only, no code.
    ck = torch.load(path, map_location="cpu", weights_only=True)
    return ck["model"] if isinstance(ck, dict) and "model" in ck else ck


def export(onnx_path: Path, checkpoint: Path, opset: int = 14) -> None:
    onnx_path = Path(onnx_path)
    if not onnx_path.is_absolute():
        onnx_path = PKG_ROOT / onnx_path
    if not Path(checkpoint).is_absolute():
        checkpoint = PKG_ROOT / checkpoint
    """Export best.pt -> onnx_path, with a parity assertion against PyTorch."""
    classes = json.loads(_LABELS.read_text(encoding="utf-8"))
    model = build_model(backbone=_tcfg["backbone"], num_classes=len(classes), pretrained=False)
    model.load_state_dict(_load_state(checkpoint))
    model.eval()

    dummy = torch.randn(1, 3, _SIZE, _SIZE)
    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names=["input"], output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=opset,
    )
    logger.info("exported %s (%.1f MB)", onnx_path, onnx_path.stat().st_size / 1e6)

    # Parity check: ONNX logits must track PyTorch within tolerance.
    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ds = PlantVillageDataset("val", eval_transforms())
    n = min(200, len(ds))
    rng = np.random.default_rng(0)
    idxs = rng.choice(len(ds), size=n, replace=False)
    max_diff = 0.0
    for i in idxs:
        x, y = ds[int(i)]
        xb = x.unsqueeze(0).numpy()
        pt = model(torch.from_numpy(xb)).detach().numpy()
        onx = sess.run(None, {"input": xb})[0]
        max_diff = max(max_diff, float(np.abs(pt - onx).max()))
    assert max_diff < 1e-3, f"ONNX/PyTorch parity failed: max diff {max_diff:.2e}"
    logger.info("parity OK: max logit diff over %d val images = %.2e", n, max_diff)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, default=Path("models/checkpoints/best.pt"))
    ap.add_argument("--out", type=Path, default=Path("models/artifacts/agridoc_cv.onnx"))
    ap.add_argument("--opset", type=int, default=14)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    export(a.out, a.checkpoint, a.opset)
    # Save labels next to the model so the runtime needs only two files.
    labels_out = a.out.with_suffix(".json")
    labels_out.write_text(_LABELS.read_text(encoding="utf-8"), encoding="utf-8")
    logger.info("labels -> %s", labels_out)