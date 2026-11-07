from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..memory import store, updates
from ..orchestration.graph import run_chat
from ..schemas import CompleteRequest, SourceRecord, ApproveRequest, ApproveResponse, ChatRequest, ChatResponse, Recommendation, RejectRequest
from ..services import actions, seed, suggestions

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return run_chat(req)


@router.get("/recommendations", response_model=list[Recommendation])
def recommendations(student_id: str = "demo_student", status: Optional[str] = None):
    return store.list_recommendations(student_id, status)


@router.post("/recommendations/{rec_id}/approve", response_model=ApproveResponse)
def approve(rec_id: str, req: ApproveRequest):
    return actions.approve(rec_id, req)


@router.post("/recommendations/{rec_id}/reject")
def reject(rec_id: str, req: RejectRequest):
    return {"recommendation": actions.reject(rec_id, req.student_id).model_dump()}


@router.post("/assignments/{record_id}/complete", response_model=SourceRecord)
def complete_assignment(record_id: str, req: CompleteRequest):
    r = store.set_completion(record_id, req.student_id, req.completed)
    if r is None:
        raise HTTPException(404, "Assignment not found for this student")
    updates.recompute_workload(req.student_id)
    return r


@router.post("/suggestions/{sug_id}/dismiss")
def dismiss_suggestion(sug_id: str, req: RejectRequest):
    suggestions.dismiss(req.student_id, sug_id)
    return {"ok": True}


@router.post("/demo/reset")
def demo_reset(student_id: str = "demo_student"):
    seed.reset(student_id)
    return {"ok": True}
