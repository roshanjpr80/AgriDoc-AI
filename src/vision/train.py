"""Train the AgriDoc AI crop-disease classifier.
python -m src.vision.train
Usage: python -m agridoc.src.vision.train [--epochs N] [--backbone efficientnet_b0]
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from configs import load_config
from src.vision.balance import class_weights
from src.vision.model import build_model, freeze_backbone, unfreeze_backbone, param_groups
from src.vision.plantvillage import PlantVillageDataset
from src.vision.transforms import train_transforms, eval_transforms

logger = logging.getLogger(__name__)


def _eval(model, loader, device, n_classes):
    model.eval()
    correct = total = 0
    per_class = [0] * n_classes
    per_class_tot = [0] * n_classes
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            pred = logits.argmax(1)
            correct += (pred == y).sum().item()
            total += y.size(0)
            for c in range(n_classes):
                per_class_tot[c] += (y == c).sum().item()
                per_class[c] += ((y == c) & (pred == c)).sum().item()
    acc = correct / max(total, 1)
    macro_acc = sum(per_class[c] / max(per_class_tot[c], 1) for c in range(n_classes)) / n_classes
    return {"acc": acc, "macro_acc": macro_acc, "correct": correct, "total": total}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--backbone", type=str, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    args = ap.parse_args()

    tcfg = load_config("train")
    dcfg = load_config("data")
    epochs = args.epochs or tcfg["epochs"]
    backbone = args.backbone or tcfg["backbone"]
    bs = args.batch_size or tcfg["batch_size"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("device=%s backbone=%s epochs=%d bs=%d", device, backbone, epochs, bs)

    classes = json.loads(Path(dcfg["classes_manifest"]).read_text())
    n_classes = len(classes)

    train_ds = PlantVillageDataset("train", train_transforms())
    val_ds = PlantVillageDataset("val", eval_transforms())
    train_loader = DataLoader(train_ds, batch_size=bs, shuffle=True,
                              num_workers=dcfg["num_workers"], drop_last=dcfg["drop_last"])
    val_loader = DataLoader(val_ds, batch_size=bs, shuffle=False,
                            num_workers=dcfg["num_workers"])

    model = build_model(backbone=backbone, num_classes=n_classes,
                        pretrained=tcfg["pretrained"], dropout=tcfg["dropout"])
    model.to(device)

    weights = class_weights().to(device)
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=tcfg["label_smoothing"])

    freeze_backbone(model)
    optimizer = torch.optim.AdamW(
        param_groups(model, backbone_lr_scale=tcfg["backbone_lr"] / tcfg["learning_rate"]),
        lr=tcfg["learning_rate"], weight_decay=tcfg["weight_decay"],
    )

    best_metric = 0.0
    best_path = Path(tcfg["best_checkpoint"])
    best_path.parent.mkdir(parents=True, exist_ok=True)
    patience = tcfg["early_stopping_patience"]
    wait = 0

    for epoch in range(1, epochs + 1):
        if epoch == tcfg["freeze_epochs"] + 1 and tcfg["finetune_backbone"]:
            unfreeze_backbone(model)
            optimizer = torch.optim.AdamW(
                param_groups(model, backbone_lr_scale=tcfg["backbone_lr"] / tcfg["learning_rate"]),
                lr=tcfg["learning_rate"], weight_decay=tcfg["weight_decay"],
            )
            logger.info("epoch %d: unfroze backbone", epoch)

        model.train()
        t0 = time.time()
        loss_sum = 0.0
        n_batches = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), tcfg["grad_clip_norm"])
            optimizer.step()
            loss_sum += loss.item()
            n_batches += 1

        val = _eval(model, val_loader, device, n_classes)
        metric = val["macro_acc"]
        logger.info(
            "epoch %2d/%d  loss=%.4f  val_acc=%.4f  val_macro_acc=%.4f  (%.1fs)",
            epoch, epochs, loss_sum / max(n_batches, 1), val["acc"], metric, time.time() - t0,
        )
        if metric > best_metric:
            best_metric = metric
            wait = 0
            torch.save({"model": model.state_dict(), "epoch": epoch,
                        "metric": metric, "backbone": backbone}, best_path)
        else:
            wait += 1
            if wait >= patience:
                logger.info("early stopping at epoch %d (best macro_acc=%.4f)", epoch, best_metric)
                break

    torch.save({"model": model.state_dict(), "epoch": epochs,
                "metric": best_metric, "backbone": backbone},
               Path(tcfg["final_checkpoint"]))
    logger.info("done. best macro_acc=%.4f  checkpoint=%s", best_metric, best_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()