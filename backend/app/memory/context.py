"""Read side of the memory layer: concept states, student model, graph, narrative, context retrieval."""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

from .. import db
from ..config import settings
from ..schemas import (Belief, ConceptState, ContextResponse, CourseSummary, EvidenceRef, GraphEdge, GraphNode,
                       GraphResponse, Observation, SemanticProposition, StudentInfo, StudentModel)
from ..timeutil import now, parse
from . import catalog, store
from .updates import confidence_belief_id, mastery_belief_id

BLIND_SPOT_GAP = 0.3
BLIND_SPOT_MIN_EVIDENCE = 2
STALE_DAYS = 60
STOP = set("the a an and or of to in on for with about what which how should i my me is are am do does this that week next "
           "take classes class course courses topics topic any can you be it at from as".split())


def profile() -> dict:
    """Student identity comes from settings; everything else is learned from imported data and chat."""
    return {"id": "demo_student", "name": settings.student_name, "completed_courses": []}


def student_info(student_id: str) -> StudentInfo:
    return StudentInfo(id=student_id, name=settings.student_name if student_id == "demo_student" else student_id,
                       timezone=settings.timezone)


def obs_evidence(o: Observation) -> EvidenceRef:
    """Human-readable provenance for an observation."""
    page, q = o.payload.get("page"), o.payload.get("question_id")
    if o.event_type == "assessment_answer":
        doc = o.payload.get("document_title") or "Assessment"
        label = f"{doc}, p. {page}, {q}" if page else f"{doc}, {q}"
        url = f"/api/documents/{o.payload.get('document_id')}/file#page={page}" if o.payload.get("document_id") else None
        provider = "documents"
    elif o.source == "document":
        label = f"{o.payload.get('document_title', 'Your document')}, p. {page}"
        url = f"/api/documents/{o.payload.get('document_id')}/file#page={page}" if o.payload.get("document_id") else None
        provider = "documents"
    elif o.source == "email":
        label = f"Email you sent: “{str(o.payload.get('subject', ''))[:60]}”"
        url, provider = None, "gmail"
    elif o.source == "chat":
        label = f"Chat: “{str(o.payload.get('statement', ''))[:60]}”"
        url, provider = None, "chat"
    else:
        label = f"{o.source.replace('_', ' ')}: “{str(o.payload.get('statement', o.event_type))[:70]}”"
        url, provider = None, o.source
    return EvidenceRef(id=o.event_id, label=label, provider=provider, source_record_id=o.source_record_id,
                       page=page, question_id=q, url=url, is_fixture=o.is_fixture)


def record_evidence(r) -> EvidenceRef:
    return EvidenceRef(id=r.id, label=f"{r.provider.replace('_', ' ').title()}: {r.title}", provider=r.provider,
                       source_record_id=r.id, url=r.source_url, is_fixture=r.is_fixture)


def active_propositions(student_id: str) -> list[SemanticProposition]:
    return [p for p in store.list_propositions(student_id) if p.status not in ("disputed", "expired")]


def goal_concepts(student_id: str) -> set[str]:
    out: set[str] = set()
    for p in active_propositions(student_id):
        if p.category in ("goal", "interest"):
            for eid in p.evidence_ids:
                o = store.get_observation(eid)
                if o:
                    out.update(o.payload.get("concept_ids", []))
            out.update(catalog.match_concepts(p.statement))
    return out


def concept_state(student_id: str, c: dict) -> ConceptState:
    m = store.get_belief(mastery_belief_id(student_id, c["id"]))
    sc = store.get_belief(confidence_belief_id(student_id, c["id"]))
    answers = [o for o in store.list_observations(student_id, concept_id=c["id"], event_type="assessment_answer")
               if o.status == "accepted"]
    correct = sum(1 for o in answers if o.payload.get("correct") is True)
    last = max((o.occurred_at for o in answers), default=None)
    stale = bool(last and (now() - parse(last)) > timedelta(days=STALE_DAYS))
    mastery = float(m.value) if m and m.value is not None else None
    conf = float(sc.value) if sc and sc.value is not None else None
    blind = bool(mastery is not None and conf is not None and len(answers) >= BLIND_SPOT_MIN_EVIDENCE
                 and conf - mastery >= BLIND_SPOT_GAP)
    ev = [obs_evidence(o) for o in answers]
    if sc:
        ev += [obs_evidence(o) for eid in sc.evidence_ids if (o := store.get_observation(eid))]
    return ConceptState(concept_id=c["id"], course_id=c["course_id"], label=c["label"], mastery=mastery,
                        evidence_strength=m.evidence_strength if m else "none", correct=correct,
                        incorrect=len(answers) - correct, self_confidence=conf, blind_spot=blind, stale=stale,
                        last_evidence_at=last, evidence=ev)


def concept_states(student_id: str, course_id: Optional[str] = None) -> list[ConceptState]:
    return [concept_state(student_id, c) for c in catalog.concepts() if not course_id or c["course_id"] == course_id]


def _global_beliefs(student_id: str) -> list[Belief]:
    out = []
    for b in store.list_beliefs(student_id):
        if b.scope.level == "concept":
            continue
        if b.expires_at and (e := parse(b.expires_at)) and e < now():
            b = b.model_copy(update={"status": "expired"})
        out.append(b)
    return out


def narrative(student_id: str) -> str:
    """Derived summary for chat consumption — regenerated from structured state, never a source of authority."""
    parts = []
    goals = [p for p in active_propositions(student_id) if p.category in ("goal", "interest")]
    if goals:
        parts.append("Stated goals/interests: " + "; ".join(
            g.statement.rstrip(". ") + (f" (stated in {len(g.evidence_ids)} sources)" if len(g.evidence_ids) > 1 else "")
            for g in goals) + ".")
    prefs = [p.statement for p in active_propositions(student_id) if p.category == "preference"]
    if prefs:
        parts.append("Preferences: " + "; ".join(p.rstrip(". ") for p in prefs) + ".")
    states = concept_states(student_id)
    weak = [s for s in states if s.mastery is not None and s.mastery < 0.5]
    strong = [s for s in states if s.mastery is not None and s.mastery >= 0.6]
    if weak:
        parts.append("Assessment evidence suggests gaps in: " + ", ".join(f"{s.label} ({s.mastery:.2f})" for s in weak) + ".")
    if strong:
        parts.append("Assessment evidence suggests solid footing in: " + ", ".join(s.label for s in strong) + ".")
    if not catalog.courses():
        parts.append("No courses added yet.")
    elif not any(s.mastery is not None for s in states):
        parts.append("No graded assessment evidence has been added yet, so there are no mastery estimates.")
    bs = [s.label for s in states if s.blind_spot]
    if bs:
        parts.append("Possible blind spots (self-confidence well above estimate): " + ", ".join(bs) + ".")
    for b in _global_beliefs(student_id):
        if b.key == "workload.upcoming_due" and b.value:
            parts.append(f"{catalog.course_label(b.scope.course_id)}: {int(float(b.value))} incomplete item(s) due in 7 days.")
        if b.key == "motivation.self_report" and b.status != "expired":
            parts.append(f"Short-lived self-report today: “{b.value}”.")
    return " ".join(parts)


def student_model(student_id: str) -> StudentModel:
    courses = []
    for c in catalog.courses():
        wl = store.get_belief(f"belief_{student_id}_{c['id']}_workload")
        courses.append(CourseSummary(course_id=c["id"], label=c["label"], upcoming_due=int(float(wl.value)) if wl and wl.value else 0,
                                     is_fixture=bool(c.get("is_fixture", True))))
    props = store.list_propositions(student_id)
    prop_ev = {p.id: [obs_evidence(o) for eid in p.evidence_ids if (o := store.get_observation(eid))] for p in props}
    return StudentModel(student=student_info(student_id), concepts=concept_states(student_id), courses=courses,
                        propositions=props, global_beliefs=_global_beliefs(student_id),
                        narrative=narrative(student_id), state_version=db.get_state_version(), proposition_evidence=prop_ev)


def graph(student_id: str) -> GraphResponse:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    for c in catalog.courses():
        nodes.append(GraphNode(id=f"course:{c['id']}", type="course", label=c["label"], data={"is_fixture": True}))
    for s in concept_states(student_id):
        nodes.append(GraphNode(id=f"concept:{s.concept_id}", type="concept", label=s.label, data={
            "mastery": s.mastery, "self_confidence": s.self_confidence, "evidence_count": s.correct + s.incorrect,
            "blind_spot": s.blind_spot, "course_id": s.course_id}))
        edges.append(GraphEdge(source=f"course:{s.course_id}", target=f"concept:{s.concept_id}", relation="contains", provenance="fixture"))
        for o in store.list_observations(student_id, concept_id=s.concept_id, event_type="assessment_answer"):
            if o.status != "accepted":
                continue
            ref = obs_evidence(o)
            nodes.append(GraphNode(id=f"evidence:{o.event_id}", type="evidence", label=ref.label,
                                   data={"correct": o.payload.get("correct"), "url": ref.url, "is_fixture": o.is_fixture}))
            edges.append(GraphEdge(source=f"concept:{s.concept_id}", target=f"evidence:{o.event_id}", relation="assessed_by", provenance="evidence"))
    for e in catalog.load()["edges"]:
        edges.append(GraphEdge(source=e["source"], target=e["target"], relation=e["relation"], provenance="fixture"))
    concept_ids = {c["id"] for c in catalog.concepts()}
    for p in active_propositions(student_id):
        if p.category not in ("goal", "interest"):
            continue
        nodes.append(GraphNode(id=f"goal:{p.id}", type="goal", label=p.statement,
                               data={"status": p.status, "sources": len(p.evidence_ids)}))
        linked = set(catalog.match_concepts(p.statement))
        for eid in p.evidence_ids:
            if (o := store.get_observation(eid)):
                linked.update(o.payload.get("concept_ids", []))
        for cid in sorted(linked & concept_ids):
            edges.append(GraphEdge(source=f"concept:{cid}", target=f"goal:{p.id}", relation="supports_goal", provenance="evidence"))
    return GraphResponse(nodes=nodes, edges=edges, beliefs=store.list_beliefs(student_id))


def query_terms(q: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", q.lower()) if w not in STOP and len(w) > 2]


def build_context(student_id: str, query: str = "", agent: str = "orchestrator") -> ContextResponse:
    terms = query_terms(query)
    concept_hits = set(catalog.match_concepts(query))
    for cid in catalog.courses_in_text(query):
        concept_hits |= {c["id"] for c in catalog.concepts() if c["course_id"] == cid}
    beliefs = [b for b in store.list_beliefs(student_id)
               if not concept_hits or b.scope.concept_id in concept_hits or b.scope.level != "concept"]
    records = store.list_records(student_id)
    rel_records = [r for r in records if (concept_hits & set(r.concept_ids))
                   or any(t in f"{r.title} {r.body}".lower() for t in terms)][:15]
    refs = [record_evidence(r) for r in rel_records]
    for hit in store.search_pages(student_id, terms or ["quiz"], limit=3):
        d = store.get_document(hit["doc_id"])
        if d:
            refs.append(EvidenceRef(id=f"{d.id}:p{hit['page']}", label=f"{d.title}, p. {hit['page']}", provider="documents",
                                    source_record_id=d.source_record_id, page=hit["page"], url=f"{d.file_url}#page={hit['page']}",
                                    is_fixture=d.is_fixture))
    facts = []
    for s in concept_states(student_id):
        if concept_hits and s.concept_id not in concept_hits:
            continue
        if s.mastery is not None:
            facts.append(f"{s.label}: BKT estimate {s.mastery:.2f} from {s.correct + s.incorrect} graded answer(s) "
                         f"({s.correct} correct).")
        if s.self_confidence is not None:
            facts.append(f"{s.label}: self-reported confidence {s.self_confidence:.2f} (self-report, not evidence of mastery).")
        refs += [e for e in s.evidence if e.provider == "documents"]
    uncertainties = ["BKT parameters are illustrative defaults, not calibrated to this student or course."]
    if any(r.is_fixture for r in records):
        uncertainties.append("Some source records are labeled demo data, not live connector reads.")
    return ContextResponse(narrative=narrative(student_id), facts=facts, relevant_beliefs=beliefs, source_records=rel_records,
                           evidence_refs=refs, uncertainties=uncertainties, state_version=db.get_state_version())
