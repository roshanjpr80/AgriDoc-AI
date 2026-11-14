"""EXIF / GPS stripping.

Farmers may take photos with location enabled. We must never persist GPS
coordinates or device identifiers. This module removes every metadata tag
from an image before it is stored or uploaded.
"""
from __future__ import annotations

import io
from typing import Tuple

from PIL import Image

# EXIF IFD tag ids we care about.
_GPS_IFD = 34853


def strip_image_metadata(img: Image.Image) -> Image.Image:
    """Return a pixel copy of *img* with all EXIF / comment / GPS removed.

    PIL's ``Image.new().putdata()`` creates a fresh image with no info dict,
    which is the safest way to guarantee metadata removal.
    """
    if img.mode in ("P", "RGBA"):
        img = img.convert("RGB")
    clean = Image.new("RGB", img.size)
    clean.putdata(list(img.getdata()))
    return clean


def has_location(img: Image.Image) -> bool:
    """Return True if the image carries GPS EXIF data."""
    exif = img.getexif()
    if exif is None:
        return False
    return _GPS_IFD in exif


def strip_bytes(raw: bytes) -> Tuple[bytes, bool]:
    """Strip metadata from raw image bytes.

    Returns (clean_bytes, had_location). The output is re-encoded as JPEG.
    """
    img = Image.open(io.BytesIO(raw))
    had = has_location(img)
    clean = strip_image_metadata(img)
    buf = io.BytesIO()
    clean.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue(), had