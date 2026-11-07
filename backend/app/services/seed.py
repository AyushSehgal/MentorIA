"""Seed / reset the deterministic demo scenario (no quiz ingested; the demo uploads it live)."""
from __future__ import annotations

from .. import db
from ..memory import updates
from ..memory.context import profile
from ..schemas import Observation
from ..timeutil import iso, resolve_rel
from .aggregation import sync_all


def seed(student_id: str = "demo_student") -> None:
    p = profile()
    obs = []
    for raw in p["seed_observations"]:
        obs.append(Observation(event_id=raw["event_id"], student_id=student_id, source=raw["source"],
                               event_type=raw["event_type"], course_id=raw.get("course_id"), concept_id=raw.get("concept_id"),
                               occurred_at=iso(resolve_rel(raw["occurred_at_rel"])), payload=raw["payload"],
                               extraction_confidence=1.0, status="accepted", is_fixture=True))
    updates.ingest_observations(obs)
    sync_all(student_id)


def reset(student_id: str = "demo_student") -> None:
    db.reset_all()
    seed(student_id)


def ensure_seeded(student_id: str = "demo_student") -> None:
    if not db.query("SELECT 1 FROM observations LIMIT 1") and not db.query("SELECT 1 FROM source_records LIMIT 1"):
        seed(student_id)
