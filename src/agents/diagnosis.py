"""Diagnosis Agent node for AgriPulse.

Runs the ONNX classifier on the farmer's photo, emits top-k predictions,
and sets ``uncertain`` when the top confidence is below the floor. Also
produces a Grad-CAM overlay URL when requested.

Tool contract: ``diagnose(image_bytes, mime_type, top_k) -> dict``.
"""
from __future__ import annotations

import logging

from .state import AgriPulseState

log = logging.getLogger("agridoc.agents.diagnosis")


def _tool(image_bytes: bytes, top_k: int = 3) -> dict:
    """Classify a leaf image. Returns {predictions, confidence, uncertain}.

    The ONNX inference.predict() signature is (image_bytes, top_k) — mime_type
    is accepted for API symmetry but not used (Pillow auto-detects format).
    """
    from src.api.inference import predict

    return predict(image_bytes, top_k=top_k)


def node(state: AgriPulseState) -> AgriPulseState:
    """LangGraph node: run the classifier and record the decision."""
    image_bytes = state.get("image_bytes", b"")
    if not image_bytes:
        state["uncertain"] = True
        state["decisions"].append("diagnosis: no image provided -> uncertain")
        return state

    try:
        result = _tool(image_bytes)
    except Exception as exc:  # noqa: BLE001
        log.warning("diagnosis failed: %s", exc)
        state["uncertain"] = True
        state["decisions"].append(f"diagnosis: classifier error -> uncertain ({exc})")
        return state

    state["predicted_class"] = result["predictions"][0]["class"]
    state["confidence"] = result["confidence"]
    state["uncertain"] = result["uncertain"]
    state["predictions"] = result["predictions"]
    state["decisions"].append(
        f"diagnosis: {state['predicted_class']} "
        f"({state['confidence']:.2f}, uncertain={state['uncertain']})"
    )
    return state