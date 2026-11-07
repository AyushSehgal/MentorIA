"""Gmail announcement extraction + interest-match ranking.

Never invents a time: event_start is set only when an explicit date AND time are found in the text.
Message text is untrusted; it is only pattern-matched, never executed or obeyed.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import settings
from ..memory import catalog, store
from ..memory.context import active_propositions, concept_states, goal_concepts, record_evidence
from ..schemas import Factor, Opportunity, ProposedAction, Recommendation, SourceRecord
from ..timeutil import human, iso, now, now_iso, parse

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
TZ_ABBR = {"est": "America/New_York", "edt": "America/New_York", "et": "America/New_York",
           "cst": "America/Chicago", "cdt": "America/Chicago", "ct": "America/Chicago",
           "mst": "America/Denver", "mdt": "America/Denver", "pst": "America/Los_Angeles",
           "pdt": "America/Los_Angeles", "pt": "America/Los_Angeles", "utc": "UTC", "gmt": "UTC"}
DATE_RE = re.compile(
    r"(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s+)?"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?"
    r"(?:,?\s*(\d{4}))?"
    r"(?:\s*(?:at|@|,|from)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.))?"
    r"(?:\s*([ecmp][sd]?t|utc|gmt)\b)?", re.I)
SPEAKER_RE = re.compile(r"^\s*speaker\s*:\s*(.+)$", re.I | re.M)
VENUE_RE = re.compile(r"^\s*(?:where|location|venue|room)\s*:\s*(.+)$", re.I | re.M)
URL_RE = re.compile(r"https?://[^\s>)\]]+")
EVENTISH = re.compile(r"\b(seminar|talk|colloquium|lecture|workshop|reading group|symposium|speaker|fair)\b", re.I)


def extract_when(text: str, sent: Optional[datetime]) -> tuple[Optional[datetime], Optional[str]]:
    """Returns (event_start, date_only_label). event_start requires explicit date+time."""
    for m in DATE_RE.finditer(text):
        mon, day, year, hh, mm, ap, tz = m.groups()
        ref = sent or now()
        try:
            y = int(year) if year else ref.year
            base = datetime(y, MONTHS[mon[:3].lower()], int(day))
        except ValueError:
            continue
        if not year and base.date() < (ref - timedelta(days=60)).date():
            base = base.replace(year=y + 1)
        if not hh:
            return None, base.strftime("%b %-d, %Y")
        h = int(hh) % 12 + (12 if ap.lower().startswith("p") else 0)
        zone = ZoneInfo(TZ_ABBR.get((tz or "").lower(), settings.timezone))
        return base.replace(hour=h, minute=int(mm or 0), tzinfo=zone), None
    return None, None


def _interest_words(student_id: str) -> set[str]:
    words = set()
    for p in active_propositions(student_id):
        if p.category in ("goal", "interest"):
            words |= {w for w in re.findall(r"[a-z]+", p.statement.lower()) if len(w) > 4}
    return words - {"would", "ideally", "research", "think", "about", "really"}


def rank(student_id: str) -> list[Opportunity]:
    goals = goal_concepts(student_id)
    words = _interest_words(student_id)
    weak = {s.concept_id for s in concept_states(student_id) if s.mastery is not None and s.mastery < 0.5}
    out = []
    for r in store.list_records(student_id, provider="gmail"):
        text = f"{r.title}\n{r.body}"
        concepts = set(r.concept_ids) | set(catalog.match_concepts(text))
        score, reasons = 0.05, []
        g = concepts & goals
        if g:
            score += 0.55
            reasons.append("Matches your stated goal/interest: " + ", ".join(catalog.concept_label(c) for c in sorted(g)))
        kw = sorted(w for w in words if w in text.lower())
        if kw:
            score += min(0.2, 0.07 * len(kw))
            reasons.append("Shares keywords with your goals: " + ", ".join(kw[:4]))
        wk = concepts & weak
        if wk:
            score += 0.25
            reasons.append("Covers a concept where assessment evidence shows a gap: " + ", ".join(catalog.concept_label(c) for c in sorted(wk)))
        if not reasons:
            reasons.append("No overlap with your stated goals or current coursework found")
        sent = parse(r.occurred_at)
        start, date_only = extract_when(text, sent)
        if start and start < now() - timedelta(hours=2):
            timing = f"Already happened ({human(start)})"
        elif start:
            timing = human(start)
        elif date_only:
            timing = f"Date mentioned ({date_only}) but no time found — worth reviewing"
        else:
            timing = "Worth reviewing — no event date found"
        sp = SPEAKER_RE.search(r.body)
        vn = VENUE_RE.search(r.body)
        url = URL_RE.search(r.body)
        out.append(Opportunity(record=r, relevance_score=round(min(score, 1.0), 2), relevance_reasons=reasons,
                               event_start=iso(start) if start else None, timing_label=timing,
                               speaker=sp.group(1).strip() if sp else None, venue=vn.group(1).strip() if vn else None,
                               url=url.group(0) if url else None))
    out.sort(key=lambda o: -o.relevance_score)
    return out


def propose_event_recommendations(student_id: str, opps: list[Opportunity]) -> list[Opportunity]:
    """Relevant, dated, future, event-like announcements → approval-gated calendar proposal."""
    for o in opps:
        if not (o.event_start and o.relevance_score >= 0.5 and EVENTISH.search(o.record.title + " " + o.record.body)):
            continue
        start = parse(o.event_start)
        if start < now():
            continue
        rid = f"rec_evt_{o.record.id}"
        existing = store.get_recommendation(rid)
        if existing and existing.status != "pending":
            o.recommendation_id = rid
            continue
        rec = Recommendation(
            id=rid, student_id=student_id, type="attend_event", title=f"Attend: {o.record.title}"[:120],
            reason=" · ".join(o.relevance_reasons), evidence_ids=[o.record.id], evidence=[record_evidence(o.record)],
            factors=[Factor(name="interest_match", value=o.relevance_score, explanation="Heuristic overlap with stated goals, keywords and weak concepts")],
            suggested_start=o.event_start, duration_minutes=60, status="pending",
            proposed_action=ProposedAction(provider="google_calendar", operation="create_event", args={
                "title": f"Attend: {o.record.title}"[:120], "start": o.event_start, "duration_minutes": 60,
                "location": o.venue or "", "source_record_id": o.record.id}),
            created_at=existing.created_at if existing else now_iso(), is_fixture=o.record.is_fixture)
        store.put_recommendation(rec)
        o.recommendation_id = rid
    return opps
