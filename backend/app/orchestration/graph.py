"""Central LangGraph orchestrator: route → (memory_update) → capability → compose."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..schemas import ChatRequest, ChatResponse
from . import nodes
from ..memory import catalog, store
from . import llm
from .llm import polish
from .tools import extract_contributions, is_self_question, route


class ChatState(TypedDict, total=False):
    student_id: str
    message: str
    mode: str
    about_me: bool  # About me question: answered from the student model, never saved
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
    llm_provider: str | None
    llm_note: str | None
    trace: list[str]


CAPABILITIES = {
    "struggling": nodes.struggling,
    "weekly_focus": nodes.weekly_focus,
    "course_next": nodes.course_next,
    "opportunities": nodes.opportunities,
    "sources": nodes.sources,
    "discussions": nodes.discussions,
    "deadlines": nodes.deadlines,
    "general": nodes.general,
}


def _node_for(intent: str) -> str:
    return "general" if intent == "memory_update" else intent


def course_names(student_id: str) -> list[str]:
    """Names of the student's courses (catalog + synced records), so the router can tell a course from an event."""
    names = {c["label"] for c in catalog.courses()}
    for p in ("canvas", "edstem", "piazza"):
        names |= {str(r.metadata["course_name"]) for r in store.list_records(student_id, provider=p) if r.metadata.get("course_name")}
    return sorted(n for n in names if n)


def route_node(state: ChatState) -> ChatState:
    if state.get("mode") == "tell":
        if is_self_question(state["message"]):
            return {"intent": "general", "about_me": True, "has_contributions": False,
                    "trace": state.get("trace", []) + ["route:tell:question"]}
        return {"intent": "memory_update", "has_contributions": True, "trace": state.get("trace", []) + ["route:tell"]}
    picked = llm.classify_intent(state["message"], course_names(state["student_id"]))  # cloud only; None -> keywords
    intent = picked or route(state["message"])
    has = bool(extract_contributions(state["student_id"], state["message"]))
    if intent == "general" and has:
        intent = "memory_update"
    how = ["router:llm"] if picked else []
    return {"intent": intent, "has_contributions": has, "trace": state.get("trace", []) + how + [f"route:{intent}"]}


def after_route(state: ChatState) -> str:
    if state["has_contributions"]:
        return "memory_update"
    return "about_me" if state.get("about_me") else _node_for(state["intent"])


def after_memory(state: ChatState) -> str:
    return "tell" if state.get("mode") == "tell" else _node_for(state["intent"])


def compose(state: ChatState) -> ChatState:
    # Never reworded by an LLM: "About me" confirmations (short) and the weekly plan (already story-shaped and
    # citation-dense; kept verbatim so it is instant and exact in demos). Other answers follow the privacy mode.
    if state.get("mode") == "tell" or state.get("intent") == "weekly_focus":
        return {"answer": state["draft"], "llm_used": False, "llm_provider": None, "llm_note": None,
                "trace": state["trace"] + ["compose"]}
    r = polish(state["message"], state["draft"])
    return {"answer": r.text, "llm_used": r.used, "llm_provider": r.provider, "llm_note": r.note,
            "trace": state["trace"] + ["compose" + (f"+{r.provider}" if r.used else "")]}


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(ChatState)
    g.add_node("route", route_node)
    g.add_node("memory_update", nodes.memory_update)
    for name, fn in CAPABILITIES.items():
        g.add_node(name, fn)
        g.add_edge(name, "compose")
    g.add_node("tell", nodes.tell)
    g.add_edge("tell", "compose")
    g.add_node("about_me", nodes.about_me)
    g.add_edge("about_me", "compose")
    g.add_node("compose", compose)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", after_route, ["memory_update", "about_me", *CAPABILITIES])
    g.add_conditional_edges("memory_update", after_memory, [*CAPABILITIES, "tell"])
    g.add_edge("compose", END)
    return g.compile()


def run_chat(req: ChatRequest) -> ChatResponse:
    out = build_graph().invoke({"student_id": req.student_id, "message": req.message, "mode": req.mode,
                                "history": [m.model_dump() for m in req.history], "trace": [], "memory_updates": []})
    intent = {"discussions": "sources", "deadlines": "sources"}.get(out["intent"], out["intent"])  # contract intents are fixed (CONTRACTS v1.9)
    return ChatResponse(answer=out["answer"], intent=intent, sources=out.get("sources", []),
                        beliefs_used=out.get("beliefs_used", []), uncertainties=out.get("uncertainties", []),
                        proposed_recommendations=out.get("recs", []), memory_updates=out.get("memory_updates", []),
                        llm_used=out.get("llm_used", False), llm_provider=out.get("llm_provider"),
                        llm_note=out.get("llm_note"), trace=out.get("trace", []))
