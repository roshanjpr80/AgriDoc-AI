"""Verified crop-disease knowledge base.

Every entry is sourced from ICAR / state agriculture department guidelines and
carries a review date. This is the *only* source the advice engine may cite;
LLMs can rephrase it, never invent doses.

Layout: data/knowledge/advisory_rules.json
  { "<class>": { "crop", "disease", "symptoms": [...], "organic": [...],
                 "chemical": [...], "prevention": [...], "source": "...",
                 "reviewed": "YYYY-MM-DD" } }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from configs import load_config, PKG_ROOT

_kb_path = PKG_ROOT / Path(load_config("advice")["knowledge_json"])
_kb: Dict[str, dict] = {}


def _load() -> Dict[str, dict]:
    if not _kb_path.exists():
        raise FileNotFoundError(
            f"Knowledge base missing: {_kb_path}. Run scripts/build_knowledge.py."
        )
    with _kb_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_entry(class_label: str) -> dict:
    """Return the KB entry for a Crop___Disease class, or raise KeyError."""
    if class_label not in _kb:
        _kb.update(_load())
    if class_label not in _kb:
        raise KeyError(f"No advisory entry for '{class_label}'")
    return _kb[class_label]


def all_classes() -> List[str]:
    if not _kb:
        _kb.update(_load())
    return sorted(_kb.keys())


def has_entry(class_label: str) -> bool:
    if class_label not in _kb:
        _kb.update(_load())
    return class_label in _kb


def search(query: str, top_k: int = 5) -> List[str]:
    """Naive keyword search over symptoms + disease names (offline RAG)."""
    if not _kb:
        _kb.update(_load())
    q = query.lower()
    scored = []
    for label, e in _kb.items():
        text = " ".join([e.get("disease", ""), *e.get("symptoms", []),
                         *e.get("organic", ""), *e.get("chemical", "")]).lower()
        score = sum(1 for w in q.split() if w in text)
        if score:
            scored.append((score, label))
    scored.sort(reverse=True)
    return [label for _, label in scored[:top_k]]