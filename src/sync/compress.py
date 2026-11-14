"""Image compression for low-end phones.

Rural users often have 2-5 MP cameras on patchy networks. A 12 MB RAW photo
takes forever to upload and often fails. This module resizes and re-quantises
images to a target budget while keeping enough detail for the CNN and
Grad-CAM overlay.

Privacy: EXIF / GPS is always stripped before any upload or queue write.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Budgets in bytes. "low" is for 2G/3G phones, "mid" for 4G, "full" for wifi.
BUDGETS = {"low": 120_000, "mid": 300_000, "full": 800_000}

# Long edge for the CNN input path. 512 keeps leaf detail while staying small.
MAX_LONG_EDGE = 512


@dataclass
class CompressedImage:
    """Container for compressed image data with metadata."""
    bytes: bytes
    mime_type: str
    width: int
    height: int
    original_bytes: int
    stripped_exif: bool


def _strip_exif(img: Image.Image) -> Image.Image:
    """Return a copy of the image with all EXIF/GPS metadata removed."""
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    return clean


def _encode(img: Image.Image, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def compress(
    raw: bytes,
    budget: str = "mid",
    max_long_edge: int = MAX_LONG_EDGE,
    mime_type: str = "image/jpeg",
) -> CompressedImage:
    """Compress an image to fit a byte budget.

    Strategy: resize so the long edge <= max_long_edge, then reduce JPEG
    quality until the payload fits the budget. Falls back to WebP if JPEG
    cannot reach the budget (better compression, still supported by
    onnxruntime via PIL decode).

    Args:
        raw: raw image bytes from the camera.
        budget: 'low' | 'mid' | 'full'.
        max_long_edge: maximum long edge in pixels after resize.
        mime_type: preferred output format.

    Returns:
        CompressedImage with the payload and metadata.
    """
    target = BUDGETS.get(budget, BUDGETS["mid"])
    img = Image.open(io.BytesIO(raw))
    stripped = False
    if "exif" in img.info or "gps" in (img.info.get("exif", b"").hex() if isinstance(img.info.get("exif"), bytes) else ""):
        img = _strip_exif(img)
        stripped = True
    # Always strip to be safe.
    if not stripped:
        img = _strip_exif(img)
        stripped = True

    # Resize preserving aspect ratio.
    w, h = img.size
    scale = min(1.0, max_long_edge / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    fmt = "JPEG" if mime_type == "image/jpeg" else ("WEBP" if mime_type == "image/webp" else "JPEG")

    # Try descending quality.
    for q in (90, 80, 70, 60, 50, 40, 30):
        data = _encode(img, fmt, q)
        if len(data) <= target:
            return CompressedImage(
                bytes=data,
                mime_type=mime_type,
                width=img.width,
                height=img.height,
                original_bytes=len(raw),
                stripped_exif=stripped,
            )
    # Last resort: WebP lossy at low quality.
    data = _encode(img, "WEBP", 25)
    return CompressedImage(
        bytes=data,
        mime_type="image/webp",
        width=img.width,
        height=img.height,
        original_bytes=len(raw),
        stripped_exif=stripped,
    )


def estimate_upload_seconds(bytes_: int, kbps: int) -> float:
    """Estimate upload time in seconds for a given payload and link speed.

    kbps values: 2G ~ 30, 3G ~ 150, 4G ~ 2000, wifi ~ 10000.
    """
    if kbps <= 0:
        return float("inf")
    return (bytes_ * 8) / (kbps * 1000)


def choose_budget(kbps: int) -> str:
    """Pick a compression budget based on measured link speed."""
    if kbps < 80:
        return "low"
    if kbps < 800:
        return "mid"
    return "full"