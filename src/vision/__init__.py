"""AgriDoc AI vision module.

This package contains computer vision components for agricultural AI:
- PlantVillage dataset handling and preprocessing
- Data augmentation for robust model training
- Class imbalance handling for fair predictions
- Model factory for EfficientNet and MobileNet variants
- Source tag normalization for accurate image grouping
"""

from .model import build_model
from .plantvillage import PlantVillageDataset, discover_classes_and_images, build_splits
from .transforms import train_transforms, eval_transforms, denormalize, image_size, normalize_stats
from .balance import class_counts, class_names, class_weights, imbalance_ratio, n_classes, weighted_sampler
from .source_tags import normalize_source, split_source_and_id, print_aliases

__all__ = [
    # Model factory
    "build_model",
    # Dataset
    "PlantVillageDataset",
    "discover_classes_and_images",
    "build_splits",
    # Data processing
    "train_transforms",
    "eval_transforms",
    "denormalize",
    "image_size",
    "normalize_stats",
    # Balance
    "class_counts",
    "class_names",
    "class_weights",
    "imbalance_ratio",
    "n_classes",
    "weighted_sampler",
    # Source tags
    "normalize_source",
    "split_source_and_id",
    "print_aliases",
]