"""Deterministic intent routing + explicit-contribution extraction (no LLM required)."""
from __future__ import annotations

import hashlib
import re
from typing import Optional

from ..memory import catalog, propositions
from ..schemas import Observation
from ..timeutil import now_iso

INTENT_RULES: list[tuple[str, re.Pattern]] = [
    ("course_next", re.compile(r"\b(class(es)?|courses?)\b.*\b(take|enroll|register|next|sign up)\b|\b(take|enroll in|register for)\b.*\b(class(es)?|courses?)\b", re.I)),
    ("struggling", re.compile(r"struggl|weak|blind ?spot|bad at|gaps?\b|don'?t understand|behind on|need help with|worst", re.I)),
    ("weekly_focus", re.compile(r"\bfocus\b|this week|prioriti|study plan|plan (my|the) week|what should i (do|study|work on)|schedule", re.I)),
    ("opportunities", re.compile(r"\btalks?\b|seminar|events?\b|opportunit|colloquium|workshop|research (talk|position)|\bemails?\b", re.I)),
    ("sources", re.compile(r"\bdue\b|deadline|assignment|calendar|piazza|canvas|announcement|upcoming", re.I)),
]

CONF_HIGH = re.compile(r"\bi(?:'m| am)?\s+(?:pretty |really |very |now )?(?:confident|comfortable|good)\s+(?:with|in|at|about)\s+([^.,;!?]+)", re.I)
CONF_KNOW = re.compile(r"\bi\s+(?:really\s+)?(?:know|understand|get)\s+([^.,;!?]+?)\s+(?:well|now|fine)\b", re.I)
CONF_LOW = re.compile(r"\bi(?:'m| am)\s+(?:not confident|unsure|confused|lost|shaky)\s+(?:about|with|in|on)\s+([^.,;!?]+)", re.I)
GOAL = re.compile(r"\b(?:my goal is(?: to)?|i want to|i'd like to|i hope to|i plan to)\s+([^.;!?]+)", re.I)
INTEREST = re.compile(r"\bi(?:'m| am)\s+(?:really |very )?interested in\s+([^.;!?]+)", re.I)
PREFER = re.compile(r"\bi prefer\s+([^.;!?]+)", re.I)
MOOD = re.compile(r"\b(?:i(?:'m| am)|feeling|i feel)\s+(?:really |so |a bit |kind of )?(unmotivated|burn(?:ed|t) out|exhausted|stressed|overwhelmed|tired)\b", re.I)
QUESTIONISH = re.compile(r"\b(know|what|which|how|should)\b|\?", re.I)


def route(message: str) -> str:
    for intent, rx in INTENT_RULES:
        if rx.search(message):
            return intent
    return "general"


def _oid(student_id: str, kind: str, text: str) -> str:
    return "obs_chat_" + hashlib.sha1(f"{student_id}:{kind}:{text.lower().strip()}:{now_iso()[:16]}".encode()).hexdigest()[:10]


def extract_contributions(student_id: str, message: str) -> list[Observation]:
    """Explicit self-reports only. Never infers mastery, motivation, or traits from phrasing."""
    out: list[Observation] = []
    ts = now_iso()

    def add(event_type: str, payload: dict, concept_id: Optional[str] = None):
        c = catalog.concept(concept_id)
        out.append(Observation(event_id=_oid(student_id, f"{event_type}:{concept_id}", payload.get("statement", "")),
                               student_id=student_id, source="chat", event_type=event_type,
                               course_id=c["course_id"] if c else None, concept_id=concept_id, occurred_at=ts,
                               payload=payload, extraction_confidence=0.95, status="accepted"))

    for rx, val in ((CONF_HIGH, 0.8), (CONF_KNOW, 0.8), (CONF_LOW, 0.25)):
        for m in rx.finditer(message):
            for cid in catalog.match_concepts(m.group(1)):
                add("self_confidence", {"value": val, "statement": m.group(0).strip()}, cid)
    for kind, sentence in propositions.extract(message):  # same extractor as documents and emails
        add(kind, {"statement": sentence, "concept_ids": catalog.match_concepts(sentence)})
    if (m := MOOD.search(message)):
        add("mood", {"statement": m.group(0).strip()})
    return out
