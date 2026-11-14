"""Class-imbalance handling for AgriDoc AI.

PlantVillage is wildly imbalanced: `Orange___Haunglongbing` has 5,507 images
while `Potato___healthy` has 152. A plain cross-entropy on the raw distribution
over-fits the majority classes and barely learns the rare ones.

Two complementary fixes are provided:

1. ``class_weights`` — per-class inverse-frequency weights used in the loss
   function. Cheap, deterministic, works with any sampler.
2. ``weighted_sampler`` — a ``WeightedRandomSampler`` that re-weights each
   sample so the effective batch is roughly balanced. Used in the train loader.

Both are derived from the same counts so they can never drift apart.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import torch
from torch.utils.data import WeightedRandomSampler

from configs import load_config

_cfg = load_config("data")


def _load_class_counts() -> Dict[str, int]:
    """Count images per class folder on disk (cached, fast).

    PlantVillage layout: data_root/train/<Class>, data_root/val/<Class>,
    data_root/test/<Class>.  We sum across all three splits.
    """
    root = Path(_cfg["data_root"])
    counts: Dict[str, int] = {}
    for split in ("train", "val", "test"):
        sp_root = root / split
        if not sp_root.exists():
            continue
        for folder in sorted(sp_root.iterdir()):
            if folder.is_dir():
                c = counts.get(folder.name, 0) + sum(1 for _ in folder.iterdir() if _.is_file())
                counts[folder.name] = c
    return counts


_CLASSES = _load_class_counts()


def class_names() -> List[str]:
    """Stable, sorted list of class folder names."""
    return sorted(_CLASSES.keys())


def class_counts() -> Dict[str, int]:
    """Raw image counts per class (for reports / MODEL_CARD)."""
    return dict(_CLASSES)


def n_classes() -> int:
    return len(_CLASSES)


def class_weights() -> torch.Tensor:
    """Inverse-frequency weights, L1-normalised.

    weight_c = N / (n_classes * count_c)
    so the sum of weights equals 1 and rare classes get the most weight.
    """
    counts = torch.tensor(
        [float(_CLASSES[c]) for c in sorted(_CLASSES.keys())], dtype=torch.float32
    )
    n = float(len(_CLASSES))
    weights = n / (counts * n).clamp(min=1.0)
    # Guard against a zero-count class producing inf.
    weights = torch.where(torch.isfinite(weights), weights, torch.ones_like(weights))
    return weights / weights.sum()


def weighted_sampler(labels: List[int], replacement: bool = True) -> WeightedRandomSampler:
    """Sampler that balances the effective batch by inverse class frequency."""
    counts = torch.tensor(
        [float(_CLASSES[c]) for c in sorted(_CLASSES.keys())], dtype=torch.float32
    )
    sample_weights = 1.0 / counts[torch.tensor(labels, dtype=torch.long)].clamp(min=1.0)
    return WeightedRandomSampler(
        weights=sample_weights, num_samples=len(labels), replacement=replacement
    )


def imbalance_ratio() -> float:
    """max_count / min_count — a single number describing how skewed the data is."""
    counts = list(_CLASSES.values())
    return max(counts) / max(min(counts), 1)