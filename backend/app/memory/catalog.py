"""Course/concept catalog from fixtures/knowledge_graph.json (labeled fixture, not an official catalog)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Optional

from ..config import FIXTURES_DIR


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads((FIXTURES_DIR / "knowledge_graph.json").read_text())


def courses() -> list[dict]:
    return load()["courses"]


def concepts() -> list[dict]:
    return load()["concepts"]


def course(course_id: Optional[str]) -> Optional[dict]:
    return next((c for c in courses() if c["id"] == course_id), None)


def concept(concept_id: Optional[str]) -> Optional[dict]:
    return next((c for c in concepts() if c["id"] == concept_id), None)


def concept_label(concept_id: Optional[str]) -> str:
    c = concept(concept_id)
    return c["label"] if c else (concept_id or "unknown concept")


def course_label(course_id: Optional[str]) -> str:
    c = course(course_id)
    return c["label"] if c else (course_id or "unassigned")


def _terms(c: dict) -> list[str]:
    return [c["label"].lower(), c["id"].replace("_", " ")] + [a.lower() for a in c.get("aliases", [])]


def match_concepts(text: str, course_id: Optional[str] = None) -> list[str]:
    """Return concept ids whose label/aliases occur as whole words in text (longest alias wins first)."""
    t = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()) + " "
    hits: list[tuple[int, str]] = []
    for c in concepts():
        if course_id and c["course_id"] != course_id:
            continue
        for term in sorted(_terms(c), key=len, reverse=True):
            norm = " " + re.sub(r"[^a-z0-9]+", " ", term).strip() + " "
            if norm.strip() and norm in t:
                hits.append((len(norm), c["id"]))
                break
    hits.sort(reverse=True)
    out: list[str] = []
    for _, cid in hits:
        if cid not in out:
            out.append(cid)
    return out


def map_topic(topic: str, course_id: Optional[str] = None) -> Optional[str]:
    """Map a quiz topic line to exactly one concept; ambiguous or unknown -> None (pending review)."""
    m = match_concepts(topic, course_id)
    return m[0] if len(m) >= 1 else None


def course_for_text(text: str) -> Optional[str]:
    t = text.lower()
    for c in courses():
        if c["label"].lower().split(" (")[0] in t or c["id"].replace("_", " ") in t:
            return c["id"]
    return None


def domain_courses(domain: str) -> list[str]:
    return [c["id"] for c in courses() if c.get("domain") == domain]
