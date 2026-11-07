"""'Suggested for you' in Quick Recap: at most one per kind, each grounded in a real record.

  event     pending attend-event recommendation from a Gmail announcement      (approve/reject)
  reading   paper from a course reading list matching your goals or gaps         (open / dismiss)
  resource  link a classmate shared on Piazza matching your goals or gaps        (open / dismiss)
  study     pending study block from the weekly plan                             (approve/reject)
"""
from __future__ import annotations

import re

from .. import db
from ..memory import catalog, propositions, store
from ..memory.context import active_propositions, concept_states, goal_concepts
from ..schemas import Suggestion


def _dismissed(student_id: str) -> set[str]:
    rows = db.query("SELECT key FROM meta WHERE key LIKE ?", (f"dismissed:{student_id}:%",))
    return {r["key"].split(":", 2)[2] for r in rows}


def dismiss(student_id: str, suggestion_id: str) -> None:
    db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, '1')", (f"dismissed:{student_id}:{suggestion_id}",))


def _goal_words(student_id: str) -> dict[str, float]:
    """Meaningful tokens (stopwords removed, light stemming) from goals/interests. The main goal — the one stated in the
    most places — counts most, so a paper about *language* beats one that merely shares a common word."""
    props = [p for p in active_propositions(student_id) if p.category in ("goal", "interest")]
    main = max((p for p in props if p.category == "goal"), key=lambda p: len(p.evidence_ids), default=None)
    weights: dict[str, float] = {}
    for p in props:
        w = 0.5 if p is main else 0.1
        for tok in propositions._tokens(p.statement):
            weights[tok] = max(weights.get(tok, 0.0), w)
    return weights


def _score(rec, goals: set[str], weak: set[str], words: dict[str, float]) -> tuple[float, str]:
    g = set(rec.concept_ids) & goals
    w = set(rec.concept_ids) & weak
    toks = propositions._tokens(f"{rec.title} {rec.body}")
    score = 2.0 * bool(g) + 1.0 * bool(w) + sum(wt for tok, wt in words.items() if tok in toks)
    if g:
        why = "Matches your goal: " + ", ".join(catalog.concept_label(c) for c in sorted(g))
    elif w:
        why = "Covers a topic where your graded work shows a gap: " + ", ".join(catalog.concept_label(c) for c in sorted(w))
    else:
        why = ""
    return score, why


def build(student_id: str) -> list[Suggestion]:
    hidden = _dismissed(student_id)
    goals = goal_concepts(student_id)
    weak = {s.concept_id for s in concept_states(student_id) if s.mastery is not None and s.mastery < 0.5}
    words = _goal_words(student_id)
    out: list[Suggestion] = []
    pending = store.list_recommendations(student_id, status="pending")

    ev = next((r for r in pending if r.type == "attend_event"), None)
    if ev:
        out.append(Suggestion(id=f"sug_{ev.id}", kind="event", source_label="From your Gmail",
                              title=ev.title.removeprefix("Attend: "), why=ev.reason.split(" · ")[0],
                              when=ev.suggested_start, recommendation=ev))

    for kind, records, label_fn in (
        ("reading", [r for r in store.list_records(student_id, provider="documents") if r.kind == "reading"],
         lambda r: f"From the {r.metadata.get('course_code') or catalog.course_label(r.course_id)} reading list"),
        ("resource", [r for r in store.list_records(student_id, provider="piazza")
                      if r.source_url and not r.metadata.get("is_instructor")],
         lambda r: "A classmate shared this on Piazza"),
    ):
        best = None
        for r in records:
            sid = f"sug_{r.id}"
            if sid in hidden:
                continue
            score, why = _score(r, goals, weak, words)
            if score >= 1 and (best is None or score > best[0]):
                best = (score, why, r)
        if best:
            _, why, r = best
            out.append(Suggestion(id=f"sug_{r.id}", kind=kind, source_label=label_fn(r), title=r.title, why=why,
                                  url=r.source_url))

    study = [r for r in pending if r.type == "study_session"]
    for r in study[: max(0, 4 - len(out))]:
        out.append(Suggestion(id=f"sug_{r.id}", kind="study", source_label="From your weekly plan",
                              title=r.title.removeprefix("Study: "), why=r.reason.split(";")[0],
                              when=r.suggested_start, recommendation=r))
    return out[:4]
