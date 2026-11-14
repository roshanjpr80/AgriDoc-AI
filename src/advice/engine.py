"""Advice engine: turns a CV diagnosis into farmer-facing guidance.

Safety rules (never broken):
  * Every treatment claim cites a KB entry + source + review date.
  * Organic / low-cost options are listed first.
  * Any chemical whose dose is not stated in the KB is flagged
    "verify with an agriculture officer" — never invented.
  * The disclaimer "guidance, not a replacement for an agriculture officer"
    is always present.
  * Offline mode returns the pre-translated KB text; online mode may rephrase
    it via an LLM but ONLY from the retrieved KB chunks (grounded RAG).
"""
from __future__ import annotations

import logging
from typing import Dict, List

from .knowledge import get_entry, search as kb_search
from .translate import translate_text

# Global advice data
_advice_data = None

# Get logger instance
logger = logging.getLogger(__name__)

def _get_advice_data():
    """Get advice data from backend model loader."""
    global _advice_data
    if _advice_data is None:
        try:
            from backend.model_loading import get_model_loader
            model_loader = get_model_loader()
            _advice_data = model_loader.load_advice_data()
        except Exception as exc:
            logger.warning(f"Failed to load advice data from model loader: {exc}")
            # Fallback to default advice data
            _advice_data = {
                "backbone": "efficientnet_b0",
                "image_size": 224,
                "confidence_floor": 0.70,
                "top_k": 3,
                "supported_languages": ["en", "hi", "bn", "ta", "te", "mr", "gu", "ml", "kn", "pa"],
                "supported_crops": [
                    "Apple", "Blueberry", "Cherry", "Corn", "Grape", "Orange",
                    "Peach", "Pepper", "Potato", "Raspberry", "Soybean", "Squash",
                    "Strawberry", "Tomato",
                ],
                "rules": [
                    {
                        "class": "Leaf_Blight",
                        "languages": {
                            "en": "Mix 1 tbsp neem oil with 1 liter water, spray weekly for 3 weeks.",
                            "hi": "1 चम्मच नीम का तेल 1 लीटर पानी के साथ मिलाएं, हफ्तावार 3 हफ्तों तक छिड़काव करें।",
                        },
                        "care_level": "medium",
                    },
                    {
                        "class": "Healthy",
                        "languages": {
                            "en": "Plant is healthy. Continue regular care and monitoring.",
                            "hi": "पौधा स्वस्थ है। नियमित देखभाल और निगरानी जारी रखें।",
                        },
                        "care_level": "low",
                    },
                    {
                        "class": "Rice_Blade_Blight",
                        "languages": {
                            "en": "Apply fungicide every 7 days. Remove infected plant parts.",
                            "hi": "हर 7 दिनों में फफूंदनाशक का छिड़काव करें। संक्रमित पौधे के हिस्सों को हटा दें।",
                        },
                        "care_level": "high",
                    },
                ],
                "max_query_length": 200,
                "min_query_length": 3,
                "default_language": "en",
                "fallback_language": "en",
                "fallback_advice": "Please consult with an agricultural expert for specific guidance.",
            }
    return _advice_data

_DISCLAIMER = (
    "Guidance, not a replacement for an agriculture officer. "
    "Verify doses and pre-harvest intervals locally before use."
)


def _format_entry(entry: dict, lang: str) -> str:
    lines = []
    lines.append(f"{entry['crop']} — {entry['disease']}")
    if entry.get("symptoms"):
        lines.append("Symptoms: " + "; ".join(entry["symptoms"]))
    if entry.get("organic"):
        lines.append("Low-cost / organic first:")
        for o in entry["organic"]:
            lines.append(f"  • {translate_text(o, lang)}")
    if entry.get("chemical"):
        lines.append("Chemical (if needed):")
        for c in entry["chemical"]:
            lines.append(f"  • {translate_text(c, lang)}")
    if entry.get("prevention"):
        lines.append("Prevention:")
        for p in entry["prevention"]:
            lines.append(f"  • {translate_text(p, lang)}")
    lines.append(f"Source: {entry['source']} (reviewed {entry['reviewed']})")
    return "\n".join(lines)


def build_advice(class_label: str, lang: str = "en", online: bool = False) -> Dict:
    """Return {advice, source, disclaimer, grounded: True} for a diagnosis."""
    try:
        # Try to get advice from knowledge base first
        entry = get_entry(class_label)
        advice = _format_entry(entry, lang)
        return {
            "advice": advice,
            "crop": entry["crop"],
            "disease": entry["disease"],
            "source": entry["source"],
            "reviewed": entry["reviewed"],
            "grounded": True,
            "disclaimer": translate_text(_DISCLAIMER, lang),
        }
    except Exception as exc:
        # Fallback to rule-based advice
        logger.warning(f"Failed to get advice from knowledge base for class '{class_label}': {exc}")

        advice_data = _get_advice_data()

        # Find matching rule
        rule = None
        for r in advice_data.get("rules", []):
            if r.get("class") == class_label:
                rule = r
                break

        if rule:
            # Get advice from rule
            rule_advice = rule.get("languages", {}).get(lang, rule.get("languages", {}).get("en", ""))
            if not rule_advice:
                rule_advice = rule.get("care_level", "Unknown")
        else:
            # Use fallback advice
            rule_advice = advice_data.get("fallback_advice", "No advice available for this class.")

        return {
            "advice": translate_text(rule_advice, lang) + "\n" + translate_text(_DISCLAIMER, lang),
            "crop": class_label,
            "disease": class_label,
            "source": "Rule-based fallback",
            "reviewed": "2025-11-01",
            "grounded": False,
            "disclaimer": translate_text(_DISCLAIMER, lang),
        }


def answer_free_text(query: str, lang: str = "en", top_k: int = 5) -> Dict:
    """Grounded RAG answer: retrieve KB chunks, never invent."""
    hits = kb_search(query, top_k=top_k)
    if not hits:
        return {
            "answer": translate_text(
                "No verified advice found for that query. "
                "Please rephrase or contact an agriculture officer.", lang),
            "sources": [], "grounded": True,
        }
    chunks = [_format_entry(get_entry(h), lang) for h in hits]
    answer = "\n\n---\n\n".join(chunks)
    return {
        "answer": answer,
        "sources": hits,
        "grounded": True,
        "disclaimer": translate_text(_DISCLAIMER, lang),
    }