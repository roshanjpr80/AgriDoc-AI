"""Tests for the data pipeline: splits, dataset, transforms, balance.

Run: python -m pytest agridoc/tests/test_data.py -q
"""
from __future__ import annotations

import json
from pathlib import Path

import torch

from configs import load_config
from src.vision.balance import (
    class_weights,
    imbalance_ratio,
    n_classes,
)
from src.vision.plantvillage import (
    PlantVillageDataset,
    build_splits,
    load_manifest,
)
from src.vision.transforms import (
    denormalize,
    eval_transforms,
    image_size,
    train_transforms,
)


def test_classes_manifest_exists():
    cfg = load_config("data")
    p = Path(cfg["classes_manifest"])
    assert p.exists(), f"missing {p}"
    classes = json.loads(p.read_text())
    assert len(classes) == 38
    assert classes[0] == "Apple___Apple_scab"


def test_splits_cover_all_images_once():
    cfg = load_config("data")
    seen = []
    for split in ("train", "val", "test"):
        files, labels, classes = load_manifest(split)
        assert len(files) == len(labels)
        seen.extend(files)
    assert len(seen) == len(set(seen)), "images leaked across splits"
    assert len(seen) == 54064


def test_every_class_in_every_split():
    for split in ("train", "val", "test"):
        _, labels, classes = load_manifest(split)
        present = set(labels)
        assert len(present) == len(classes), (
            f"{split} covers {len(present)}/{len(classes)} classes"
        )


def test_dataset_loads_and_shape():
    ds = PlantVillageDataset("train", transform=eval_transforms())
    assert len(ds) > 0
    img, label = ds[0]
    assert img.shape == (3, image_size(), image_size())
    assert img.dtype == torch.float32
    from src.vision.balance import n_classes
    assert 0 <= label < n_classes()


def test_train_augmentation_varies():
    ds = PlantVillageDataset("train", transform=train_transforms())
    imgs = [ds[i][0] for i in range(4)]
    # Augmentation must produce different tensors for the same image.
    assert not torch.equal(imgs[0], imgs[1])
    assert all(t.shape == imgs[0].shape for t in imgs)


def test_denormalize_range():
    cfg = load_config("data")
    t = torch.randn(3, 32, 32)
    out = denormalize(t)
    assert out.min() >= -0.01
    assert out.max() <= 1.01


def test_class_weights_sum_to_one():
    w = class_weights()
    assert w.shape == (n_classes(),)
    assert abs(float(w.sum()) - 1.0) < 1e-6


def test_imbalance_ratio():
    # Measured: Orange___Haunglongbing 5507 / Potato___healthy 152.
    ratio = imbalance_ratio()
    assert 36.0 < ratio < 37.0  # ratio varies slightly with exact phash grouping


def test_build_splits_is_deterministic():
    s1 = build_splits(seed=42)
    s2 = build_splits(seed=42)
    assert s1 == s2