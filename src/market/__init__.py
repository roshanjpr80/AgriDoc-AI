"""Market intelligence: mandi price ingestion, caching, and forecasting.

Data sources are public and free:
  * Agmarknet (agmarknet.gov.in) — daily APMC prices, CC BY 4.0.
  * e-NAM (enam.gov.in) — live mandi prices.

All responses are cached to disk so the app works offline and stays within
the source's rate limits. No API key is required for the public endpoints.
"""
from __future__ import annotations

from src.market.prices import fetch_price, cache_prices, cached_price
from src.market.forecast import price_forecast, simple_signal
from src.market.lookup import crop_for_class

__all__ = [
    "fetch_price",
    "cache_prices",
    "cached_price",
    "price_forecast",
    "simple_signal",
    "crop_for_class",
]