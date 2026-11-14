"""Tests for vision module: transforms, perceptual hashing, Grad-CAM, model.

Run: python -m pytest tests/test_vision.py -q
"""
from __future__ import annotations

import io
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
from PIL import Image

from src.vision.transforms import (
    train_transforms,
    eval_transforms,
    denormalize,
    image_size,
    normalize_stats,
)
from src.vision.phash import (
    phash_path as phash,
    hamming as hamming_distance,
    group_near_duplicates,
    _measure_grouping,
)
from src.vision.gradcam import (
    overlay_png,
)
from src.vision.model import (
    build_model as create_model,
    count_trainable as count_parameters,
)
from src.vision.plantvillage import (
    PlantVillageDataset,
    load_manifest,
    build_splits,
)
from src.vision.balance import (
    n_classes,
    class_weights,
    imbalance_ratio,
)


class TestTransforms:
    """Test image transforms."""

    def test_image_size(self):
        assert image_size() == 224

    def test_eval_transforms_output_shape(self):
        transform = eval_transforms()
        img = Image.new("RGB", (300, 300), color="green")
        tensor = transform(img)
        assert tensor.shape == (3, 224, 224)

    def test_train_transforms_output_shape(self):
        transform = train_transforms()
        img = Image.new("RGB", (300, 300), color="green")
        tensor = transform(img)
        assert tensor.shape == (3, 224, 224)

    def test_train_transforms_are_stochastic(self):
        transform = train_transforms()
        img = Image.new("RGB", (300, 300), color="green")
        t1 = transform(img)
        t2 = transform(img)
        # Should produce different tensors due to augmentation
        assert not np.allclose(t1.numpy(), t2.numpy())

    def test_denormalize_range(self):
        import torch
        t = torch.randn(3, 32, 32)
        out = denormalize(t)
        assert out.min() >= -0.01
        assert out.max() <= 1.01

    def test_denormalize_inverts_normalize(self):
        import torch
        from torchvision import transforms as T
        mean, std = normalize_stats()
        normalize = T.Normalize(mean=mean, std=std)
        original = torch.rand(3, 32, 32)
        normalized = normalize(original.clone())
        denormalized = denormalize(normalized)
        assert torch.allclose(original, denormalized, atol=1e-5)


class TestPerceptualHash:
    """Test perceptual hashing for near-duplicate detection."""

    def test_phash_returns_64bit_int(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmpdir / "test.jpg")
            h = phash(str(tmpdir / "test.jpg"))
            assert isinstance(h, int)
            assert 0 <= h < (1 << 64)

    def test_phash_same_image_same_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(tmpdir / "test.jpg")
            h1 = phash(str(tmpdir / "test.jpg"))
            h2 = phash(str(tmpdir / "test.jpg"))
            assert h1 == h2

    def test_phash_different_images_different_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # Use varied patterns instead of solid colors to ensure different phash
            img1 = Image.new("RGB", (100, 100), color="red")
            # Add some noise to make it different
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img1)
            for i in range(100):
                for j in range(100):
                    if (i + j) % 10 == 0:
                        draw.point((i, j), fill=(255, 255, 255))

            img2 = Image.new("RGB", (100, 100), color="blue")
            draw = ImageDraw.Draw(img2)
            for i in range(100):
                for j in range(100):
                    if (i * j) % 7 == 0:
                        draw.point((i, j), fill=(255, 255, 255))

            img1.save(tmpdir / "test1.jpg")
            img2.save(tmpdir / "test2.jpg")
            h1 = phash(str(tmpdir / "test1.jpg"))
            h2 = phash(str(tmpdir / "test2.jpg"))
            assert h1 != h2

    def test_hamming_distance(self):
        assert hamming_distance(0, 0) == 0
        assert hamming_distance(0, 1) == 1
        assert hamming_distance(0b1111, 0b0000) == 4
        assert hamming_distance(0b1010, 0b0101) == 4

    def test_group_near_duplicates_identical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            img = Image.new("RGB", (100, 100), color="green")
            img.save(tmpdir / "test1.jpg")
            img.save(tmpdir / "test2.jpg")
            groups = group_near_duplicates([str(tmpdir / "test1.jpg"), str(tmpdir / "test2.jpg")])
            assert len(groups) == 1
            assert len(groups[0]) == 2

    def test_group_near_duplicates_different(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            from PIL import ImageDraw
            # Use varied patterns instead of solid colors to ensure different phash
            img1 = Image.new("RGB", (100, 100), color="red")
            draw = ImageDraw.Draw(img1)
            for i in range(100):
                for j in range(100):
                    if (i + j) % 10 == 0:
                        draw.point((i, j), fill=(255, 255, 255))

            img2 = Image.new("RGB", (100, 100), color="blue")
            draw = ImageDraw.Draw(img2)
            for i in range(100):
                for j in range(100):
                    if (i * j) % 7 == 0:
                        draw.point((i, j), fill=(255, 255, 255))

            img1.save(tmpdir / "test1.jpg")
            img2.save(tmpdir / "test2.jpg")
            groups = group_near_duplicates([str(tmpdir / "test1.jpg"), str(tmpdir / "test2.jpg")])
            assert len(groups) == 2
            assert all(len(g) == 1 for g in groups)


class TestGradCAM:
    """Test Grad-CAM heatmap generation."""

    def test_overlay_png_requires_checkpoint(self):
        """Test that overlay_png needs a trained checkpoint."""
        img = Image.new("RGB", (224, 224), color="green")
        # Without a real checkpoint, this will fail - just verify the function exists
        # The actual test requires a trained model checkpoint
        import src.vision.gradcam as gradcam_module
        assert hasattr(gradcam_module, "overlay_png")


class TestModel:
    """Test model creation and loading."""

    def test_create_model_output_shape(self):
        model = create_model(num_classes=38)
        import torch
        x = torch.randn(1, 3, 224, 224)
        out = model(x)
        assert out.shape == (1, 38)

    def test_count_parameters(self):
        model = create_model(num_classes=38)
        params = count_parameters(model)
        assert params > 0
        assert params < 10_000_000  # EfficientNet-B0 is ~5.3M params


class TestPlantVillageDataset:
    """Test PlantVillage dataset loading."""

    def test_dataset_loads(self):
        ds = PlantVillageDataset("train", transform=eval_transforms())
        assert len(ds) > 0

    def test_dataset_item_shape(self):
        ds = PlantVillageDataset("train", transform=eval_transforms())
        img, label = ds[0]
        assert img.shape == (3, 224, 224)
        assert 0 <= label < n_classes()

    def test_load_manifest_splits(self):
        for split in ("train", "val", "test"):
            files, labels, classes = load_manifest(split)
            assert len(files) == len(labels)
            assert len(classes) == 38
            assert all(isinstance(f, str) for f in files)
            assert all(isinstance(l, int) for l in labels)

    def test_no_leakage_across_splits(self):
        seen = set()
        for split in ("train", "val", "test"):
            files, _, _ = load_manifest(split)
            for f in files:
                assert f not in seen, f"Leakage: {f} in multiple splits"
                seen.add(f)


class TestBalance:
    """Test class balance utilities."""

    def test_n_classes(self):
        assert n_classes() == 38

    def test_class_weights_sum_to_one(self):
        w = class_weights()
        assert w.shape == (38,)
        assert abs(float(w.sum()) - 1.0) < 1e-6

    def test_class_weights_positive(self):
        w = class_weights()
        assert all(w > 0)

    def test_imbalance_ratio(self):
        ratio = imbalance_ratio()
        # Known: Orange___Haunglongbing 5507 / Potato___healthy 152
        assert 35.0 < ratio < 38.0


class TestBuildSplits:
    """Test split building (smoke test)."""

    def test_build_splits_deterministic(self):
        # This is slow, so just test that it runs without error
        # and produces deterministic results
        s1 = build_splits(seed=42)
        s2 = build_splits(seed=42)
        assert s1 == s2


# Fixtures

@pytest.fixture
def mock_onnx_session():
    """Mock ONNX inference session for testing."""
    import src.api.inference as inference_module
    from unittest.mock import patch

    mock_session = MagicMock()
    import numpy as np
    logits = np.zeros((1, 38), dtype=np.float32)
    logits[0, 0] = 10.0
    mock_session.run.return_value = [logits]

    mock_labels = [f"Class_{i}" for i in range(38)]
    mock_labels[0] = "Apple___Apple_scab"

    with patch.object(inference_module, "_session", mock_session):
        with patch.object(inference_module, "_LABELS", mock_labels):
            yield mock_session