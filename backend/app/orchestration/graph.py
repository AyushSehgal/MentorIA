"""Central LangGraph orchestrator: route → (memory_update) → capability → compose."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..schemas import ChatRequest, ChatResponse
from . import nodes
from .llm import polish
from .tools import extract_contributions, route


class ChatState(TypedDict, total=False):
    student_id: str
    message: str
    history: list[dict]
    intent: str
    has_contributions: bool
    draft: str
    answer: str
    sources: list[Any]
    beliefs_used: list[str]
    uncertainties: list[str]
    recs: list[Any]
    memory_updates: list[str]
    llm_used: bool
    trace: list[str]


CAPABILITIES = {
    "struggling": nodes.struggling,
    "weekly_focus": nodes.weekly_focus,
    "course_next": nodes.course_next,
    "opportunities": nodes.opportunities,
    "sources": nodes.sources,
    "general": nodes.general,
}


def _node_for(intent: str) -> str:
    return "general" if intent == "memory_update" else intent


def route_node(state: ChatState) -> ChatState:
    intent = route(state["message"])
    has = bool(extract_contributions(state["student_id"], state["message"]))
    if intent == "general" and has:
        intent = "memory_update"
    return {"intent": intent, "has_contributions": has, "trace": state.get("trace", []) + [f"route:{intent}"]}


def after_route(state: ChatState) -> str:
    return "memory_update" if state["has_contributions"] else _node_for(state["intent"])


def after_memory(state: ChatState) -> str:
    return _node_for(state["intent"])


def compose(state: ChatState) -> ChatState:
    answer, used = polish(state["message"], state["draft"])
    return {"answer": answer, "llm_used": used, "trace": state["trace"] + ["compose" + ("+llm" if used else "")]}


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(ChatState)
    g.add_node("route", route_node)
    g.add_node("memory_update", nodes.memory_update)
    for name, fn in CAPABILITIES.items():
        g.add_node(name, fn)
        g.add_edge(name, "compose")
    g.add_node("compose", compose)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", after_route, ["memory_update", *CAPABILITIES])
    g.add_conditional_edges("memory_update", after_memory, list(CAPABILITIES))
    g.add_edge("compose", END)
    return g.compile()


def run_chat(req: ChatRequest) -> ChatResponse:
    out = build_graph().invoke({"student_id": req.student_id, "message": req.message,
                                "history": [m.model_dump() for m in req.history], "trace": [], "memory_updates": []})
    return ChatResponse(answer=out["answer"], intent=out["intent"], sources=out.get("sources", []),
                        beliefs_used=out.get("beliefs_used", []), uncertainties=out.get("uncertainties", []),
                        proposed_recommendations=out.get("recs", []), memory_updates=out.get("memory_updates", []),
                        llm_used=out.get("llm_used", False), trace=out.get("trace", []))
