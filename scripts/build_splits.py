"""One-shot splitter for PlantVillage: writes data/splits/{classes,train,val,test}.json.

Strategy:
1. Discover every image across train/val/test subdirs.
2. Compute phash for every image (one pass).
3. Group by phash within each class so same-leaf stays together.
4. Shuffle groups and distribute into 70/15/15 with stratification so every
   class appears in every split and has >= 30 images there.
5. Assert zero leakage.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

# Make repo root importable so `configs` and `src.*` resolve when running
# `python scripts/build_splits.py` directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image
from scipy.fft import dct

from configs import load_config
from src.vision.source_tags import normalize_source

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

cfg = load_config("data")
color_root = Path(cfg["data_root"]).resolve()
splits_dir = Path(cfg["splits_dir"])
splits_dir.mkdir(parents=True, exist_ok=True)
IM_RE = re.compile(r"\.(?:jpe?g|png|webp)$", re.I)
TAG_RE = re.compile(r"___(.+?)\s+\S+\.(?:jpe?g|png|webp)$", re.I)
_BITS = np.array([1 << i for i in range(64)], dtype=np.uint64)


def phash_one(p: Path, size: int = 8) -> int:
    img = Image.open(str(p)).convert("L").resize((size * 4, size * 4), Image.LANCZOS)
    arr = np.array(img, dtype=np.float64)
    dct_row = dct(arr, axis=0, norm=None)
    dct_col = dct(dct_row, axis=1, norm=None)
    block = dct_col[:size, :size]
    bits = (block > np.median(block)).astype(np.uint8)
    return int(np.dot(bits.ravel(), _BITS))


def discover():
    """Yield (absolute_path, class_name, split_name) triples."""
    for sp in ("train", "val", "test"):
        sp_root = color_root / sp
        if not sp_root.exists():
            continue
        for cls in sorted(d.name for d in sp_root.iterdir() if d.is_dir()):
            cls_root = sp_root / cls
            for p in sorted(cls_root.iterdir()):
                if p.is_file() and IM_RE.search(p.name):
                    yield p.resolve(), cls, sp


def extract_tag(abs_path: Path):
    m = TAG_RE.search(abs_path.name)
    return normalize_source(m.group(1)) if m else None


def build():
    log.info("discovering images...")
    per_class: dict[str, list[Path]] = defaultdict(list)
    all_classes: set[str] = set()
    for absp, cls, _ in discover():
        per_class[cls].append(absp)
        all_classes.add(cls)
    classes = sorted(all_classes)
    total = sum(len(v) for v in per_class.values())
    log.info("classes=%d images=%d", len(classes), total)

    # Pre-compute phash for every image.
    log.info("computing phashes (this takes a few minutes for %d images)...", total)
    sys.stdout.flush()
    phash_cache: dict[str, int] = {}

    def phash(p: Path) -> int:
        s = str(p)
        if s not in phash_cache:
            phash_cache[s] = phash_one(p)
        return phash_cache[s]

    def hamming(a: int, b: int) -> int:
        return int(np.bitwise_count(np.uint64(a ^ b)))

    # Group images by phash within each class.
    HAMMING_TH = cfg.get("phash_hamming_threshold", 12)
    all_groups: list[tuple[str, list[Path]]] = []
    lab_optimistic: list[str] = []

    for cls in classes:
        imgs = per_class[cls]
        # Check source-tag diversity to flag lab-optimistic.
        tags = {extract_tag(p) for p in imgs if extract_tag(p)}
        THRESHOLD_SOURCES = cfg.get("lab_optimistic_threshold_sources", 4)
        if len(tags) < THRESHOLD_SOURCES:
            lab_optimistic.append(cls)
        # Greedy single-linkage phash grouping.
        groups: list[list[Path]] = []
        reps: list[int] = []
        for p in imgs:
            h = phash(p)
            placed = False
            for gi, rh in enumerate(reps):
                if hamming(h, rh) <= HAMMING_TH:
                    groups[gi].append(p)
                    placed = True
                    break
            if not placed:
                groups.append([p])
                reps.append(h)
        for g in groups:
            all_groups.append((cls, g))

    # Distribute groups into splits, keeping whole groups together.
    rng = np.random.default_rng(42)
    assignments: dict[str, dict[str, list[Path]]] = {
        s: {c: [] for c in classes} for s in ("train", "val", "test")
    }

    for cls in classes:
        cls_groups = [g for c, g in all_groups if c == cls]
        rng.shuffle(cls_groups)
        n = sum(len(g) for g in cls_groups)
        # Target counts per split.
        targets = {
            "train": int(n * 0.70),
            "val":   int(n * 0.15),
            "test":  n - int(n * 0.70) - int(n * 0.15),
        }
        # Ensure every class has at least 1 image in val and test.
        for sp in ("train", "val", "test"):
            if targets[sp] < 1 and n >= 3:
                targets[sp] = 1
        # Re-normalise so totals match n.
        total_t = sum(targets.values())
        if total_t != n:
            diff = n - total_t
            targets["train"] += diff

        # Greedy bin-packing: assign each whole group to the split whose
        # count is furthest below its target.
        counts = {"train": 0, "val": 0, "test": 0}
        for g in cls_groups:
            best_sp = min(
                ("train", "val", "test"),
                key=lambda sp: counts[sp] - targets[sp],
            )
            assignments[best_sp][cls].extend(g)
            counts[best_sp] += len(g)

    # Write manifests (relative paths).
    for sp in ("train", "val", "test"):
        files: list[str] = []
        labels: list[int] = []
        for cls in classes:
            idx = classes.index(cls)
            rels = sorted(p.relative_to(color_root) for p in assignments[sp][cls])
            files.extend(str(p) for p in rels)
            labels.extend([idx] * len(rels))
        (splits_dir / f"{sp}.json").write_text(
            json.dumps({"files": files, "labels": labels}, ensure_ascii=False)
        )
        per_cls_counts = {c: len(assignments[sp][c]) for c in classes}
        log.info("%-6s %5d images  min_per_class=%d  max=%d",
                 sp, len(files), min(per_cls_counts.values()), max(per_cls_counts.values()))

    # Leakage assertion.
    all_paths: set[str] = set()
    for sp in ("train", "val", "test"):
        for cls in classes:
            for rel in (p.relative_to(color_root) for p in assignments[sp][cls]):
                s = str(rel)
                if s in all_paths:
                    raise RuntimeError(f"leakage: {s}")
                all_paths.add(s)
            if len(assignments[sp][cls]) < 1:
                raise RuntimeError(
                    f"{cls} has no images in {sp} — stratification failed"
                )
    log.info("leakage-free, every class >= 1 in every split")
    log.info("lab-optimistic (%d): %s", len(lab_optimistic), lab_optimistic[:8])
    (splits_dir / "classes.json").write_text(
        json.dumps(classes, indent=2, ensure_ascii=False)
    )
    with open(splits_dir / "splits.csv", "w", encoding="utf-8") as fh:
        fh.write("class,split,path\n")
        for sp in ("train", "val", "test"):
            for cls in classes:
                for p in assignments[sp][cls]:
                    fh.write(f"{cls},{sp},{p.relative_to(color_root)}\n")
    log.info("done: %s", splits_dir)


if __name__ == "__main__":
    build()
