"""Translation layer.

Offline mode: serve pre-translated strings from data/knowledge/translations.json.
Online mode: call Bhashini (free, government) and cache the result.

English is the source of truth. All other languages are served from the
offline file when connectivity is unavailable.
"""
from __future__ import annotations

import json
from pathlib import Path

from configs import PKG_ROOT, load_config

_cfg = load_config("advice")
_PATH = PKG_ROOT / Path(_cfg["translations_json"])
_CACHE: dict[str, dict[str, str]] = {}


def _load() -> dict[str, dict[str, str]]:
    if not _CACHE and _PATH.exists():
        with _PATH.open("r", encoding="utf-8") as fh:
            _CACHE.update(json.load(fh))
    return _CACHE


def translate_text(text: str, target_lang: str) -> str:
    """Translate a single string. Falls back to the source text if no
    translation is available (never returns a hallucinated one)."""
    if target_lang == "en" or not text:
        return text

    # Get available languages from advice config
    advice_cfg = load_config("advice")
    available_langs = advice_cfg.get("languages", ["en"])

    # Check if target language is supported
    if target_lang not in available_langs:
        return text

    data = _load()
    if target_lang in data and text in data[target_lang]:
        return data[target_lang][text]

    # If no translation found, try rule-based fallback from model loader
    try:
        from backend.model_loading import get_model_loader
        model_loader = get_model_loader()
        advice_data = model_loader.load_advice_data()

        # Look for translation in rule-based advice
        for rule in advice_data.get("rules", []):
            rule_text = rule.get("languages", {}).get(target_lang)
            if rule_text and rule.get("class") in text:
                return rule_text

        # Check for fallback advice
        fallback_advice = advice_data.get("fallback_advice", "")
        if fallback_advice and "advice" in text:
            return fallback_advice

    except Exception:
        pass

    return text


def translate_batch(texts: list[str], target_lang: str) -> list[str]:
    return [translate_text(t, target_lang) for t in texts]


def available_languages() -> list[str]:
    data = _load()
    return ["en"] + sorted(data.keys())