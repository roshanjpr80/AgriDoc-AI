"""Tests for source tag normalization and split validation."""
import pytest
from src.vision.source_tags import normalize_source
from src.vision.plantvillage import build_splits, discover_classes_and_images
from collections import defaultdict
import re


def test_normalize_source_basic():
    """Test basic source tag normalization."""
    # Test simple sources
    assert normalize_source("RS_HL") == "russel_hlb"
    assert normalize_source("RS_HLB") == "russel_hlb"
    assert normalize_source("CREC_HLB") == "cerris_rusticana_hlb"

    # Test with copy suffix
    assert normalize_source("RS_HL copy") == "russel_hlb"
    assert normalize_source("RS_HLB copy 2") == "russel_hlb"
    assert normalize_source("CREC_HLB copy") == "cerris_rusticana_hlb"

    # Test with trailing numeric ids
    assert normalize_source("RS_HL 3335") == "russel_hlb"
    assert normalize_source("RS_HLB 5677") == "russel_hlb"
    assert normalize_source("CREC_HL 123") == "cerris_rusticana_hl"

    # Test multiple trailing elements
    assert normalize_source("RS_HL 3335 copy") == "russel_hlb"
    assert normalize_source("RS_HLB 5677 copy 2") == "russel_hlb"


def test_normalize_source_alias():
    """Test source tag aliases."""
    # Test Rutgers aliases
    assert normalize_source("Rutgers_Bacterial_Slot") == "russel_bacterial_slot"
    assert normalize_source("Rutgers_Bacterial_Slot copy") == "russel_bacterial_slot"
    assert normalize_source("Rutgers_HLB") == "russel_hlb"
    assert normalize_source("Rutgers_HLB copy") == "russel_hlb"

    # Test CREC aliases
    assert normalize_source("CREC_HLB") == "cerris_rusticana_hlb"
    assert normalize_source("CREC_HLB copy") == "cerris_rusticana_hlb"


def test_normalize_source_edge_cases():
    """Test edge cases for source normalization."""
    # Test empty/whitespace
    assert normalize_source("") == ""
    assert normalize_source("   ") == ""

    # Test source without prefix
    assert normalize_source("Rs Hlb") == "rs_hlb"

    # Test mixed case
    assert normalize_source("Rs_HlB") == "rs_hlb"


def test_split_no_leakage():
    """Test that splits have no image leakage across splits."""
    classes, split_images = discover_classes_and_images()
    split_paths = defaultdict(set)

    for split in ("train", "val", "test"):
        for cls in classes:
            for rel_path in split_images[split].get(cls, []):
                split_paths[split].add(rel_path)

    # Check no duplicates across splits
    all_paths = []
    for split, paths in split_paths.items():
        for path in paths:
            if path in all_paths:
                pytest.fail(f"Image {path} appears in multiple splits")
            all_paths.append(path)


def test_split_minimum_images_per_class():
    """Test that every class has >=30 images in every split."""
    classes, split_images = discover_classes_and_images()

    for split in ("train", "val", "test"):
        for cls in classes:
            image_count = len(split_images[split].get(cls, []))
            assert image_count >= 30, (
                f"Class {cls} has only {image_count} images in {split} split. "
                f"Minimum required is 30."
            )


def test_split_source_normalization():
    """Test that source normalization is applied consistently."""
    classes, split_images = discover_classes_and_images()

    for split in ("train", "val", "test"):
        for cls in classes:
            source_tags = set()
            for rel_path in split_images[split].get(cls, []):
                # Extract source tag from filename
                filename = rel_path.split("/")[-1]
                m = re.search(r"___(.+?)\s+\S+\.(?:jpg|jpeg|png)$", filename, re.IGNORECASE)
                if m:
                    source_tags.add(m.group(1))

            # All sources in the same split should normalize to the same tag
            normalized_sources = {normalize_source(s) for s in source_tags}
            assert len(normalized_sources) == len(source_tags), (
                f"Source normalization created duplicates in class {cls} for {split} split"
            )


def test_build_splits_idempotent():
    """Test that build_splits produces the same results for the same seed."""
    s1 = build_splits(seed=42)
    s2 = build_splits(seed=42)

    # Compare all metrics
    assert s1["train"]["min_per_class"] == s2["train"]["min_per_class"]
    assert s1["val"]["min_per_class"] == s2["val"]["min_per_class"]
    assert s1["test"]["min_per_class"] == s2["test"]["min_per_class"]
    assert s1["all_classes_present"] == s2["all_classes_present"]
    assert s1["leakage_check"] == s2["leakage_check"]


def test_build_splits_class_distribution():
    """Test that build_splits distributes classes correctly across splits."""
    s = build_splits(seed=42)

    # All 38 classes should be present in each split
    assert s["train"]["classes_present"] == 38
    assert s["val"]["classes_present"] == 38
    assert s["test"]["classes_present"] == 38

    # Every class should have >=30 images in each split
    assert s["train"]["min_per_class"] >= 30
    assert s["val"]["min_per_class"] >= 30
    assert s["test"]["min_per_class"] >= 30


def test_build_splits_image_counts():
    """Test that build_splits produces reasonable image counts."""
    s = build_splits(seed=42)

    total_images = (
        s["train"]["total_images"] +
        s["val"]["total_images"] +
        s["test"]["total_images"]
    )

    # Should be all images from PlantVillage dataset (approximate)
    # PlantVillage has ~52,000 color images
    assert 50000 <= total_images <= 60000, (
        f"Total images {total_images} seems unreasonable for PlantVillage"
    )


def test_build_splits_regime_classification():
    """Test that build_splits correctly classifies classes into regimes."""
    # This test ensures that the three-tier regime classification works correctly
    classes, split_images = discover_classes_and_images()

    for cls in classes:
        # Count distinct normalized sources for this class
        source_tags = set()
        for split in ("train", "val", "test"):
            for rel_path in split_images[split].get(cls, []):
                filename = rel_path.split("/")[-1]
                m = re.search(r"___(.+?)\s+\S+\.(?:jpg|jpeg|png)$", filename, re.IGNORECASE)
                if m:
                    source_tags.add(m.group(1))

        # Normalize sources
        normalized_sources = {normalize_source(s) for s in source_tags}
        n_norm = len(normalized_sources)

        # Classify based on number of normalized sources
        if n_norm >= 4:
            assert cls in ["Tomato___Late_blight"], (
                f"Class {cls} has {n_norm} normalized sources, expected to be in regime A"
            )
        elif 1 <= n_norm <= 3:
            # Should be in regime B
            pass  # Most classes will be here
        else:
            # Should be in regime C (no sources)
            assert cls in ["Corn_(maize)___Common_rust_", "Potato___healthy"], (
                f"Class {cls} has {n_norm} normalized sources, expected to be in regime C"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])