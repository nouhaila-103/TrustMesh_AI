"""
TrustMesh AI - autonomous trust agent.

Built with LangGraph. The agent:
 1. Decides which CAMARA signals (via Nokia Network-as-Code) are relevant
    for the transaction and fetches them.
 2. Fuses the signals with a risk-scoring policy into a single trust score.
 3. Produces an explainable decision (APPROVE / CHALLENGE / BLOCK) with a
    natural-language reasoning chain (LLM if OPENAI_API_KEY is set,
    deterministic fallback otherwise so the demo never breaks on stage).
"""

import os
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from nac_client import check_reachability, check_sim_swap, verify_location


class TrustState(TypedDict, total=False):
    phone_number: str
    transaction_type: str
    claimed_latitude: Optional[float]
    claimed_longitude: Optional[float]
    signals: Dict[str, Any]
    risk_events: List[str]
    trust_score: float
    decision: str
    reasoning: str


def node_fetch_signals(state: TrustState) -> TrustState:
    """Orchestration step: call the CAMARA APIs relevant to this transaction."""
    phone_number = state["phone_number"]
    signals: Dict[str, Any] = {}

    sim_swap = check_sim_swap(phone_number, max_age_hours=240)
    signals["sim_swap"] = sim_swap.__dict__

    reachability = check_reachability(phone_number)
    signals["reachability"] = reachability.__dict__

    if state.get("claimed_latitude") is not None and state.get("claimed_longitude") is not None:
        location = verify_location(
            phone_number,
            latitude=state["claimed_latitude"],
            longitude=state["claimed_longitude"],
        )
        signals["location"] = location.__dict__

    state["signals"] = signals
    return state


def node_fuse_signals(state: TrustState) -> TrustState:
    """Rule-based fusion policy -> trust score (0-100) + flagged risk events."""
    score = 100.0
    events: List[str] = []
    signals = state["signals"]

    sim_swap = signals.get("sim_swap", {})
    if sim_swap.get("error"):
        score -= 5
        events.append("SIM swap signal unavailable (degraded trust)")
    elif sim_swap.get("swapped_recently"):
        score -= 45
        events.append("Recent SIM swap detected - strong account-takeover indicator")

    reachability = signals.get("reachability", {})
    if reachability.get("error"):
        score -= 5
        events.append("Device status signal unavailable (degraded trust)")
    elif reachability.get("reachable") is False:
        score -= 20
        events.append("Device currently unreachable on the network")

    location = signals.get("location")
    if location:
        if location.get("error"):
            score -= 5
            events.append("Location signal unavailable (degraded trust)")
        elif location.get("result_type") == "FALSE":
            score -= 30
            events.append("Device location does not match claimed transaction location")
        elif location.get("result_type") == "UNKNOWN":
            score -= 10
            events.append("Device location could not be confirmed")

    score = max(0.0, min(100.0, score))
    state["trust_score"] = score
    state["risk_events"] = events

    if score >= 70:
        state["decision"] = "APPROVE"
    elif score >= 40:
        state["decision"] = "CHALLENGE"
    else:
        state["decision"] = "BLOCK"

    return state


def node_explain(state: TrustState) -> TrustState:
    """Produce a human-readable, auditable reasoning chain for the decision."""
    events = state["risk_events"]
    score = state["trust_score"]
    decision = state["decision"]

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = (
                "You are TrustMesh AI, a fraud-risk explainer for a bank/fintech. "
                f"Trust score: {score}/100. Decision: {decision}. "
                f"Risk events detected: {events or ['none']}. "
                "In 2-3 short sentences, explain this decision for an audit log. "
                "Be precise and factual, no fluff."
            )
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
            state["reasoning"] = resp.choices[0].message.content.strip()
            return state
        except Exception:  # noqa: BLE001 - never let the demo crash on the LLM call
            pass

    # Deterministic fallback (also what runs with no API key at all)
    if not events:
        state["reasoning"] = (
            f"Trust score {score:.0f}/100. No risk signals were flagged across "
            f"SIM swap, device reachability, and location checks. Decision: {decision}."
        )
    else:
        state["reasoning"] = (
            f"Trust score {score:.0f}/100. Flagged: " + "; ".join(events) + f". Decision: {decision}."
        )
    return state


def build_agent():
    graph = StateGraph(TrustState)
    graph.add_node("fetch_signals", node_fetch_signals)
    graph.add_node("fuse_signals", node_fuse_signals)
    graph.add_node("explain", node_explain)

    graph.set_entry_point("fetch_signals")
    graph.add_edge("fetch_signals", "fuse_signals")
    graph.add_edge("fuse_signals", "explain")
    graph.add_edge("explain", END)

    return graph.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def evaluate_transaction(
    phone_number: str,
    transaction_type: str,
    claimed_latitude: Optional[float] = None,
    claimed_longitude: Optional[float] = None,
) -> TrustState:
    agent = get_agent()
    initial_state: TrustState = {
        "phone_number": phone_number,
        "transaction_type": transaction_type,
        "claimed_latitude": claimed_latitude,
        "claimed_longitude": claimed_longitude,
    }
    result = agent.invoke(initial_state)
    return result
