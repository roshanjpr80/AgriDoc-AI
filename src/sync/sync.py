"""Queue sync: upload queued predictions when the network returns.

The device calls ``sync()`` periodically (or when connectivity is detected).
It uploads unsynced items, then reconciles duplicates: if the same image
was already predicted online, the server result wins and the queued item is
dropped. Farmer verdicts from the offline queue are merged into the expert
review queue on the server.

This module is device-side (pure stdlib + requests); the server side is
``/sync`` endpoint in the FastAPI app.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Dict, List, Optional

from src.sync.compress import CompressedImage, compress
from src.sync.queue import (
    QueuedPrediction,
    list_unsynced,
    mark_synced,
    purge_synced,
)

log = logging.getLogger("agridoc.sync")


def prepare_upload(device_id: str, budget: str = "mid") -> List[Dict]:
    """Compress every unsynced item for upload.

    Returns a list of dicts ready to be POSTed to /sync.
    """
    items = list_unsynced(device_id)
    out: List[Dict] = []
    for item in items:
        try:
            raw = _b64decode(item.image_b64)
            comp = compress(raw, budget=budget)
        except Exception as exc:  # noqa: BLE001
            log.warning("compress failed for %s: %s", item.id, exc)
            continue
        out.append(
            {
                "id": item.id,
                "ts": item.ts,
                "image_b64": _b64encode(comp.bytes),
                "mime_type": comp.mime_type,
                "predicted_class": item.predicted_class,
                "confidence": item.confidence,
                "uncertain": item.uncertain,
                "farmer_correct": item.farmer_correct,
                "farmer_comment": item.farmer_comment,
            }
        )
    return out


def apply_sync_result(device_id: str, result: Dict) -> Dict:
    """Apply the server's /sync response to the local queue.

    result shape:
      {"synced": [item_id, ...], "merged": [item_id, ...],
       "rejected": [item_id, ...], "server_predictions": {...}}
    """
    synced = mark_synced(device_id, result.get("synced", []))
    merged = mark_synced(device_id, result.get("merged", []))
    rejected = mark_synced(device_id, result.get("rejected", []))
    removed = purge_synced(device_id)
    return {
        "marked_synced": synced + merged + rejected,
        "purged": removed,
        "server_predictions": result.get("server_predictions", {}),
    }


def _b64decode(s: str) -> bytes:
    import base64

    return base64.b64decode(s)


def _b64encode(b: bytes) -> str:
    import base64

    return base64.b64encode(b).decode("ascii")