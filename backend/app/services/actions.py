"""Approval-gated external actions. Nothing is written externally without an explicit approve call
whose confirmed title/start/duration exactly match the stored proposal."""
from __future__ import annotations

from fastapi import HTTPException

from ..connectors import google_calendar
from ..memory import store
from ..schemas import ApproveRequest, ApproveResponse, Recommendation
from ..timeutil import now_iso, parse


def _same_time(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return a == b
    pa, pb = parse(a), parse(b)
    return pa is not None and pb is not None and pa == pb


def approve(rec_id: str, req: ApproveRequest) -> ApproveResponse:
    rec = store.get_recommendation(rec_id)
    if not rec or rec.student_id != req.student_id:
        raise HTTPException(404, "Recommendation not found for this student")
    if rec.status in ("executed", "executed_simulated"):
        # Idempotent: a repeated approve never writes twice.
        return ApproveResponse(recommendation=rec, executed=rec.status == "executed",
                               simulated=rec.status == "executed_simulated",
                               result_detail=f"Already processed: {rec.result_detail}")
    if rec.status != "pending":
        raise HTTPException(409, f"Recommendation is {rec.status}, not pending")
    c = req.confirm
    if c.title != rec.title or c.duration_minutes != rec.duration_minutes or not _same_time(c.suggested_start, rec.suggested_start):
        raise HTTPException(409, "Confirmed details do not match the proposal; refresh and review again")
    act = rec.proposed_action
    if not act or act.provider != "google_calendar" or act.operation != "create_event" or not rec.suggested_start or not rec.duration_minutes:
        rec.status, rec.result_detail = "approved", "Approved (no external action attached)."
        store.put_recommendation(rec)
        return ApproveResponse(recommendation=rec, executed=False, simulated=False, result_detail=rec.result_detail)

    description = f"{rec.reason}\n\nCreated by MentorIA after your approval (recommendation {rec.id})."
    if google_calendar.write_enabled():
        try:
            res = google_calendar.create_event(rec.id, rec.title, rec.suggested_start, rec.duration_minutes, description)
        except Exception as e:
            rec.status, rec.result_detail = "failed", f"Google Calendar write failed: {e}"
            store.put_recommendation(rec)
            return ApproveResponse(recommendation=rec, executed=False, simulated=False, result_detail=rec.result_detail)
        store.log_action(f"act_{rec.id}", rec.id, {"simulated": False, "event": res, "at": now_iso()})
        rec.status = "executed"
        rec.result_detail = ("Event already existed in Google Calendar (no duplicate created)." if res.get("duplicate")
                             else "Created in Google Calendar.") + (f" {res.get('htmlLink')}" if res.get("htmlLink") else "")
    else:
        store.log_action(f"act_{rec.id}", rec.id, {"simulated": True, "title": rec.title, "start": rec.suggested_start,
                                                   "duration_minutes": rec.duration_minutes, "at": now_iso()})
        rec.status = "executed_simulated"
        rec.result_detail = ("SIMULATED — Google Calendar write is not configured/verified, so nothing was written externally. "
                             "The approved block is recorded locally.")
    store.put_recommendation(rec)
    return ApproveResponse(recommendation=rec, executed=rec.status == "executed", simulated=rec.status == "executed_simulated",
                           result_detail=rec.result_detail)


def reject(rec_id: str, student_id: str) -> Recommendation:
    rec = store.get_recommendation(rec_id)
    if not rec or rec.student_id != student_id:
        raise HTTPException(404, "Recommendation not found for this student")
    if rec.status not in ("pending", "rejected"):
        raise HTTPException(409, f"Recommendation is {rec.status}, cannot reject")
    rec.status, rec.result_detail = "rejected", "Rejected by student. No external action taken."
    store.put_recommendation(rec)
    return rec
