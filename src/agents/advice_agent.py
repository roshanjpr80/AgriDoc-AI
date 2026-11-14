"""Advice Agent node for AgriPulse.

Looks up grounded treatment advice from the knowledge base in the farmer's
language. Never invents doses: every claim cites a KB entry. Sets
``call_expert`` when confidence is low or the disease is severe.
"""
from __future__ import annotations

import logging

from .state import AgriPulseState

log = logging.getLogger("agridoc.agents.advice")

# Diseases that always warrant an expert call regardless of CV confidence.
SEVERE_DISEASES = {
    "HLB (Citrus greening)",
    "Late blight",
    "Bacterial spot",
    "Black rot",
    "Esca (Black Measles)",
}


def _tool(class_label: str, language: str = "en") -> dict:
    """Return grounded advice for a diagnosis. Raises KeyError if unknown."""
    from src.advice.engine import build_advice

    return build_advice(class_label, lang=language)


def node(state: AgriPulseState) -> AgriPulseState:
    """LangGraph node: fetch advice and safety warnings."""
    class_label = state.get("predicted_class", "")
    language = state.get("language", "en")
    if not class_label:
        state["call_expert"] = True
        state["decisions"].append("advice: no diagnosis -> escalate to expert")
        return state

    try:
        advice = _tool(class_label, language)
    except KeyError:
        state["call_expert"] = True
        state["decisions"].append(
            f"advice: no KB entry for {class_label} -> escalate to expert"
        )
        return state

    state["advice_text"] = advice["advice"]
    state["advice_source"] = advice.get("source", "Unknown")
    state["advice_grounded"] = advice.get("grounded", False)
    state["treatment_options"] = [
        line.strip("• ").strip()
        for line in advice["advice"].splitlines()
        if line.startswith("•")
    ]
    state["safety_warnings"] = _safety_warnings(advice)
    state["call_expert"] = bool(state.get("uncertain", False)) or _is_severe(class_label)
    state["decisions"].append(
        f"advice: {len(state['treatment_options'])} options, "
        f"call_expert={state['call_expert']}"
    )
    return state


def _is_severe(class_label: str) -> bool:
    """A disease is severe if its name appears in the SEVERE set."""
    return any(s.lower() in class_label.lower() for s in SEVERE_DISEASES)


def _safety_warnings(advice: dict) -> list[str]:
    """Extract safety warnings from the KB entry.

    The KB stores chemical options with dosage text; any chemical whose dose
    is not stated is flagged for an agriculture officer.
    """
    warnings = []
    entry = advice
    for chem in entry.get("chemical", []):
        if "dose" in chem.lower() or "verify" in chem.lower():
            warnings.append(chem)
    if entry.get("reviewed"):
        warnings.append(f"Source reviewed {entry['reviewed']}")
    return warnings