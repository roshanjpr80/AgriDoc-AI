"""Offline prediction queue for AgriDoc AI.

This module provides an offline-first prediction queue that allows farmers to
upload leaf disease photos for analysis even when internet is unavailable.
Predictions are queued locally, retried when connectivity returns, and results
synced back to the cloud when possible.
"""
from __future__ import annotations

import json
import os
import threading
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from configs import load_config

logger = logging.getLogger(__name__)

# Configuration
_cfg = load_config("sync")
_QUEUE_DIR = Path(_cfg["queue_dir"])
_LOCK = threading.Lock()
MAX_QUEUE_SIZE = int(_cfg["max_queue_size"])
MAX_RETRIES = int(_cfg["max_retries"])
# How long (hours) a queued item is retained before purging. Read from
# configs/sync.yaml so there is one place to change it. The raw value from
# sync.yaml is in hours; this converts to seconds for internal use.
QUEUE_TTL_SECONDS = int(_cfg.get("queue_ttl_hours", 72)) * 3600


@dataclass
class QueuedPrediction:
    """Represents a prediction queued for offline processing."""
    id: str
    ts: float
    image_b64: str
    mime_type: str
    predicted_class: str
    confidence: float
    uncertain: bool
    synced: bool = False
    farmer_correct: Optional[bool] = None
    farmer_comment: str = ""
    farmer_id: str = ""

    # Fields for retry tracking
    attempts: int = field(default=0)
    next_retry_ts: float = field(default_factory=lambda: time.time() + 1)

    def should_retry(self) -> bool:
        """Check if this prediction should be retried."""
        return not self.synced and self.attempts < MAX_RETRIES and time.time() <= self.next_retry_ts

    def increment_attempts(self) -> None:
        """Increment attempt counter and set next retry time."""
        self.attempts += 1
        self.next_retry_ts = time.time() + (2 ** self.attempts)  # Exponential backoff

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "ts": self.ts,
            "image_b64": self.image_b64,
            "mime_type": self.mime_type,
            "predicted_class": self.predicted_class,
            "confidence": self.confidence,
            "uncertain": self.uncertain,
            "synced": self.synced,
            "farmer_correct": self.farmer_correct,
            "farmer_comment": self.farmer_comment,
            "farmer_id": self.farmer_id,
            "attempts": self.attempts,
            "next_retry_ts": self.next_retry_ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueuedPrediction":
        """Create a QueuedPrediction from dictionary."""
        # Handle backward compatibility
        if "attempts" not in data:
            data["attempts"] = 0
        if "next_retry_ts" not in data:
            data["next_retry_ts"] = time.time()
        return cls(**data)


def _ensure_dir() -> None:
    _QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def _queue_path(device_id: str) -> Path:
    return _QUEUE_DIR / f"{device_id}.jsonl"


def create_prediction(
    image_bytes: bytes,
    mime_type: str,
    predicted_class: str,
    confidence: float,
    uncertain: bool,
    device_id: str = "",
) -> QueuedPrediction:
    """Create a new QueuedPrediction from image data."""
    return QueuedPrediction(
        id=make_item_id(),
        ts=time.time(),
        image_b64=_b64encode(image_bytes),
        mime_type=mime_type,
        predicted_class=predicted_class,
        confidence=confidence,
        uncertain=uncertain,
        farmer_id=device_id,
    )


def _b64decode(s: str) -> bytes:
    """Decode base64 string to bytes."""
    import base64
    return base64.b64decode(s)


def _b64encode(b: bytes) -> str:
    """Encode bytes to base64 string."""
    import base64
    return base64.b64encode(b).decode("ascii")


def queue_size(device_id: str) -> dict:
    """Get queue size statistics for a device."""
    path = _queue_path(device_id)
    if not path.exists():
        return {"total": 0, "synced": 0, "unsynced": 0}

    total = synced = unsynced = 0
    with _LOCK:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                total += 1
                if rec.get("synced"):
                    synced += 1
                else:
                    unsynced += 1
    return {"total": total, "synced": synced, "unsynced": unsynced}


def _validate_capacity(device_id: str) -> bool:
    """Check if the queue has capacity for new items."""
    size = queue_size(device_id)
    return size["unsynced"] < MAX_QUEUE_SIZE


def enqueue(prediction: QueuedPrediction) -> str:
    """Append a prediction to the queue if capacity allows."""
    _ensure_dir()
    path = _queue_path(prediction.farmer_id or "")
    with _LOCK:
        # Check capacity before adding
        if not _validate_capacity(prediction.farmer_id or ""):
            logger.warning("Queue at capacity for device %s", prediction.farmer_id or "")
            return prediction.id

        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(prediction.to_dict(), ensure_ascii=False) + "\n")
    return prediction.id


def list_pending(device_id: str) -> List[QueuedPrediction]:
    """Return all predictions that haven't been successfully synced yet."""
    path = _queue_path(device_id)
    if not path.exists():
        return []

    pending: List[QueuedPrediction] = []
    with _LOCK:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                prediction = QueuedPrediction.from_dict(rec)
                if not prediction.synced and prediction.should_retry():
                    pending.append(prediction)
    return pending


def list_synced(device_id: str) -> List[QueuedPrediction]:
    """Return all predictions that have been successfully synced."""
    path = _queue_path(device_id)
    if not path.exists():
        return []

    synced: List[QueuedPrediction] = []
    with _LOCK:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                prediction = QueuedPrediction.from_dict(rec)
                if prediction.synced:
                    synced.append(prediction)
    return synced


def mark_synced(device_id: str, item_ids: List[str]) -> int:
    """Mark the given item IDs as synced. Returns the count marked."""
    path = _queue_path(device_id)
    if not path.exists():
        return 0

    ids = set(item_ids)
    updated = 0
    records: List[dict] = []
    with _LOCK:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec["id"] in ids and not rec.get("synced"):
                    rec["synced"] = True
                    rec["attempts"] = 0  # Reset attempts on successful sync
                    updated += 1
                records.append(rec)
        with path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return updated


def purge_old(device_id: str, max_age_seconds: int = QUEUE_TTL_SECONDS) -> int:
    """Remove synced predictions older than max_age_seconds."""
    path = _queue_path(device_id)
    if not path.exists():
        return 0

    cutoff = time.time() - max_age_seconds
    kept: List[dict] = []
    removed = 0
    with _LOCK:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("synced") and rec.get("ts", 0) < cutoff:
                    removed += 1
                    continue
                kept.append(rec)
        with path.open("w", encoding="utf-8") as fh:
            for rec in kept:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return removed


def get_queue_stats(device_id: str) -> dict:
    """Get statistics about the queue for a device."""
    path = _queue_path(device_id)
    if not path.exists():
        return {"total": 0, "synced": 0, "pending": 0}

    total = synced = pending = 0
    with _LOCK:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                total += 1
                if rec.get("synced"):
                    synced += 1
                else:
                    pending += 1
    return {"total": total, "synced": synced, "pending": pending}


def list_unsynced(device_id: str) -> List[QueuedPrediction]:
    """Return all predictions that have not yet been synced."""
    return list_pending(device_id)


def purge_synced(device_id: str, max_age_seconds: int = QUEUE_TTL_SECONDS) -> int:
    """Remove synced predictions older than max_age_seconds."""
    return purge_old(device_id, max_age_seconds=max_age_seconds)


def make_item_id() -> str:
    """Generate a unique item ID for a prediction."""
    return f"q{int(time.time() * 1000)}{os.urandom(3).hex()}"
