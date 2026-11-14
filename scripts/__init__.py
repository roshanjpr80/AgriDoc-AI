"""AgriDoc AI package root.

This module marks the repo root as a package so scripts can import `configs` and
`src.<sub>` modules using absolute imports (e.g., `from configs import load_config`,
`from src.vision.model import build_model`).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent  # repo root (D:/agridoc)
# Alias for configs module access from repo root
import sys
sys.path.insert(0, str(ROOT))