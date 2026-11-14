"""AgriDoc AI configuration.

Centralises all tunables so the app behaves consistently across
offline (zero-connectivity) and online modes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
# PlantVillage color images. The canonical location is data/plantvillage; the
# fallbacks below cover a sibling checkout and a renamed dataset folder, so the
# same code finds the data on any machine without per-developer edits.
_PV_CANDIDATES = [
    BASE_DIR / "data" / "plantvillage",
    BASE_DIR / "plantvillage dataset" / "color",
    BASE_DIR / "plantvillage dataset" / "grayscale",
    BASE_DIR.parent / "Agri Doc AI" / "plantvillage dataset" / "color",
    BASE_DIR.parent / "Agri Doc AI" / "plantvillage dataset" / "grayscale",
]
DATA_DIR: Path = next((p for p in _PV_CANDIDATES if p.exists()), _PV_CANDIDATES[0])

MODEL_DIR = BASE_DIR / "models" / "artifacts"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CV_MODEL_PATH = MODEL_DIR / "agridoc_cv.onnx"
ADVISORY_DB_PATH = MODEL_DIR / "advisory_rules.json"

# Runtime toggles
OFFLINE_MODE = os.environ.get("AGRIDOC_OFFLINE", "0") == "1"
# When offline, weather/market/LLM calls degrade gracefully instead of failing.
ENABLE_WEATHER = os.environ.get("AGRIDOC_WEATHER", "1") == "1"
ENABLE_MARKET = os.environ.get("AGRIDOC_MARKET", "1") == "1"
ENABLE_NLP = os.environ.get("AGRIDOC_NLP", "1") == "1"

# CV model
IMAGE_SIZE = 224
TOP_K = 3
# ImageNet normalisation stats (ResNet/EfficientNet pretrained weights).
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Backbone. EfficientNet-B0 matches config/train.yaml and is the model
# exported at configs/advice.yaml — models/checkpoints/best.pt and
# models/artifacts/agridoc_cv.onnx were both trained with it (98.82% top-1
# on PlantVillage, see reports/test_report.json).
CV_BACKBONE = "efficientnet_b0"
# Confidence below which the UI must refuse to guess. PlantVillage is lab-clean;
# real farmer photos are muddy, backlit and occluded, so a low-confidence
# prediction is worse than an honest "uncertain".
CONFIDENCE_FLOOR = 0.70
# How the CV model is served at runtime. onnxruntime is the default: it decouples
# the model from the training framework and runs anywhere, including the browser
# via ONNX Runtime Web.
CV_RUNTIME = "onnx"

# Model file paths and validation
MODEL_PATH = MODEL_DIR / "agridoc_cv.onnx"
LABELS_PATH = MODEL_DIR / "agridoc_cv.onnx.json"
META_PATH = MODEL_DIR / "meta.json"

# SHA-256 hashes for model validation (populated from meta.json)
MODEL_SHA256 = None
LABELS_SHA256 = None
META_SHA256 = None

# Load SHA-256 hashes from meta.json if it exists
if os.path.exists(str(META_PATH)):
    try:
        with open(META_PATH, "r") as f:
            meta = json.load(f)
            MODEL_SHA256 = meta.get("model_sha256")
            LABELS_SHA256 = meta.get("labels_sha256")
            META_SHA256 = meta.get("meta_sha256")
    except Exception:
        # If metadata is corrupted, continue without hash validation
        pass
else:
    # Create meta.json if it doesn't exist (for initial setup)
    meta = {
        "model_sha256": "",
        "labels_sha256": "",
        "meta_sha256": "",
        "version": "1.0.0",
        "created_at": "2025-11-01",
        "description": "AgriDoc AI model files with SHA-256 validation"
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

# ---------------------------------------------------------------------------
# Advisory
# ---------------------------------------------------------------------------
SUPPORTED_CROPS: List[str] = [
    "Apple", "Blueberry", "Cherry", "Corn", "Grape", "Orange",
    "Peach", "Pepper", "Potato", "Raspberry", "Soybean", "Squash",
    "Strawberry", "Tomato",
]
# Languages the app can speak/read. ISO 639-1 codes.
SUPPORTED_LANGUAGES: List[str] = [
    "en", "hi", "bn", "ta", "te", "mr", "gu", "ml", "kn", "pa",
]

# Security
API_KEY_HEADER = "X-API-Key"
ALLOWED_API_KEYS = {
    k.strip() for k in os.environ.get("AGRIDOC_API_KEYS", "").split(",") if k.strip()
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  #  sticker for agricultural advice.
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
RATE_LIMIT_PER_MIN = int(os.environ.get("AGRIDOC_RATE_LIMIT", "60"))

# Market data sources (public, free, no auth)
ENAM_API = "https://enam.gov.in/apmc/api/prices"
AGMARKNET_API = "https://agmarknet.gov.in/api/prices"

# Database
# SQLite (dev, no server) or PostgreSQL (prod). Python's sqlite3 is built-in.
#   sqlite:///./data/agridoc.db
#   postgresql://user:password@localhost:5432/agridoc
DATABASE_URL = os.environ.get("AGRIDOC_DATABASE_URL", "sqlite:///./data/agridoc.db")

# Sync queue configuration
SYNC_DIR = BASE_DIR / "data" / "offline" / "queue"
MAX_QUEUE_SIZE = 200
MAX_RETRIES = 3
# Queue TTL is defined in configs/sync.yaml (queue_ttl_hours) and reads as seconds
# here for backward compatibility with existing code. The configs/sync.yaml value
# is the source of truth (72 hours = 259200 seconds).
QUEUE_TTL_SECONDS = 259200  # 72 hours, matches configs/sync.yaml