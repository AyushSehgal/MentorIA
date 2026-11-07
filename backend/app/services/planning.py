"""Weekly prioritization: transparent heuristic, not a trained recommender.

priority = (0.4 + 0.6·goal_relevance) × concept_gap × (0.3 + 0.7·deadline_urgency) × feasible_time
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from ..memory import catalog, store
from ..memory.context import concept_states, goal_concepts, obs_evidence, record_evidence
from ..schemas import ConceptState, EvidenceRef, Factor, FreeWindow, ProposedAction, Recommendation, SourceRecord
from ..timeutil import human, iso, now, now_iso, parse
from .aggregation import free_windows

UNKNOWN_GAP = 0.25
SESSION_MIN = 50


@dataclass
class Priority:
    concept: ConceptState
    score: float
    factors: list[Factor]
    deadline: Optional[SourceRecord]
    window: Optional[FreeWindow]
    evidence: list[EvidenceRef] = field(default_factory=list)


def _pick_window(windows: list[FreeWindow], deadline: Optional[SourceRecord], used: set[str]) -> Optional[FreeWindow]:
    limit = parse(deadline.occurred_at) if deadline else now() + timedelta(days=7)
    earliest = now() + timedelta(minutes=45)
    cands = [w for w in windows if w.start not in used and parse(w.start) >= earliest
             and parse(w.start) + timedelta(minutes=SESSION_MIN) <= min(parse(w.end), limit)]
    # Student preference fixture: afternoons. Prefer windows starting 12:00–18:00, then earliest.
    cands.sort(key=lambda w: (not (12 <= parse(w.start).hour < 18), parse(w.start)))
    return cands[0] if cands else None


def priorities(student_id: str, limit: int = 3) -> list[Priority]:
    goals = goal_concepts(student_id)
    goal_courses = {catalog.concept(c)["course_id"] for c in goals if catalog.concept(c)}
    assignments = [a for a in store.list_records(student_id, kind="assignment") if not a.metadata.get("completed")
                   and (d := parse(a.occurred_at)) and now() <= d <= now() + timedelta(days=10)]
    windows = free_windows(student_id)
    out: list[Priority] = []
    for s in concept_states(student_id):
        related = sorted([a for a in assignments if s.concept_id in a.concept_ids], key=lambda a: a.occurred_at)
        if s.mastery is None and not related:
            continue  # no evidence and no deadline → nothing grounded to say
        deadline = related[0] if related else None
        days = (parse(deadline.occurred_at) - now()).total_seconds() / 86400 if deadline else None
        urgency = max(0.0, 1 - days / 10) if days is not None else 0.0
        gap = (1 - s.mastery) if s.mastery is not None else UNKNOWN_GAP
        goal = 1.0 if s.concept_id in goals else (0.5 if s.course_id in goal_courses else 0.2)
        window = _pick_window(windows, deadline, set())
        feasible = 1.0 if window else 0.3
        score = (0.4 + 0.6 * goal) * gap * (0.3 + 0.7 * urgency) * feasible
        f = [
            Factor(name="concept_gap", value=round(gap, 2), explanation=(
                f"1 − BKT estimate {s.mastery:.2f} from {s.correct + s.incorrect} graded answer(s)" if s.mastery is not None
                else "No graded evidence yet; neutral placeholder gap (not a measured weakness)")),
            Factor(name="deadline_urgency", value=round(urgency, 2), explanation=(
                f"“{deadline.title}” due {human(parse(deadline.occurred_at))}" if deadline else "No related deadline in the next 10 days")),
            Factor(name="goal_relevance", value=round(goal, 2), explanation=(
                "Directly linked to a stated goal" if goal == 1.0 else
                "Same course as a goal-linked concept" if goal == 0.5 else "Required coursework; not linked to stated goals")),
            Factor(name="feasible_time", value=feasible, explanation=(
                f"Free {window.minutes}-min window found before the deadline" if window else "No free window ≥50 min before the deadline")),
        ]
        ev = [e for e in s.evidence if e.provider == "documents"] + ([record_evidence(deadline)] if deadline else [])
        if s.blind_spot:
            f.append(Factor(name="blind_spot_candidate", value=1.0,
                            explanation=f"Self-confidence {s.self_confidence:.2f} vs estimate {s.mastery:.2f} (candidate signal, not a diagnosis)"))
            score *= 1.15
        out.append(Priority(concept=s, score=round(score, 3), factors=f, deadline=deadline, window=window, evidence=ev))
    out.sort(key=lambda p: -p.score)
    return out[:limit]


def propose_study_sessions(student_id: str, prios: list[Priority], max_recs: int = 2) -> list[Recommendation]:
    """Persist approval-gated study-session proposals with distinct, non-overlapping windows."""
    windows = free_windows(student_id)
    used: set[str] = set()
    recs = []
    for p in prios[:max_recs]:
        w = _pick_window(windows, p.deadline, used)
        if not w:
            continue
        used.add(w.start)
        s = p.concept
        start = parse(w.start)
        rid = f"rec_study_{s.concept_id}_{start.strftime('%Y%m%d')}"
        existing = store.get_recommendation(rid)
        if existing and existing.status != "pending":
            recs.append(existing)
            continue
        for old in store.list_recommendations(student_id, status="pending"):
            if old.id.startswith(f"rec_study_{s.concept_id}_") and old.id != rid:
                store.delete_recommendation(old.id)  # superseded, never acted on
        wrong = [str(o.payload.get("question_id")) for o in store.list_observations(student_id, s.concept_id, "assessment_answer")
                 if o.status == "accepted" and o.payload.get("correct") is False]
        title = f"Study: {s.label}"
        if p.deadline:
            title += f" before {p.deadline.title.split(':')[0]}"
        reason_bits = []
        if s.mastery is not None:
            reason_bits.append(f"Graded quiz evidence puts {s.label} at {s.mastery:.2f} ({s.incorrect} of {s.correct + s.incorrect} answers incorrect"
                               + (f": {', '.join(wrong)}" if wrong else "") + ")")
        else:
            reason_bits.append(f"No graded evidence yet for {s.label}, but work on it is due soon")
        if p.deadline:
            reason_bits.append(f"“{p.deadline.title}” is due {human(parse(p.deadline.occurred_at))}")
        if s.blind_spot:
            reason_bits.append("your self-confidence is notably higher than the estimate, so a check-in could surface a blind spot")
        rec = Recommendation(
            id=rid, student_id=student_id, type="study_session", title=title[:120], reason="; ".join(reason_bits) + ".",
            evidence_ids=[e.id for e in p.evidence], evidence=p.evidence, factors=p.factors, suggested_start=iso(start),
            duration_minutes=SESSION_MIN, status="pending",
            proposed_action=ProposedAction(provider="google_calendar", operation="create_event", args={
                "title": title[:120], "start": iso(start), "duration_minutes": SESSION_MIN, "concept_id": s.concept_id}),
            created_at=existing.created_at if existing else now_iso(),
            is_fixture=any(e.is_fixture for e in p.evidence))
        store.put_recommendation(rec)
        recs.append(rec)
    return recs
