"""Grounded belief updates. Agents submit Observations; only this module changes beliefs.

Guardrails (spec §6):
- assessment_answer -> BKT mastery, only when accepted (reliable correctness + topic mapping)
- self_confidence  -> separate self-report belief; never touches mastery
- goal/interest/preference -> semantic proposition with provenance
- mood -> short-lived self-report (expires 24h); never a trait
- source records -> workload facts (counts of upcoming deadlines)
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from ..schemas import Belief, BeliefScope, BeliefUpdate, Observation, SemanticProposition, SourceRecord
from ..timeutil import iso, now, now_iso, parse
from . import bkt, catalog, store

PROPOSITION_TYPES = {"goal": "goal", "interest": "interest", "preference": "preference"}


def mastery_belief_id(student_id: str, concept_id: str) -> str:
    return f"belief_{student_id}_{concept_id}_mastery"


def confidence_belief_id(student_id: str, concept_id: str) -> str:
    return f"belief_{student_id}_{concept_id}_selfconf"


def recompute_mastery(student_id: str, concept_id: str) -> Optional[BeliefUpdate]:
    """Replay all accepted assessment answers chronologically (idempotent, order-independent)."""
    obs = [o for o in store.list_observations(student_id, concept_id=concept_id, event_type="assessment_answer")
           if o.status == "accepted" and isinstance(o.payload.get("correct"), bool)]
    if not obs:
        return None
    obs.sort(key=lambda o: (o.occurred_at, o.event_id))
    p = bkt.replay([bool(o.payload["correct"]) for o in obs])
    c = catalog.concept(concept_id)
    b = Belief(
        id=mastery_belief_id(student_id, concept_id), student_id=student_id,
        scope=BeliefScope(level="concept", course_id=c["course_id"] if c else obs[0].course_id, concept_id=concept_id),
        key="knowledge.mastery", value=round(p, 3), evidence_strength=bkt.evidence_strength(len(obs)),
        status="estimated", evidence_ids=[o.event_id for o in obs], updated_at=now_iso())
    return store.put_belief(b)


def _apply(o: Observation) -> list[BeliefUpdate]:
    updates: list[BeliefUpdate] = []
    et = o.event_type
    if et == "assessment_answer":
        if o.status == "accepted" and o.concept_id:
            u = recompute_mastery(o.student_id, o.concept_id)
            if u:
                updates.append(u)
    elif et == "self_confidence" and o.concept_id:
        val = float(o.payload.get("value", 0))
        c = catalog.concept(o.concept_id)
        u = store.put_belief(Belief(
            id=confidence_belief_id(o.student_id, o.concept_id), student_id=o.student_id,
            scope=BeliefScope(level="concept", course_id=c["course_id"] if c else o.course_id, concept_id=o.concept_id),
            key="knowledge.self_confidence", value=round(max(0.0, min(1.0, val)), 2), evidence_strength="weak",
            status="self_reported", evidence_ids=[o.event_id], updated_at=now_iso()))
        if u:
            updates.append(u)
    elif et in PROPOSITION_TYPES:
        statement = str(o.payload.get("statement", "")).strip()
        if statement:
            store.put_proposition(SemanticProposition(
                id=f"prop_{o.event_id}", student_id=o.student_id, statement=statement,
                category=PROPOSITION_TYPES[et], scope=o.course_id or "global", status="self_reported",
                evidence_ids=[o.event_id], updated_at=o.occurred_at))
    elif et == "mood":
        start = parse(o.occurred_at) or now()
        u = store.put_belief(Belief(
            id=f"belief_{o.student_id}_motivation_selfreport", student_id=o.student_id,
            scope=BeliefScope(level="global"), key="motivation.self_report",
            value=str(o.payload.get("statement", ""))[:200], evidence_strength="weak", status="self_reported",
            evidence_ids=[o.event_id], updated_at=now_iso(), expires_at=iso(start + timedelta(hours=24))))
        if u:
            updates.append(u)
    elif et == "study_session_completed":
        n = len(store.list_observations(o.student_id, event_type="study_session_completed"))
        u = store.put_belief(Belief(
            id=f"belief_{o.student_id}_engagement_sessions", student_id=o.student_id,
            scope=BeliefScope(level="global"), key="engagement.sessions_completed", value=float(n),
            evidence_strength=bkt.evidence_strength(n), status="source_fact",
            evidence_ids=[x.event_id for x in store.list_observations(o.student_id, event_type="study_session_completed")],
            updated_at=now_iso()))
        if u:
            updates.append(u)
    return updates


def ingest_observations(observations: list[Observation]) -> tuple[int, int, int, list[BeliefUpdate]]:
    """Returns (accepted, duplicates, pending_review, belief_updates). Re-ingest is a no-op."""
    accepted = dup = pending = 0
    updates: list[BeliefUpdate] = []
    for o in sorted(observations, key=lambda x: (x.occurred_at, x.event_id)):
        if not store.insert_observation(o):
            dup += 1
            continue
        if o.status == "pending_review":
            pending += 1
            continue
        accepted += 1
        updates.extend(_apply(o))
    return accepted, dup, pending, updates


def recompute_workload(student_id: str) -> list[BeliefUpdate]:
    """Per-course count of incomplete assignments due in the next 7 days (source-backed fact)."""
    horizon = now() + timedelta(days=7)
    updates = []
    assignments = store.list_records(student_id, kind="assignment")
    for c in catalog.courses():
        due = [a for a in assignments if a.course_id == c["id"] and not a.metadata.get("completed")
               and (d := parse(a.occurred_at)) and now() <= d <= horizon]
        u = store.put_belief(Belief(
            id=f"belief_{student_id}_{c['id']}_workload", student_id=student_id,
            scope=BeliefScope(level="course", course_id=c["id"]), key="workload.upcoming_due",
            value=float(len(due)), evidence_strength="strong" if due else "none", status="source_fact",
            evidence_ids=sorted(a.id for a in due), updated_at=now_iso()))
        if u:
            updates.append(u)
    return updates


def ingest_records(records: list[SourceRecord]) -> tuple[int, int]:
    added = dup = 0
    for r in records:
        if store.upsert_record(r):
            added += 1
        else:
            dup += 1
    return added, dup
