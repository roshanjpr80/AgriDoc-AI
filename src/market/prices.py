"""Mandi price ingestion with disk caching.

Sources (public, free, no auth):
  * Agmarknet: https://agmarknet.gov.in/api/prices
  * e-NAM:     https://enam.gov.in/apmc/api/prices

Responses are cached to ``data/market/<crop>/<district>.json`` for 24h so the
app works offline and stays within the source's rate limits. All HTTP errors
degrade to the cached value or an empty result — never raise to the caller.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from configs import PKG_ROOT

log = logging.getLogger("agridoc.market")

_CACHE_DIR = PKG_ROOT / "data" / "market"
_CACHE_TTL = 24 * 3600  # 1 day


@dataclass
class PriceRecord:
    crop: str
    district: str
    state: str
    min_price: float
    max_price: float
    modal_price: float
    unit: str
    ts: float
    source: str


def _cache_path(crop: str, district: str) -> Path:
    return _CACHE_DIR / crop / f"{district}.json"


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return time.time() - path.stat().st_mtime < _CACHE_TTL


def cached_price(crop: str, district: str) -> Optional[PriceRecord]:
    """Return a cached price record if it is still fresh, else None."""
    path = _cache_path(crop, district)
    if not _is_fresh(path):
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return PriceRecord(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        log.warning("cache read failed for %s/%s: %s", crop, district, exc)
        return None


def cache_prices(records: List[PriceRecord]) -> None:
    """Write price records to the disk cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for rec in records:
        path = _cache_path(rec.crop, rec.district)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(asdict(rec), fh, ensure_ascii=False)


def fetch_price(
    crop: str,
    district: str = "",
    state: str = "",
    offline: bool = False,
) -> Optional[PriceRecord]:
    """Fetch the latest price for *crop*.

    Order: cache -> Agmarknet -> e-NAM -> None. Never raises.
    """
    cached = cached_price(crop, district)
    if cached is not None:
        return cached
    if offline or os.environ.get("AGRIDOC_OFFLINE", "0") == "1":
        return None

    record = _fetch_agmarknet(crop, district, state)
    if record is None:
        record = _fetch_enam(crop, district, state)
    if record is not None:
        cache_prices([record])
    return record


def _fetch_agmarknet(crop: str, district: str, state: str) -> Optional[PriceRecord]:
    """Query the public Agmarknet price API."""
    try:
        import urllib.parse
        import httpx

        base = "https://agmarknet.gov.in/api/prices"
        params = {"commodity": crop, "district": district, "state": state}
        url = base + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})
        resp = httpx.get(url, headers={"User-Agent": "AgriDocAI/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        records = data.get("records") or data.get("data") or []
        if not records:
            return None
        rec = records[0]
        return PriceRecord(
            crop=crop,
            district=rec.get("district") or district,
            state=rec.get("state") or state,
            min_price=float(rec.get("min_price") or rec.get("min") or 0),
            max_price=float(rec.get("max_price") or rec.get("max") or 0),
            modal_price=float(rec.get("modal_price") or rec.get("modal") or 0),
            unit=rec.get("unit") or "quintal",
            ts=time.time(),
            source="agmarknet",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("agmarknet fetch failed for %s: %s", crop, exc)
        return None


def _fetch_enam(crop: str, district: str, state: str) -> Optional[PriceRecord]:
    """Query the public e-NAM price API."""
    try:
        import urllib.parse
        import httpx

        base = "https://enam.gov.in/apmc/api/prices"
        params = {"commodity": crop, "apmc": district}
        url = base + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})
        resp = httpx.get(url, headers={"User-Agent": "AgriDocAI/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        records = data.get("records") or data.get("data") or []
        if not records:
            return None
        rec = records[0]
        return PriceRecord(
            crop=crop,
            district=rec.get("apmc") or rec.get("district") or district,
            state=rec.get("state") or state,
            min_price=float(rec.get("min_price") or rec.get("min") or 0),
            max_price=float(rec.get("max_price") or rec.get("max") or 0),
            modal_price=float(rec.get("modal_price") or rec.get("modal") or 0),
            unit=rec.get("unit") or "quintal",
            ts=time.time(),
            source="enam",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("enam fetch failed for %s: %s", crop, exc)
        return None