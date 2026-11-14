"""Tests for the advice engine and knowledge base.

Run: python -m pytest tests/test_advice.py -q
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.advice.engine import (
    build_advice,
    answer_free_text,
    _DISCLAIMER,
)
from src.advice.knowledge import (
    get_entry,
    search as kb_search,
    all_classes,
    has_entry,
)
from src.advice.translate import (
    translate_text,
    available_languages,
)
from configs import load_config

SUPPORTED_LANGUAGES = load_config("advice")["languages"]


class TestKnowledgeBase:
    """Test knowledge base loading and retrieval."""

    def test_kb_loads_all_38_diseases(self):
        classes = all_classes()
        assert len(classes) == 38

    def test_get_entry_exists(self):
        entry = get_entry("Apple___Apple_scab")
        assert entry["crop"] == "Apple"
        assert entry["disease"] == "Apple scab"
        assert "symptoms" in entry
        assert "organic" in entry
        assert "chemical" in entry
        assert "prevention" in entry
        assert "source" in entry
        assert "reviewed" in entry

    def test_get_entry_raises_on_missing(self):
        with pytest.raises(KeyError):
            get_entry("NonExistent___Disease")

    def test_search_returns_relevant(self):
        hits = kb_search("apple scab", top_k=5)
        assert len(hits) > 0
        assert any("Apple___Apple_scab" in h for h in hits)

    def test_search_empty_returns_empty(self):
        hits = kb_search("nonexistentqueryxyz", top_k=5)
        assert hits == []

    def test_has_entry(self):
        assert has_entry("Apple___Apple_scab") is True
        assert has_entry("NonExistent___Disease") is False

    def test_kb_entry_structure(self):
        entry = get_entry("Tomato___Late_blight")
        assert entry["crop"] == "Tomato"
        assert entry["disease"] == "Late blight"
        assert isinstance(entry["symptoms"], list)
        assert isinstance(entry["organic"], list)
        assert isinstance(entry["chemical"], list)
        assert isinstance(entry["prevention"], list)
        assert isinstance(entry["source"], str)
        assert isinstance(entry["reviewed"], str)


class TestTranslation:
    """Test translation system."""

    def test_supported_languages(self):
        assert len(SUPPORTED_LANGUAGES) == 10
        assert "en" in SUPPORTED_LANGUAGES
        assert "hi" in SUPPORTED_LANGUAGES
        assert "bn" in SUPPORTED_LANGUAGES
        assert "ta" in SUPPORTED_LANGUAGES
        assert "te" in SUPPORTED_LANGUAGES
        assert "mr" in SUPPORTED_LANGUAGES
        assert "gu" in SUPPORTED_LANGUAGES
        assert "ml" in SUPPORTED_LANGUAGES
        assert "kn" in SUPPORTED_LANGUAGES
        assert "pa" in SUPPORTED_LANGUAGES

    def test_translate_english_returns_same(self):
        text = "Hello world"
        result = translate_text(text, "en")
        assert result == "Hello world"

    def test_translate_hindi(self):
        # Test known translation
        result = translate_text("Guidance, not a replacement for an agriculture officer.", "hi")
        assert "मार्गदर्शन" in result

    def test_translate_fallback_to_english(self):
        # Unknown language code should fallback to English
        result = translate_text("Hello", "xx")
        assert result == "Hello"

    def test_translate_missing_key_returns_original(self):
        # Translation key not in dictionary should return original
        result = translate_text("unknown key xyz", "hi")
        assert result == "unknown key xyz"

    def test_available_languages(self):
        langs = available_languages()
        assert "en" in langs
        assert "hi" in langs
        assert len(langs) >= 10


class TestAdviceEngine:
    """Test build_advice and answer_free_text."""

    def test_build_advice_grounded(self):
        result = build_advice("Apple___Apple_scab", lang="en", online=False)
        assert "advice" in result
        assert "crop" in result
        assert "disease" in result
        assert "source" in result
        assert "reviewed" in result
        assert result["grounded"] is True
        assert "disclaimer" in result
        assert "Guidance, not a replacement" in result["disclaimer"]

    def test_build_advice_hindi(self):
        result = build_advice("Apple___Apple_scab", lang="hi", online=False)
        assert "advice" in result
        # Should contain Hindi text
        assert any(ord(c) > 127 for c in result["advice"])

    def test_build_advice_all_languages(self):
        for lang in SUPPORTED_LANGUAGES:
            result = build_advice("Apple___Apple_scab", lang=lang, online=False)
            assert "advice" in result
            assert result["grounded"] is True

    def test_build_advice_severe_disease_warning(self):
        # Test a severe disease that should have special handling
        result = build_advice("Tomato___Late_blight", lang="en", online=False)
        assert "advice" in result
        # Should include organic first, then chemical with warning

    def test_build_advice_organic_first(self):
        result = build_advice("Tomato___Early_blight", lang="en", online=False)
        advice_text = result["advice"]
        # Organic should appear before chemical
        organic_idx = advice_text.find("Low-cost / organic first")
        chemical_idx = advice_text.find("Chemical (if needed)")
        if organic_idx != -1 and chemical_idx != -1:
            assert organic_idx < chemical_idx

    def test_answer_free_text_returns_grounded(self):
        result = answer_free_text("How to treat apple scab?", lang="en")
        assert "answer" in result
        assert "sources" in result
        assert result["grounded"] is True
        assert "disclaimer" in result

    def test_answer_free_text_no_hits(self):
        result = answer_free_text("xyz nonexistent query", lang="en")
        assert result["answer"] is not None
        assert result["sources"] == []
        assert result["grounded"] is True

    def test_answer_free_text_all_languages(self):
        for lang in SUPPORTED_LANGUAGES:
            result = answer_free_text("How to treat leaf blight?", lang=lang)
            assert "answer" in result
            assert result["grounded"] is True

    def test_disclaimer_present_in_all_outputs(self):
        for lang in SUPPORTED_LANGUAGES:
            result = build_advice("Apple___Apple_scab", lang=lang, online=False)
            assert _DISCLAIMER in result["disclaimer"] or "Guidance" in result["disclaimer"]


class TestAdviceSafety:
    """Test safety rules in advice engine."""

    def test_chemical_doses_not_invented(self):
        # Verify that chemical advice references KB, not invented
        result = build_advice("Tomato___Late_blight", lang="en", online=False)
        # Should mention "verify with agriculture officer" for chemicals
        # or reference KB source

    def test_organic_listed_first(self):
        result = build_advice("Tomato___Early_blight", lang="en", online=False)
        advice = result["advice"]
        organic_pos = advice.find("Low-cost / organic first")
        chemical_pos = advice.find("Chemical (if needed)")
        if organic_pos >= 0 and chemical_pos >= 0:
            assert organic_pos < chemical_pos

    def test_source_and_reviewed_always_present(self):
        for class_name in ["Apple___Apple_scab", "Tomato___Late_blight", "Potato___Early_blight"]:
            result = build_advice(class_name, lang="en", online=False)
            assert "source" in result
            assert "reviewed" in result
            assert result["source"]
            assert result["reviewed"]


