"""Evaluate trained model on test set: accuracy, per-class P/R/F1, confusion matrix, calibration.

Usage:
    PYTHONPATH=/d /c/Python314/python scripts/evaluate.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Make repo root importable so `configs` and `src.*` resolve when running
# `python scripts/evaluate.py` directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

from configs import load_config
from src.vision.model import build_model
from src.vision.plantvillage import PlantVillageDataset
from src.vision.transforms import eval_transforms

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """Expected Calibration Error (ECE) using equal-width bins."""
    confidences = probs.max(axis=1)
    preds = probs.argmax(axis=1)
    correct = (preds == labels).astype(float)

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bin_boundaries[:-1], bin_boundaries[1:]):
        mask = (confidences > lo) & (confidences <= hi)
        if mask.sum() == 0:
            continue
        bin_acc = correct[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += mask.sum() / len(confidences) * abs(bin_acc - bin_conf)
    return float(ece)


def main():
    cfg = load_config("data")
    tcfg = load_config("train")
    ckpt_path = Path(tcfg["best_checkpoint"])

    classes = json.loads(Path(cfg["classes_manifest"]).read_text(encoding="utf-8"))
    n_classes = len(classes)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("device=%s backbone=%s", device, tcfg["backbone"])

    # Load model
    model = build_model(backbone=tcfg["backbone"], num_classes=n_classes, pretrained=False)
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model"], strict=False)
    model.to(device)
    model.eval()
    log.info("loaded checkpoint %s (%.1f MB)", ckpt_path.name, ckpt_path.stat().st_size / 1e6)

    # Test dataset
    test_ds = PlantVillageDataset("test", eval_transforms())
    from torch.utils.data import DataLoader

    test_loader = DataLoader(
        test_ds, batch_size=64, shuffle=False, num_workers=2
    )

    all_labels = []
    all_probs = []
    for x, y in test_loader:
        x, y = x.to(device), y.to(device)
        with torch.no_grad():
            logits = model(x)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
        all_probs.append(probs)
        all_labels.append(y.cpu().numpy())

    all_probs = np.concatenate(all_probs, axis=0)
    all_labels = np.concatenate(all_labels, axis=0)

    preds = all_probs.argmax(axis=1)
    overall_acc = (preds == all_labels).mean()

    # Per-class metrics (zero_division handles classes with no test samples)
    precision, recall, f1, support = precision_recall_fscore_support(
        all_labels, preds, labels=list(range(n_classes)), average=None, zero_division=0
    )
    macro_precision = precision.mean()
    macro_recall = recall.mean()
    macro_f1 = f1.mean()

    # Calibration
    ece = compute_ece(all_probs, all_labels)

    # Top-1 and top-3 accuracy
    top1_acc = overall_acc
    top3_acc = (all_probs.argsort(axis=1)[:, -3:] == all_labels[:, None]).any(axis=1).mean()

    # Confusion matrix
    cm = confusion_matrix(all_labels, preds)

    # Confidence floor analysis
    floor = float(cfg["confidence_floor"])
    confident_mask = all_probs.max(axis=1) >= floor
    confident_acc = (preds[confident_mask] == all_labels[confident_mask]).mean()
    confident_ratio = confident_mask.mean()

    log.info("=" * 60)
    log.info("TEST SET EVALUATION")
    log.info("=" * 60)
    log.info("Test samples : %d", len(all_labels))
    log.info("Classes      : %d", n_classes)
    log.info("")
    log.info("--- Overall ---")
    log.info("Top-1 accuracy  : %.4f (%.2f%%)", top1_acc, top1_acc * 100)
    log.info("Top-3 accuracy  : %.4f (%.2f%%)", top3_acc, top3_acc * 100)
    log.info("Macro Precision : %.4f", macro_precision)
    log.info("Macro Recall    : %.4f", macro_recall)
    log.info("Macro F1        : %.4f", macro_f1)
    log.info("ECE (calibration): %.4f", ece)
    log.info("")
    log.info("--- Confidence Floor (%.0f%%) ---", floor * 100)
    log.info("Confident ratio : %.2f%%", confident_ratio * 100)
    log.info("Confident acc   : %.4f", confident_acc)
    log.info("")
    log.info("--- Per-Class ---")
    log.info("%-50s %8s %8s %8s %8s", "Class", "Prec", "Rec", "F1", "Support")
    log.info("-" * 80)
    for i, cls in enumerate(classes):
        log.info(
            "%-50s %8.4f %8.4f %8.4f %8d",
            cls[:50], precision[i], recall[i], f1[i], support[i],
        )
    log.info("")
    log.info("--- Confusion Matrix (%dx%d) ---", n_classes, n_classes)
    log.info(cm)

    # Save report
    report_dir = Path(tcfg["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "test_report.json"

    report = {
        "overall": {
            "top1_accuracy": float(top1_acc),
            "top3_accuracy": float(top3_acc),
            "macro_precision": float(macro_precision),
            "macro_recall": float(macro_recall),
            "macro_f1": float(macro_f1),
            "ece": float(ece),
        },
        "confidence_floor": {
            "floor": floor,
            "confident_ratio": float(confident_ratio),
            "confident_accuracy": float(confident_acc),
        },
        "per_class": [
            {"class": classes[i], "precision": float(precision[i]), "recall": float(recall[i]),
             "f1": float(f1[i]), "support": int(support[i])}
            for i in range(n_classes)
        ],
        "confusion_matrix": cm.tolist(),
        "checkpoint": str(ckpt_path),
        "backbone": tcfg["backbone"],
        "num_classes": n_classes,
        "test_samples": len(all_labels),
    }

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Report saved: %s", report_path)

    # Also save a human-readable summary
    summary_path = report_dir / "test_summary.txt"
    summary_lines = [
        "AgriDoc AI — Test Set Evaluation",
        "=" * 50,
        f"Model: {tcfg['backbone']} (Best checkpoint)",
        f"Classes: {n_classes}",
        f"Test samples: {len(all_labels)}",
        "",
        f"Top-1 accuracy:  {top1_acc:.4f} ({top1_acc*100:.2f}%)",
        f"Top-3 accuracy:  {top3_acc:.4f} ({top3_acc*100:.2f}%)",
        f"Macro Precision: {macro_precision:.4f}",
        f"Macro Recall:    {macro_recall:.4f}",
        f"Macro F1:        {macro_f1:.4f}",
        f"ECE:             {ece:.4f}",
        "",
        f"Confidence floor: {floor:.0%}",
        f"Confident samples: {confident_ratio*100:.1f}%",
        f"Confident accuracy: {confident_acc:.4f}",
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    log.info("Summary saved: %s", summary_path)

    return report


if __name__ == "__main__":
    report = main()
