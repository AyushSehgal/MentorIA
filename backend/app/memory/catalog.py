"""Course/concept catalog, stored in SQLite and grown by imports (course overview PDFs or source packs).

MentorIA starts with an empty catalog. Relations come from imported documents and are labeled with their provenance;
they are never invented by an LLM.
"""
from __future__ import annotations

import re
import threading
from typing import Optional

from .. import db

_lock = threading.Lock()
_cache: dict = {"version": None, "data": None}


def _version() -> str:
    rows = db.query("SELECT value FROM meta WHERE key='catalog_version'")
    return rows[0]["value"] if rows else "0"


def _bump() -> None:
    db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('catalog_version', ?)", (str(int(_version()) + 1),))


def load() -> dict:
    v = _version() + ":" + str(db.get_state_version()) + ":" + str(id(db.conn()))
    with _lock:
        if _cache["version"] != v:
            _cache["data"] = {
                "courses": [db.loads(r["data"]) for r in db.query("SELECT data FROM courses ORDER BY id")],
                "concepts": [db.loads(r["data"]) for r in db.query("SELECT data FROM concepts ORDER BY rowid")],
                "edges": [db.loads(r["data"]) for r in db.query("SELECT data FROM concept_edges ORDER BY rowid")],
            }
            _cache["version"] = v
        return _cache["data"]


def invalidate() -> None:
    with _lock:
        _cache["version"] = None


# ---- writes -------------------------------------------------------------------
def upsert_course(course: dict) -> bool:
    """course: {id, label, code?, domain?, source?, is_fixture?}. Returns True if new."""
    new = not db.query("SELECT 1 FROM courses WHERE id=?", (course["id"],))
    db.execute("INSERT OR REPLACE INTO courses(id, data) VALUES(?, ?)", (course["id"], db.dumps(course)))
    _bump()
    invalidate()
    return new


def upsert_concept(concept: dict) -> bool:
    """concept: {id, course_id, label, aliases[]}. Returns True if new."""
    new = not db.query("SELECT 1 FROM concepts WHERE id=?", (concept["id"],))
    if new:
        db.execute("INSERT INTO concepts(id, course_id, data) VALUES(?,?,?)", (concept["id"], concept["course_id"], db.dumps(concept)))
    else:
        db.execute("UPDATE concepts SET course_id=?, data=? WHERE id=?", (concept["course_id"], db.dumps(concept), concept["id"]))
    _bump()
    invalidate()
    return new


def upsert_edge(edge: dict) -> bool:
    """edge: {source: 'concept:x', target: 'concept:y', relation, provenance}."""
    new = not db.query("SELECT 1 FROM concept_edges WHERE source=? AND target=? AND relation=?",
                       (edge["source"], edge["target"], edge["relation"]))
    db.execute("INSERT OR REPLACE INTO concept_edges(source, target, relation, data) VALUES(?,?,?,?)",
               (edge["source"], edge["target"], edge["relation"], db.dumps(edge)))
    _bump()
    invalidate()
    return new


# ---- reads --------------------------------------------------------------------
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


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def _terms(c: dict) -> list[str]:
    return [c["label"].lower(), c["id"].replace("_", " ")] + [a.lower() for a in c.get("aliases", [])]


def match_concepts(text: str, course_id: Optional[str] = None) -> list[str]:
    """Concept ids whose label/aliases occur as whole words in text (longest match first)."""
    t = _norm(text)
    hits: list[tuple[int, str]] = []
    for c in concepts():
        if course_id and c["course_id"] != course_id:
            continue
        for term in sorted(_terms(c), key=len, reverse=True):
            norm = _norm(term)
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
    m = match_concepts(topic, course_id) or (match_concepts(topic) if course_id else [])
    return m[0] if m else None


def _course_terms(c: dict) -> list[str]:
    terms = [c["label"].split(" (")[0], c["id"].replace("_", " ")]
    if c.get("code"):
        terms += [c["code"], c["code"].replace("-", "")]
    return [t for t in terms if t] + list(c.get("aliases", []))


def courses_in_text(text: str) -> list[str]:
    t = _norm(text)
    found = []
    for c in courses():
        if any(_norm(term) in t for term in _course_terms(c) if term.strip()):
            found.append(c["id"])
    return found


def course_for_text(text: str) -> Optional[str]:
    found = courses_in_text(text)
    return found[0] if found else None


def domain_courses(domain: str) -> list[str]:
    return [c["id"] for c in courses() if c.get("domain") == domain]
