"""Dashboard aggregation: source cards + insights + pending recommendations."""
from __future__ import annotations

from datetime import timedelta

from ..config import settings
from ..memory import catalog, store
from ..memory.context import active_propositions, concept_states, obs_evidence, record_evidence, student_info
from ..schemas import (CalendarCard, ConnectorStatus, DashboardCards, DashboardResponse, DocumentsCard, GmailCard, Insight,
                       KnowledgeCounts, SourceCard)
from ..timeutil import human, now, now_iso, parse
from . import imports, opportunity_ranking, planning, suggestions
from .aggregation import free_windows, statuses


def _status(all_s: list[ConnectorStatus], p: str) -> ConnectorStatus:
    return next(s for s in all_s if s.provider == p)


def knowledge(student_id: str) -> KnowledgeCounts:
    goals = [p for p in active_propositions(student_id) if p.category in ("goal", "interest")]
    answers = [o for o in store.list_observations(student_id, event_type="assessment_answer") if o.status == "accepted"]
    items = sum(len(store.list_records(student_id, provider=p)) for p in ("canvas", "google_calendar", "gmail", "piazza"))
    return KnowledgeCounts(courses=len(catalog.courses()), concepts=len(catalog.concepts()),
                           documents=len(store.list_documents(student_id)), graded_answers=len(answers), goals=len(goals),
                           goal_sources=sum(len(p.evidence_ids) for p in goals), source_items=items,
                           imports=len(imports.list_imports(student_id)))


def insights(student_id: str) -> list[Insight]:
    out: list[Insight] = []
    goals = sorted([p for p in active_propositions(student_id) if p.category == "goal"], key=lambda p: -len(p.evidence_ids))
    for p in goals[:2]:
        n = len(p.evidence_ids)
        out.append(Insight(id=f"ins_goal_{p.id}", kind="goal", title="Your goal" + (f" — stated in {n} sources" if n > 1 else ""),
                           detail=p.statement, evidence=[obs_evidence(o) for eid in p.evidence_ids if (o := store.get_observation(eid))],
                           confidence_note="Self-reported. Correct it on the Student Model page if it's wrong."))
    states = concept_states(student_id)
    for s in states:
        if s.blind_spot:
            out.append(Insight(id=f"ins_blind_{s.concept_id}", kind="blind_spot", title=f"Possible blind spot: {s.label}",
                               detail=f"You rated your confidence {s.self_confidence:.2f}, but {s.incorrect} of {s.correct + s.incorrect} "
                                      f"graded answers were incorrect (estimate {s.mastery:.2f}).",
                               course_id=s.course_id, concept_id=s.concept_id,
                               evidence=[e for e in s.evidence if e.provider == "documents"],
                               confidence_note="Candidate signal from self-report vs. a few graded answers — not a diagnosis."))
        if s.stale:
            out.append(Insight(id=f"ins_stale_{s.concept_id}", kind="stale_evidence", title=f"Old evidence: {s.label}",
                               detail="The latest graded evidence is over 60 days old.", course_id=s.course_id,
                               concept_id=s.concept_id, evidence=s.evidence[:2], confidence_note="Estimate may be outdated."))
    for i, p in enumerate(planning.priorities(student_id, limit=2)):
        s = p.concept
        out.append(Insight(id=f"ins_focus_{s.concept_id}", kind="focus_area", title=f"Focus #{i + 1}: {s.label}",
                           detail="; ".join(f.explanation for f in p.factors[:3]) + ".", course_id=s.course_id,
                           concept_id=s.concept_id, evidence=p.evidence,
                           confidence_note="Heuristic priority (gap × urgency × goal relevance × time)."))
    soon = sorted([a for a in store.list_records(student_id, kind="assignment") if not a.metadata.get("completed")
                   and (d := parse(a.occurred_at)) and now() <= d <= now() + timedelta(hours=96)], key=lambda a: a.occurred_at)
    graded_concepts = {s.concept_id for s in states if s.mastery is not None}
    for a in soon:
        out.append(Insight(id=f"ins_due_{a.id}", kind="deadline", title=f"Due soon: {a.title}",
                           detail=f"{catalog.course_label(a.course_id)} — due {human(parse(a.occurred_at))}.",
                           course_id=a.course_id, evidence=[record_evidence(a)], confidence_note="Source-backed deadline."))
        missing = [c for c in a.concept_ids if c not in graded_concepts]
        if missing:
            out.append(Insight(id=f"ins_missing_{a.id}", kind="missing_evidence",
                               title=f"No graded evidence for {', '.join(catalog.concept_label(c) for c in missing)}",
                               detail=f"“{a.title}” covers this, but MentorIA has no graded quiz evidence to judge readiness.",
                               course_id=a.course_id, evidence=[record_evidence(a)],
                               confidence_note="Upload graded work to get an estimate."))
    return out


def dashboard(student_id: str) -> DashboardResponse:
    st = statuses(student_id)
    opps = opportunity_ranking.propose_event_recommendations(student_id, opportunity_ranking.rank(student_id))
    canvas = sorted(store.list_records(student_id, provider="canvas"), key=lambda r: r.occurred_at or "9999")
    def _still_relevant(r) -> bool:  # keep events that haven't ended yet (today's in-progress ones too)
        start = parse(r.occurred_at)
        if not start:
            return False
        end = parse(r.metadata.get("end")) or start + timedelta(hours=1)
        return end >= now() - timedelta(minutes=30)

    cal = sorted([r for r in store.list_records(student_id, provider="google_calendar") if _still_relevant(r)],
                 key=lambda r: r.occurred_at or "")
    piazza = sorted(store.list_records(student_id, provider="piazza"), key=lambda r: r.occurred_at or "", reverse=True)
    cards = DashboardCards(
        canvas=SourceCard(provider="canvas", label="Canvas — Due Soon", status=_status(st, "canvas"), items=canvas),
        google_calendar=CalendarCard(provider="google_calendar", label="Google Calendar — This Week",
                                     status=_status(st, "google_calendar"), items=cal, free_windows=free_windows(student_id)),
        gmail=GmailCard(provider="gmail", label="Gmail — Academic Opportunities", status=_status(st, "gmail"),
                        items=[r for r in store.list_records(student_id, provider="gmail")], opportunities=opps),
        piazza=SourceCard(provider="piazza", label="Piazza — Course Discussions", status=_status(st, "piazza"), items=piazza),
        documents=DocumentsCard(label="Documents — Academic Sources", status=_status(st, "documents"),
                                documents=store.list_documents(student_id)),
    )
    return DashboardResponse(student=student_info(student_id), generated_at=now_iso(), demo_mode=settings.demo_mode,
                             cards=cards, insights=insights(student_id),
                             recommendations=store.list_recommendations(student_id, status="pending"), connectors=st,
                             knowledge=knowledge(student_id), suggestions=suggestions.build(student_id))
