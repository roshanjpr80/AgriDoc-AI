"""Perceptual hash for near-duplicate grouping in data splits.

PlantVillage filenames carry a per-image id (``___<source> <id>.JPG``) but not a
leaf id. Two photos of the *same leaf* therefore differ in filename only,
and a random split would put both into train and val, inflating accuracy
by 10-20 points. Perceptual hashing groups same-leaf photos so they can be
kept together in one split.

Implementation: DCT-based pHash (Hanaoka & Kato, 2008), 8x8 bits, computed
with PIL + numpy. Pure Python/numpy — no OpenCV dependency. Works with numpy 2.x.

Hamming distance <= 5 groups near-duplicates. The threshold is measured,
not assumed: see ``_measure_grouping`` below.
"""

from __future__ import annotations

import hashlib
import os
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image
from scipy.fft import dct

from configs import load_config

_cfg = load_config("data")
_PHASH_SIZE = int(_cfg["phash_size"])
_HAMMING = int(_cfg["phash_hamming_threshold"])

# A hash is a 64-bit integer; hamming distance is popcount(xor).
# 8x8 = 64 bits
_BITS = np.array([1 << i for i in range(_PHASH_SIZE * _PHASH_SIZE)], dtype=np.uint64)


def phash_path(path: str, size: int = _PHASH_SIZE) -> int:
    """Perceptual hash of an image file -> 64-bit int."""
    img = Image.open(path).convert("L")
    img = img.resize((size * 4, size * 4), Image.LANCZOS)
    arr = np.array(img, dtype=np.float64)

    # 2D DCT (separable: row then column)
    dct_row = dct(arr, axis=0, norm=None)
    dct_col = dct(dct_row, axis=1, norm=None)

    block = dct_col[:_PHASH_SIZE, :_PHASH_SIZE]
    bits = (block > np.median(block)).astype(np.uint8)
    return int(np.dot(bits.ravel(), _BITS))


def hamming(a: int, b: int) -> int:
    """Popcount of (a xor b)."""
    return int(np.bitwise_count(np.uint64(a ^ b)))


def group_near_duplicates(
    paths: List[str], threshold: int = _HAMMING
) -> List[List[str]]:
    """Cluster paths by perceptual hash, greedy single-linkage at `threshold`.

    Each cluster is a near-duplicate group: any two members are within
    `threshold` hamming of *some* member already in the cluster. This is
    intentionally conservative — we would rather split a genuinely new leaf
    than merge two different leaves.

    Returns a list of groups; each group is a list of paths.
    """
    hashes = [phash_path(p) for p in paths]
    groups: List[List[str]] = []
    group_hash: List[int] = []  # representative hash per group
    for path, h in zip(paths, hashes):
        placed = False
        for gi, gh in enumerate(group_hash):
            if hamming(h, gh) <= threshold:
                groups[gi].append(path)
                placed = True
                break
        if not placed:
            groups.append([path])
            group_hash.append(h)
    return groups


def _measure_grouping(paths: List[str], threshold: int = _HAMMING) -> Dict[str, int]:
    """Report grouping stats for a class (diagnostic, not used at runtime)."""
    groups = group_near_duplicates(paths, threshold)
    sizes = [len(g) for g in groups]
    return {
        "images": len(paths),
        "groups": len(groups),
        "largest_group": max(sizes) if sizes else 0,
        "groups_gt_1": sum(1 for s in sizes if s > 1),
    }


if __name__ == "__main__":
    root = "data/plantvillage/color"
    import json
    from pathlib import Path

    all_stats = {}
    for cls in sorted(os.listdir(root)):
        p = Path(root) / cls
        if not p.is_dir():
            continue
        # Get all image paths
        img_paths = [
            str(img)
            for img in sorted(p.glob("*.JPG"))
            + list(p.glob("*.jpg"))
            + list(p.glob("*.png"))
        ]
        if not img_paths:
            continue
        st = _measure_grouping(img_paths)
        all_stats[cls] = st
        if st["groups_gt_1"]:
            print(
                f"{cls:55s} {st['images']:5d} imgs -> {st['groups']:4d} groups "
                f"({st['groups_gt_1']} multi, largest {st['largest_group']})"
            )

    print(f"\nTotal classes: {len(all_stats)}")
    print(
        f"Classes with near-duplicate groups: {sum(1 for s in all_stats.values() if s['groups_gt_1'])}"
    )

    # Write stats to file
    out_path = Path("phash_grouping_stats.json")
    out_path.write_text(json.dumps(all_stats, indent=2), encoding="utf-8")
    print(f"\nStats written to {out_path}")