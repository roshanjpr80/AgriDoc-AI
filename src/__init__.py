"""AgriDoc AI source package.

Hyperparameters live in ``configs/*.yaml``; this module loads them so nothing
is hardcoded in the code.
"""
from __future__ import annotations

from configs import load_config as _load_config
from configs import config_path

# Re-export the canonical loader so imports like
#   from src import load_config
# work without duplicating logic. Path resolution lives in configs/__init__.py.
load_config = _load_config