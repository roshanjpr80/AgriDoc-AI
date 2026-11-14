"""Image transforms for AgriDoc AI.

Train transforms simulate real-world farmer photos (muddy, backlit, blurry,
occluded, shot on a phone). Val/test transforms are clean deterministic crops
so metrics are comparable across runs.
"""
from __future__ import annotations

from typing import Tuple

import torch
import torchvision.transforms as T
from torchvision.transforms import InterpolationMode

from configs import load_config

_cfg = load_config("data")
_AUG = _cfg["augmentation"]


def _blur() -> T.Transform:
    """Random Gaussian blur, sampled radius in [3, 7]."""
    lo, hi = _AUG["blur_kernel_range"]
    k = torch.randint(low=lo, high=hi + 1, size=(1,)).item()
    if k % 2 == 0:
        k += 1  # GaussianBlur needs an odd kernel
    return T.GaussianBlur(kernel_size=k, sigma=(0.1, 2.0))


def _cutout() -> T.Transform:
    """Random erase (cutout) so the model cannot lean on one background pixel."""
    return T.RandomErasing(
        p=_AUG["cutout_p"],
        scale=(_AUG["cutout_size"], _AUG["cutout_size"]),
        ratio=(1.0, 1.0),
    )


def train_transforms() -> T.Compose:
    """Strong augmentation for training."""
    size = _cfg["image_size"]
    return T.Compose(
        [
            T.Resize((size, size), interpolation=InterpolationMode.BILINEAR),
            T.RandomAffine(
                degrees=_AUG["rotation_degrees"],
                translate=None,
                scale=tuple(_AUG["scale_range"]),
                shear=None,
                interpolation=InterpolationMode.BILINEAR,
                fill=0,
            ),
            T.RandomHorizontalFlip(p=_AUG["hflip_p"]),
            T.RandomVerticalFlip(p=_AUG["vflip_p"]),
            T.ColorJitter(
                brightness=_AUG["brightness_jitter"],
                contrast=_AUG["contrast_jitter"],
                saturation=_AUG["saturation_jitter"],
                hue=_AUG["hue_jitter"],
            ),
            T.ToTensor(),
            T.Normalize(mean=_cfg["imagenet_mean"], std=_cfg["imagenet_std"]),
            _blur(),
            _cutout(),
        ]
    )


def eval_transforms() -> T.Compose:
    """Deterministic centre-crop + normalisation for validation/test."""
    size = _cfg["image_size"]
    return T.Compose(
        [
            T.Resize((size, size), interpolation=InterpolationMode.BILINEAR),
            T.ToTensor(),
            T.Normalize(mean=_cfg["imagenet_mean"], std=_cfg["imagenet_std"]),
        ]
    )


def denormalize(tensor: torch.Tensor) -> torch.Tensor:
    """Reverse ImageNet normalisation for overlay rendering / visualisation."""
    mean = torch.tensor(_cfg["imagenet_mean"], device=tensor.device).view(3, 1, 1)
    std = torch.tensor(_cfg["imagenet_std"], device=tensor.device).view(3, 1, 1)
    out = tensor * std + mean
    return out.clamp(0.0, 1.0)


def image_size() -> int:
    return int(_cfg["image_size"])


def normalize_stats() -> Tuple[list, list]:
    return _cfg["imagenet_mean"], _cfg["imagenet_std"]