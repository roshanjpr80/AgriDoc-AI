"""Privacy helpers for AgriDoc AI.

Guards:
- Strip EXIF / GPS from every uploaded image, always.
- Coarsen location to district level for outbreak reporting.
- No device id, no personal data, stored only with explicit consent.
"""
from __future__ import annotations

from src.privacy.exif import strip_image_metadata, has_location
from src.privacy.location import coarsen_location, is_valid_district

__all__ = ["strip_image_metadata", "has_location", "coarsen_location", "is_valid_district"]