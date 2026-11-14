"""Expert review queue for "was this correct?" feedback.

Every CV prediction is a chance to improve. Farmer feedback is queued for an
agriculture officer to review; confirmed errors are logged to reports/failures.jsonl
for the next training cycle. Privacy: only class label + verdict, never the image
or device id by default.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from configs import PKG_ROOT, load_config

_path = PKG_ROOT / "reports" / "feedback.jsonl"
_lock = threading.Lock()


def submit(class_label: str, correct: bool, comment: str = "") -> dict:
    _path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "class": class_label,
        "correct": bool(correct),
        "comment": comment,
    }
    with _lock:
        with _path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"queued": True, "record": record}


def purge_user() -> dict:
    """Delete all feedback records (privacy: delete-my-data)."""
    if _path.exists():
        _path.unlink()
    return {"deleted": True, "path": str(_path)}


def summary() -> dict:
    if not _path.exists():
        return {"total": 0, "correct": 0, "incorrect": 0}
    total = correct = incorrect = 0
    with _path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            total += 1
            if r.get("correct"):
                correct += 1
            else:
                incorrect += 1
    return {"total": total, "correct": correct, "incorrect": incorrect}