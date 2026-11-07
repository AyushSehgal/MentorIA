from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ..memory import catalog, context, store, updates
from ..schemas import (ContextResponse, GraphResponse, HistoryResponse, IngestRequest, IngestResponse, Observation,
                       PropositionStatusRequest, SelfConfidenceRequest, SemanticProposition, StudentModel)
from ..timeutil import now_iso

router = APIRouter(prefix="/api/memory")


@router.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    for r in req.source_records:
        r.student_id = req.student_id
    for o in req.observations:
        o.student_id = req.student_id
    updates.ingest_records(req.source_records)
    acc, dup, pend, ups = updates.ingest_observations(req.observations)
    ups += updates.recompute_workload(req.student_id) if req.source_records else []
    return IngestResponse(accepted=acc, duplicates=dup, pending_review=pend, belief_updates=ups)


@router.get("/context", response_model=ContextResponse)
def get_context(student_id: str = "demo_student", query: str = "", agent: str = "orchestrator"):
    return context.build_context(student_id, query, agent)


@router.get("/model", response_model=StudentModel)
def model(student_id: str = "demo_student"):
    return context.student_model(student_id)


@router.get("/graph", response_model=GraphResponse)
def graph(student_id: str = "demo_student"):
    return context.graph(student_id)


@router.get("/history", response_model=HistoryResponse)
def history(student_id: str = "demo_student"):
    obs = sorted(store.list_observations(student_id), key=lambda o: o.occurred_at, reverse=True)
    return HistoryResponse(observations=obs, belief_updates=store.list_belief_updates(student_id))


@router.post("/self_confidence")
def self_confidence(req: SelfConfidenceRequest):
    c = catalog.concept(req.concept_id)
    if not c:
        raise HTTPException(404, "Unknown concept")
    ts = now_iso()
    # Unique per request: now_iso() has 1 s resolution, and a repeated event_id would be dropped as a duplicate,
    # silently losing a quick second adjustment of the slider.
    o = Observation(event_id=f"obs_ui_conf_{req.concept_id}_{ts}_{uuid4().hex[:8]}", student_id=req.student_id, source="self_report",
                    event_type="self_confidence", course_id=c["course_id"], concept_id=req.concept_id, occurred_at=ts,
                    payload={"value": req.value, "statement": f"Set confidence to {req.value:.2f} in the Student Model view"})
    _, _, _, ups = updates.ingest_observations([o])
    return {"belief_updates": [u.model_dump() for u in ups]}


@router.post("/propositions/{pid}", response_model=SemanticProposition)
def set_proposition(pid: str, req: PropositionStatusRequest):
    p = store.get_proposition(pid)
    if not p or p.student_id != req.student_id:
        raise HTTPException(404, "Proposition not found")
    p.status, p.updated_at = req.status, now_iso()
    store.put_proposition(p)
    return p
