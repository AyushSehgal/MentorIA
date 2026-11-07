"""Capability nodes. Each reads real stored evidence and returns a grounded draft + provenance."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..memory import catalog, store, updates
from ..memory.context import (build_context, concept_states, goal_concepts, profile, record_evidence,
                              active_propositions)
from ..schemas import EvidenceRef
from ..services import opportunity_ranking, planning
from ..services.aggregation import free_windows
from ..timeutil import human, now, parse
from .tools import classify_tell, extract_contributions

State = dict[str, Any]
BKT_CAVEAT = "Mastery numbers are Bayesian Knowledge Tracing estimates with illustrative, uncalibrated parameters."


def _demo_caveat(refs: list[EvidenceRef]) -> list[str]:
    """Sample-data status stays in the API (is_fixture); the UI no longer labels it (ADR-013)."""
    return []


def _dedupe(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    seen, out = set(), []
    for r in refs:
        if r.id not in seen:
            seen.add(r.id)
            out.append(r)
    return out


def memory_update(state: State) -> State:
    obs = extract_contributions(state["student_id"], state["message"])
    if not obs and state.get("mode") == "tell":
        obs = [classify_tell(state["student_id"], state["message"])]
    notes = []
    if obs:
        updates.ingest_observations(obs)
        for o in obs:
            if o.event_type == "self_confidence":
                notes.append(f"Recorded self-reported confidence {o.payload['value']:.2f} for {catalog.concept_label(o.concept_id)} "
                             "(kept separate from quiz-based mastery).")
            elif o.event_type in ("goal", "interest", "preference"):
                prop = next((p for p in store.list_propositions(state["student_id"]) if o.event_id in p.evidence_ids), None)
                if prop and len(prop.evidence_ids) > 1:
                    notes.append(f"This matches a {o.event_type} you already stated elsewhere — “{prop.statement}” is now backed by "
                                 f"{len(prop.evidence_ids)} sources.")
                else:
                    notes.append(f"Saved {o.event_type}: “{o.payload['statement']}” (self-reported; you can correct it on the Student Model page).")
            elif o.event_type == "note":
                notes.append(f"Saved a note about you: “{o.payload['statement']}”.")
            elif o.event_type == "mood":
                notes.append("Noted how you're feeling today as a short-lived self-report (expires in 24h; not a permanent trait).")
    return {"memory_updates": notes, "trace": state["trace"] + ["memory_update"]}


def struggling(state: State) -> State:
    sid, msg = state["student_id"], state["message"].lower()
    course_ids = catalog.courses_in_text(state["message"]) or [c["id"] for c in catalog.courses()]
    if not course_ids:
        return {"draft": "I don't know about any of your courses yet. Add a course overview and some graded work on the "
                         "Add data page, and I'll tell you where the evidence points.",
                "sources": [], "beliefs_used": [], "uncertainties": ["No courses or graded evidence added yet."],
                "trace": state["trace"] + ["struggling"]}
    states = [s for s in concept_states(sid) if s.course_id in course_ids or set(s.also_in) & set(course_ids)]
    graded = [s for s in states if s.mastery is not None]
    scope = " / ".join(catalog.course_label(c) for c in course_ids)
    refs: list[EvidenceRef] = []
    lines: list[str] = []
    if not graded:
        lines.append(f"I don't have any graded assessment evidence for {scope} yet, so I can't say which topics you're struggling with.")
        conf = [s for s in states if s.self_confidence is not None]
        if conf:
            lines.append("What I do have are your own confidence ratings (self-report, not evidence of mastery):")
            lines += [f"- {s.label}: self-rated {s.self_confidence:.2f}" for s in conf]
        lines.append("Upload a graded quiz or exam on the Documents page and I'll map each graded answer to a concept.")
        return {"draft": "\n".join(lines), "sources": [], "beliefs_used": [],
                "uncertainties": ["No graded evidence available."], "trace": state["trace"] + ["struggling"]}
    weak = sorted([s for s in graded if s.mastery < 0.5], key=lambda s: s.mastery)
    ok = [s for s in graded if s.mastery >= 0.5]
    none = [s for s in states if s.mastery is None]
    if weak:
        lines.append(f"Based on graded assessment evidence in {scope}, these topics look like the clearest gaps:")
        for s in weak:
            wrong = [o for o in store.list_observations(sid, s.concept_id, "assessment_answer")
                     if o.status == "accepted" and o.payload.get("correct") is False]
            cites = "; ".join(f"{o.payload.get('document_title', 'quiz')} p. {o.payload.get('page')} {o.payload.get('question_id')}" for o in wrong)
            line = (f"- **{s.label}** — estimate {s.mastery:.2f}; {s.incorrect} of {s.correct + s.incorrect} graded answers incorrect"
                    + (f" ({cites})" if cites else "") + ".")
            if s.blind_spot:
                line += f" You rated your confidence {s.self_confidence:.2f}, well above the estimate — a possible blind spot worth checking, not a diagnosis."
            lines.append(line)
            refs += [e for e in s.evidence if e.provider == "documents"]
    else:
        lines.append(f"None of the graded evidence in {scope} points to a clear gap right now.")
    if ok:
        lines.append("Looking solid on the same evidence: " + ", ".join(f"{s.label} ({s.mastery:.2f})" for s in ok) + ".")
        refs += [e for s in ok for e in s.evidence if e.provider == "documents"]
    if none:
        shown = ", ".join(s.label for s in none[:5]) + (f", and {len(none) - 5} more" if len(none) > 5 else "")
        lines.append(f"Not enough graded evidence to evaluate: {shown}.")
    pending = [o for o in store.list_observations(sid, event_type="assessment_answer") if o.status == "pending_review"]
    unc = [BKT_CAVEAT]
    if pending:
        lines.append(f"{len(pending)} extracted answer(s) need review before they count (e.g. partial credit), so they don't affect these estimates.")
    oldest = min((parse(s.last_evidence_at) for s in graded if s.last_evidence_at), default=None)
    if oldest:
        days = (now() - oldest).days
        unc.append(f"Evidence comes from assessments dated up to {days} day(s) ago; your understanding may have changed since.")
    if any(s.correct + s.incorrect < 3 for s in weak):
        unc.append("Several estimates rest on only 1–2 graded answers.")
    unc.append("Questions you ask (chat/Piazza) are not treated as evidence of weakness.")
    refs = _dedupe(refs)
    used = [f"belief_{sid}_{s.concept_id}_mastery" for s in graded]
    return {"draft": "\n".join(lines), "sources": refs, "beliefs_used": used, "uncertainties": unc + _demo_caveat(refs),
            "trace": state["trace"] + ["retrieve_context", "struggling"]}


def weekly_focus(state: State) -> State:
    sid = state["student_id"]
    prios = planning.priorities(sid, limit=4)
    recs = planning.propose_study_sessions(sid, prios)
    refs: list[EvidenceRef] = []
    lines = []
    if not prios:
        lines.append("I don't have graded evidence or upcoming deadlines to build a grounded plan yet. Sync your sources or upload a graded quiz.")
    else:
        lines.append("Here's how I'd prioritize this week, combining graded evidence, deadlines, your goals, and free calendar time:")
        for i, p in enumerate(prios, 1):
            s = p.concept
            f = {x.name: x for x in p.factors}
            bits = [f["concept_gap"].explanation if s.mastery is not None else "no graded evidence yet"]
            if p.deadline:
                bits.append(f"{p.deadline.title} due {human(parse(p.deadline.occurred_at))}")
            if f["goal_relevance"].value == 1.0:
                bits.append("linked to your stated goal")
            if s.blind_spot:
                bits.append("possible blind spot (confidence ≫ estimate)")
            lines.append(f"{i}. **{s.label}** (priority {p.score:.2f}) — " + "; ".join(bits) + ".")
            refs += p.evidence
    listed = {p.concept.concept_id for p in prios}
    goal_ids = goal_concepts(sid)
    soon = sorted([a for a in store.list_records(sid, kind="assignment") if not a.metadata.get("completed")
                   and (d := parse(a.occurred_at)) and now() <= d <= now() + timedelta(days=14)], key=lambda a: a.occurred_at)
    for a in soon:
        linked = [c for c in a.concept_ids if c in goal_ids and c not in listed]
        if linked:
            st = next((x for x in concept_states(sid) if x.concept_id == linked[0]), None)
            note = (f"Current estimate {st.mastery:.2f}." if st and st.mastery is not None
                    else "There's no graded evidence on it yet, so plan an early start.")
            lines.append(f"Linked to your goal: **{catalog.concept_label(linked[0])}** — “{a.title}” is due "
                         f"{human(parse(a.occurred_at))}. {note}")
            refs.append(record_evidence(a))
            break
    windows = free_windows(sid)
    if windows:
        total = sum(w.minutes for w in windows) // 60
        lines.append(f"Your calendar shows about {total} free hours across {len(windows)} windows (9am–9pm) over the next 7 days.")
    if recs:
        lines.append("I've drafted study block(s) below. Nothing is added to your calendar unless you approve it.")
    opps = [o for o in opportunity_ranking.propose_event_recommendations(sid, opportunity_ranking.rank(sid))
            if o.event_start and o.relevance_score >= 0.5 and parse(o.event_start) <= now() + timedelta(days=7) and parse(o.event_start) > now()]
    if opps:
        o = opps[0]
        lines.append(f"Also relevant to your goals: **{o.record.title}** — {o.timing_label}.")
        refs.append(record_evidence(o.record))
        if o.recommendation_id and (r := store.get_recommendation(o.recommendation_id)) and r.status == "pending":
            recs.append(r)
    refs = _dedupe(refs)
    unc = [BKT_CAVEAT, "Priority weights are transparent heuristics (gap × urgency × goal relevance × feasible time), not a trained model."]
    return {"draft": "\n".join(lines), "sources": refs, "recs": recs,
            "beliefs_used": [f"belief_{sid}_{p.concept.concept_id}_mastery" for p in prios if p.concept.mastery is not None],
            "uncertainties": unc + _demo_caveat(refs), "trace": state["trace"] + ["retrieve_context", "plan_week"]}


def course_next(state: State) -> State:
    sid = state["student_id"]
    prof = profile()
    goals = sorted([p for p in active_propositions(sid) if p.category == "goal"], key=lambda p: -len(p.evidence_ids))
    gc = goal_concepts(sid)
    lines = ["I don't have a verified course catalog or official prerequisite data, so I won't name specific courses or claim prerequisites."]
    if goals:
        lines.append("Your stated goals: " + "; ".join(
            f"“{g.statement}”" + (f" (in {len(g.evidence_ids)} sources)" if len(g.evidence_ids) > 1 else "") for g in goals) + ".")
    if prof.get("completed_courses"):
        lines.append("Completed courses on record: " + ", ".join(c["label"] for c in prof["completed_courses"]) + ".")
    current = [c["label"] for c in catalog.courses()]
    if current:
        lines.append("Courses I know you're taking: " + ", ".join(current) + ".")
    if gc:
        lines.append("Subject areas that line up with those goals (from your course overviews, not a catalog): "
                     + ", ".join(catalog.concept_label(c) for c in sorted(gc)) + ".")
    weak = [s for s in concept_states(sid) if s.mastery is not None and s.mastery < 0.5]
    if weak:
        lines.append("Before taking more advanced courses that build on them, consider shoring up: "
                     + ", ".join(s.label for s in weak) + " (based on graded evidence).")
    hits = [h for h in store.search_pages(sid, ["course catalog", "degree audit", "degree requirements"], limit=3)]
    refs = []
    if hits:
        for h in hits:
            d = store.get_document(h["doc_id"])
            if d:
                refs.append(EvidenceRef(id=f"{d.id}:p{h['page']}", label=f"{d.title}, p. {h['page']}", provider="documents",
                                        source_record_id=d.source_record_id, page=h["page"], url=f"{d.file_url}#page={h['page']}",
                                        is_fixture=d.is_fixture))
        lines.append("An uploaded document mentions prerequisites/catalog info; see the cited page(s) — I haven't verified it as an official catalog.")
    else:
        lines.append("To get specific recommendations, upload your department's course catalog or degree audit (PDF) and I'll match it against your goals and evidence.")
    return {"draft": "\n".join(lines), "sources": refs, "beliefs_used": [],
            "uncertainties": ["No verified course catalog or prerequisite data available.",
                              "I have no record of your completed courses."],
            "trace": state["trace"] + ["retrieve_context", "course_next"]}


def opportunities(state: State) -> State:
    sid = state["student_id"]
    opps = opportunity_ranking.propose_event_recommendations(sid, opportunity_ranking.rank(sid))
    lines, refs, recs = [], [], []
    rel = [o for o in opps if o.relevance_score >= 0.3]
    if not opps:
        lines.append("I haven't found any academic announcements in your synced Gmail.")
    elif not rel:
        lines.append("None of the synced announcements match your stated goals.")
    else:
        lines.append("Announcements from Gmail ranked against your goals:")
        for o in rel:
            who = f" Speaker: {o.speaker}." if o.speaker else ""
            where = f" Where: {o.venue}." if o.venue else ""
            lines.append(f"- **{o.record.title}** — {o.timing_label}.{who}{where} Why: {o.relevance_reasons[0]}.")
            refs.append(record_evidence(o.record))
            if o.recommendation_id and (r := store.get_recommendation(o.recommendation_id)) and r.status == "pending":
                recs.append(r)
        if recs:
            lines.append("I can add dated events to your calendar if you approve below.")
    low = [o for o in opps if o.relevance_score < 0.3]
    if low:
        lines.append(f"Skipped {len(low)} announcement(s) with no overlap with your goals (e.g. {low[0].record.title}).")
    unc = ["Relevance is a keyword/concept-overlap heuristic.", "Event times are shown only when the email states them explicitly."]
    return {"draft": "\n".join(lines), "sources": refs, "recs": recs, "beliefs_used": [],
            "uncertainties": unc + _demo_caveat(refs), "trace": state["trace"] + ["rank_opportunities"]}


def sources(state: State) -> State:
    sid = state["student_id"]
    horizon = now() + timedelta(days=7)
    due = sorted([a for a in store.list_records(sid, kind="assignment") if not a.metadata.get("completed")
                  and (d := parse(a.occurred_at)) and now() <= d <= horizon], key=lambda a: a.occurred_at)
    lines = []
    if due:
        lines.append("Due in the next 7 days (Canvas):")
        lines += [f"- **{a.title}** ({catalog.course_label(a.course_id)}) — due {human(parse(a.occurred_at))}" for a in due]
    else:
        lines.append("Nothing incomplete is due in the next 7 days in your synced Canvas data.")
    ann = [p for p in store.list_records(sid, provider="piazza") if p.metadata.get("is_instructor")]
    if ann:
        lines.append("Recent instructor posts (Piazza):")
        lines += [f"- {p.title}" for p in sorted(ann, key=lambda p: p.occurred_at or "", reverse=True)[:3]]
    events = [e for e in store.list_records(sid, kind="calendar_event") if (d := parse(e.occurred_at)) and now() <= d <= horizon]
    lines.append(f"Your calendar has {len(events)} event(s) in the next 7 days.")
    refs = [record_evidence(r) for r in due + ann[:3]]
    return {"draft": "\n".join(lines), "sources": refs, "beliefs_used": [f"belief_{sid}_{c['id']}_workload" for c in catalog.courses()],
            "uncertainties": _demo_caveat(refs), "trace": state["trace"] + ["query_sources"]}


def general(state: State) -> State:
    sid = state["student_id"]
    ctx = build_context(sid, state["message"])
    lines = []
    mood = any("short-lived" in n for n in state.get("memory_updates", []))
    if state.get("memory_updates"):
        lines.append("Got it — I've updated your student model.")
    if mood:
        lines.append("Rough days happen. If it helps, ask “What should I focus on this week?” and approve just one short block — "
                     "or skip planning today. I won't treat this as a lasting trait.")
        return {"draft": "\n".join(lines), "sources": [], "beliefs_used": [f"belief_{sid}_motivation_selfreport"],
                "uncertainties": [], "trace": state["trace"] + ["general"]}
    if any(("goal" in n or "interest" in n) for n in state.get("memory_updates", [])):
        gc = sorted(goal_concepts(sid))
        if gc:
            lines.append("Concepts in your courses that connect to your goals: " + ", ".join(catalog.concept_label(c) for c in gc) + ".")
        opps = [o for o in opportunity_ranking.rank(sid) if o.relevance_score >= 0.5]
        if opps:
            lines.append("Opportunities in your inbox that fit:")
            lines += [f"- **{o.record.title}** — {o.timing_label}" for o in opps[:3]]
        lines.append("Ask “What should I focus on this week?” to see how this changes your priorities.")
        refs = [record_evidence(o.record) for o in opps[:3]]
        return {"draft": "\n".join(lines), "sources": refs, "beliefs_used": [], "uncertainties": [
                    "Goals are what you told me; I don't infer them from your activity."],
                "trace": state["trace"] + ["retrieve_context", "general"]}
    if ctx.facts:
        lines.append("Here's what I know that's relevant:")
        lines += [f"- {f}" for f in ctx.facts[:6]]
    elif ctx.source_records:
        lines.append("Related items from your sources:")
        lines += [f"- {r.title} ({r.provider.replace('_', ' ')})" for r in ctx.source_records[:6]]
    if not lines:
        lines.append(ctx.narrative or "I don't have much stored about you yet.")
    lines.append("You can ask me: “What systems topics am I struggling with?”, “What should I focus on this week?”, "
                 "“What classes should I take next?”, or “Any research talks I should attend?”")
    refs = ctx.evidence_refs[:8]
    return {"draft": "\n".join(lines), "sources": refs, "beliefs_used": [b.id for b in ctx.relevant_beliefs][:10],
            "uncertainties": ctx.uncertainties, "trace": state["trace"] + ["retrieve_context", "general"]}


def tell(state: State) -> State:
    """'About me' replies: confirm what was saved and what it connects to. Never invents facts about the student."""
    sid, notes = state["student_id"], state.get("memory_updates", [])
    lines, refs = [], []
    if not notes:
        lines.append("I couldn't find anything to save in that. Try starting with “My goal is…”, “I'm interested in…” or “I prefer…”.")
    if any(("goal" in n or "interest" in n) for n in notes):
        gc = sorted(goal_concepts(sid))
        if gc:
            lines.append("Connects to: " + ", ".join(catalog.concept_label(c) for c in gc) + ".")
        opps = [o for o in opportunity_ranking.rank(sid) if o.relevance_score >= 0.5]
        if opps:
            lines.append("Fits these opportunities:")
            lines += [f"- **{o.record.title}** — {o.timing_label}" for o in opps[:3]]
            refs = [record_evidence(o.record) for o in opps[:3]]
    if any("confidence" in n for n in notes):
        lines.append("Kept separate from your quiz-based mastery estimates.")
        flagged = [s.label for s in concept_states(sid) if s.blind_spot]
        if flagged:
            lines.append("Possible blind spot (confidence well above graded evidence): " + ", ".join(flagged) + ".")
    if any("short-lived" in n for n in notes):
        lines.append("Thanks for telling me. This expires in 24 hours and isn't treated as a lasting trait.")
    if not lines:
        lines.append("Saved. You can review or correct it on the Student Model page.")
    return {"draft": "\n".join(lines), "sources": refs, "beliefs_used": [], "uncertainties": [],
            "trace": state["trace"] + ["tell"]}
