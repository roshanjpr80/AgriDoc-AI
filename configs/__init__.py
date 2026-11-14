"""AgriDoc AI configuration package.

Hyperparameters live in ``configs/*.yaml``. This module loads them so nothing
is hardcoded in the code. Configs are plain YAML files; the package marker
ensures ``from configs import load_config`` resolves.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parent          # agridoc/configs
PKG_ROOT = ROOT.parent                          # agridoc/

# Config keys that hold filesystem paths relative to the agridoc package root.
_PATH_KEYS = {
    "data_root", "splits_dir", "train_manifest", "val_manifest",
    "test_manifest", "classes_manifest", "checkpoint_dir",
    "best_checkpoint", "final_checkpoint", "report_dir",
    "splits_csv", "knowledge_json", "translations_json",
    "onnx_model", "onnx_labels", "classes_manifest",
}


def load_config(name: str) -> Dict[str, Any]:
    """Load ``configs/<name>.yaml``.

    Values whose keys look like paths are resolved relative to the agridoc
    package root, so the process can run from any working directory.
    Raises FileNotFoundError with a helpful message if the file is missing.
    """
    path = ROOT / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found: {path}. Create configs/{name}.yaml first."
        )
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    for key in _PATH_KEYS:
        if key in data and isinstance(data[key], str):
            p = Path(data[key])
            if not p.is_absolute():
                data[key] = str(PKG_ROOT / p)
    return data


def config_path(name: str) -> Path:
    return ROOT / f"{name}.yaml"