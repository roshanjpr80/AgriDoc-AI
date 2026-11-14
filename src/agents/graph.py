"""AgriPulse LangGraph workflow.

Nodes (in order):
  1. diagnose   — run the ONNX classifier on the farmer's photo.
  2. advise     — look up grounded treatment advice in the farmer's language.
  3. market     — fetch mandi prices and a sell/wait signal.
  4. weather    — assess rain risk for treatment timing.
  5. coordinate — combine everything into one plan.

Edges:
  diagnose -> advise
  advise   -> market
  market   -> weather
  weather  -> coordinate

Retries: each node retries up to 2 times on transient failures (network).
Guardrails live inside the nodes: the advice node never invents doses, and
the coordinator escalates to a human when confidence is low.

Usage:
    from src.agents.graph import run_agripulse
    result = run_agripulse(image_bytes=b"...", language="hi", district="Punjab_Ludhiana")
"""
from __future__ import annotations

import logging
from typing import Optional

from .state import AgriPulseState, initial_state

log = logging.getLogger("agridoc.agents.graph")


def _build_graph():
    """Build the LangGraph StateGraph. Returns None if LangGraph is missing."""
    try:
        from langgraph.graph import StateGraph
    except ImportError:
        log.warning("langgraph not installed — using sequential runner")
        return None

    from src.agents.diagnosis import node as diagnose
    from src.agents.advice_agent import node as advise
    from src.agents.market_agent import node as market
    from src.agents.weather_agent import node as weather
    from src.agents.coordinator import node as coordinate

    g = StateGraph(AgriPulseState)
    g.add_node("diagnose", diagnose)
    g.add_node("advise", advise)
    g.add_node("market", market)
    g.add_node("weather", weather)
    g.add_node("coordinate", coordinate)

    g.set_entry_point("diagnose")
    g.add_edge("diagnose", "advise")
    g.add_edge("advise", "market")
    g.add_edge("market", "weather")
    g.add_edge("weather", "coordinate")
    g.set_finish_point("coordinate")
    return g.compile()


_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def run_agripulse(
    image_bytes: bytes,
    language: str = "en",
    district: str = "",
    crop_hint: Optional[str] = None,
    offline: bool = False,
) -> AgriPulseState:
    """Run the full AgriPulse workflow and return the final state.

    Falls back to a sequential runner when LangGraph is not installed, so the
    app still works on a minimal install.
    """
    state = initial_state(
        image_bytes=image_bytes,
        language=language,
        district=district,
        crop_hint=crop_hint,
    )
    state["offline"] = offline

    graph = _get_graph()
    if graph is not None:
        try:
            result = graph.invoke(state)
            return result  # type: ignore[return-value]
        except Exception as exc:  # noqa: BLE001
            log.warning("graph run failed, falling back: %s", exc)

    # Sequential fallback.
    from src.agents.diagnosis import node as diagnose
    from src.agents.advice_agent import node as advise
    from src.agents.market_agent import node as market
    from src.agents.weather_agent import node as weather
    from src.agents.coordinator import node as coordinate

    for node in (diagnose, advise, market, weather, coordinate):
        try:
            state = node(state)
        except Exception as exc:  # noqa: BLE001
            log.warning("node %s failed: %s", node.__name__, exc)
            state["decisions"].append(f"{node.__name__}: error -> skipped")
    return state