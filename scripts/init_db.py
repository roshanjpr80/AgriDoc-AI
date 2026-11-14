"""Create the AgriDoc AI database.

SQLite by default — no server, no docker, no install. Python's sqlite3 module
is built in. To use PostgreSQL instead, set AGRIDOC_DATABASE_URL before running.

Usage:
    python scripts/init_db.py
    AGRIDOC_DATABASE_URL=sqlite:///./data/agridoc.db python scripts/init_db.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so `from configs import ...` works.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATABASE_URL = os.environ.get("AGRIDOC_DATABASE_URL", "sqlite:///./data/agridoc.db")

if DATABASE_URL.startswith("sqlite"):
    # sqlite:///./data/agridoc.db  ->  ./data/agridoc.db
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    print(f"Using SQLite database: {db_path}")
elif DATABASE_URL.startswith("postgresql://"):
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)
    conn = psycopg2.connect(DATABASE_URL)
    print(f"Using PostgreSQL database")
else:
    print(f"ERROR: unsupported database URL scheme: {DATABASE_URL}")
    sys.exit(1)


def _column_sql(name: str, col_type: str, constraints: str = "") -> str:
    return f"{name} {col_type} {constraints}".strip()


# Schema

# Each row = one farmer's "was this correct?" verdict on a diagnosis.
# Privacy: stores only the class label + verdict, never the image or device id.
FEEDBACK_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,  -- ISO-8601 UTC
    class_label   TEXT    NOT NULL,
    correct       INTEGER NOT NULL,  -- 0 = wrong, 1 = correct
    comment       TEXT    NOT NULL DEFAULT '',
    district      TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_feedback_class ON feedback(class_label);
CREATE INDEX IF NOT EXISTS idx_feedback_ts    ON feedback(ts);
"""

# District-level outbreak tracking (from src/community).
# Aggregated, anonymous — no farmer is individually identifiable.
HOTSPOTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS hotspots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    district    TEXT    NOT NULL,
    crop        TEXT    NOT NULL,
    disease     TEXT    NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    severity    TEXT    NOT NULL DEFAULT 'medium'  -- low | medium | high
);

CREATE INDEX IF NOT EXISTS idx_hotspots_district ON hotspots(district);
CREATE INDEX IF NOT EXISTS idx_hotspots_ts       ON hotspots(ts);
"""

# Offline sync queue — predictions made offline, queued for later sync.
SYNC_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_queue (
    id          TEXT    PRIMARY KEY,  -- client-generated UUID
    ts          REAL    NOT NULL,     -- epoch seconds
    image_b64   TEXT    NOT NULL,
    mime_type   TEXT    NOT NULL,
    predicted_class TEXT NOT NULL,
    confidence  REAL    NOT NULL,
    uncertain   INTEGER NOT NULL,     -- 0/1
    farmer_correct INTEGER,            -- NULL if not yet answered
    farmer_comment TEXT NOT NULL DEFAULT '',
    synced      INTEGER NOT NULL DEFAULT 0  -- 0 = pending, 1 = synced
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_synced ON sync_queue(synced);
"""

# Model retraining log — tracks every training run and its outcome.
TRAINING_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS training_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    backbone    TEXT    NOT NULL,
    epochs      INTEGER NOT NULL,
    top1_acc    REAL    NOT NULL,
    top3_acc    REAL    NOT NULL,
    macro_f1    REAL    NOT NULL,
    checkpoint  TEXT    NOT NULL,
    notes       TEXT    NOT NULL DEFAULT ''
);
"""


def _exec_sql(conn, schema: str, label: str):
    if DATABASE_URL.startswith("postgresql://"):
        cur = conn.cursor()
        cur.execute(schema)
        conn.commit()
        cur.close()
    else:
        conn.executescript(schema)
    print(f"  [OK] {label} table(s) created")


def main():
    print(f"AgriDoc AI — database initialisation")
    print(f"  URL: {DATABASE_URL}")
    print()

    if DATABASE_URL.startswith("sqlite"):
        _exec_sql(conn, FEEDBACK_SCHEMA, "feedback")
        _exec_sql(conn, HOTSPOTS_SCHEMA, "hotspots")
        _exec_sql(conn, SYNC_SCHEMA, "sync_queue")
        _exec_sql(conn, TRAINING_LOG_SCHEMA, "training_log")
        conn.commit()
        conn.close()
        print(f"\nDone. Database file: {db_path}")
        print(f"  Size: {db_path.stat().st_size} bytes")
    elif DATABASE_URL.startswith("postgresql://"):
        cur = conn.cursor()
        for stmt in [FEEDBACK_SCHEMA, HOTSPOTS_SCHEMA, SYNC_SCHEMA, TRAINING_LOG_SCHEMA]:
            cur.execute(stmt)
        conn.commit()
        cur.close()
        conn.close()
        print("\nDone. PostgreSQL tables created.")

    print("\nTables created:")
    print("  feedback      — farmer 'was this correct?' verdicts")
    print("  hotspots      — district-level anonymous outbreak tracking")
    print("  sync_queue    — offline prediction queue")
    print("  training_log  — model retraining history")


if __name__ == "__main__":
    main()