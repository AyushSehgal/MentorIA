"""Typed accessors over SQLite for every memory-layer entity."""
from __future__ import annotations

from typing import Optional

from .. import db
from ..schemas import (Belief, BeliefUpdate, ConnectorStatus, DocumentSummary, Observation, Recommendation,
                       SemanticProposition, SourceRecord)


# ---- source records ---------------------------------------------------------
def _completion_key(student_id: str, provider: str, external_id: str) -> str:
    return f"done:{student_id}:{provider}:{external_id}"


def _apply_completion(r: SourceRecord) -> None:
    """A student's own 'complete' toggle wins over whatever a sync or re-import says."""
    rows = db.query("SELECT value FROM meta WHERE key=?", (_completion_key(r.student_id, r.provider, r.external_id),))
    if rows:
        r.metadata = dict(r.metadata) | {"completed": rows[0]["value"] == "1", "completed_by_student": rows[0]["value"] == "1"}


def set_completion(record_id: str, student_id: str, completed: bool) -> Optional[SourceRecord]:
    r = get_record(record_id)
    if r is None or r.student_id != student_id:
        return None
    db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
               (_completion_key(student_id, r.provider, r.external_id), "1" if completed else "0"))
    _apply_completion(r)
    db.execute("UPDATE source_records SET data=? WHERE id=?", (db.dumps(r.model_dump()), r.id))
    db.bump_state_version()
    return r


def upsert_record(r: SourceRecord) -> bool:
    """Dedup by (student, provider, external_id). Returns True if newly added."""
    _apply_completion(r)
    existing = db.query("SELECT id FROM source_records WHERE student_id=? AND provider=? AND external_id=?",
                        (r.student_id, r.provider, r.external_id))
    if existing:
        r.id = existing[0]["id"]
        db.execute("UPDATE source_records SET kind=?, data=? WHERE id=?", (r.kind, db.dumps(r.model_dump()), r.id))
        return False
    db.execute("INSERT INTO source_records(id, student_id, provider, external_id, kind, data) VALUES(?,?,?,?,?,?)",
               (r.id, r.student_id, r.provider, r.external_id, r.kind, db.dumps(r.model_dump())))
    return True


def delete_records(student_id: str, provider: str, keep_external_ids: Optional[set[str]] = None,
                   only_fixture: Optional[bool] = None) -> None:
    for rec in list_records(student_id, provider=provider):
        if keep_external_ids is not None and rec.external_id in keep_external_ids:
            continue
        if only_fixture is not None and rec.is_fixture != only_fixture:
            continue
        db.execute("DELETE FROM source_records WHERE id=?", (rec.id,))


def list_records(student_id: str, provider: Optional[str] = None, kind: Optional[str] = None) -> list[SourceRecord]:
    sql, params = "SELECT data FROM source_records WHERE student_id=?", [student_id]
    if provider:
        sql += " AND provider=?"
        params.append(provider)
    if kind:
        sql += " AND kind=?"
        params.append(kind)
    return [SourceRecord(**db.loads(r["data"])) for r in db.query(sql, params)]


def get_record(record_id: str) -> Optional[SourceRecord]:
    rows = db.query("SELECT data FROM source_records WHERE id=?", (record_id,))
    return SourceRecord(**db.loads(rows[0]["data"])) if rows else None


# ---- observations (immutable) -------------------------------------------------
def insert_observation(o: Observation) -> bool:
    """Immutable + idempotent: returns False if event_id already exists (never overwritten)."""
    if db.query("SELECT 1 FROM observations WHERE event_id=?", (o.event_id,)):
        return False
    db.execute("INSERT INTO observations(event_id, student_id, concept_id, event_type, occurred_at, data) VALUES(?,?,?,?,?,?)",
               (o.event_id, o.student_id, o.concept_id, o.event_type, o.occurred_at, db.dumps(o.model_dump())))
    return True


def list_observations(student_id: str, concept_id: Optional[str] = None, event_type: Optional[str] = None) -> list[Observation]:
    sql, params = "SELECT data FROM observations WHERE student_id=?", [student_id]
    if concept_id:
        sql += " AND concept_id=?"
        params.append(concept_id)
    if event_type:
        sql += " AND event_type=?"
        params.append(event_type)
    sql += " ORDER BY occurred_at, event_id"
    return [Observation(**db.loads(r["data"])) for r in db.query(sql, params)]


def get_observation(event_id: str) -> Optional[Observation]:
    rows = db.query("SELECT data FROM observations WHERE event_id=?", (event_id,))
    return Observation(**db.loads(rows[0]["data"])) if rows else None


# ---- beliefs ------------------------------------------------------------------
def get_belief(belief_id: str) -> Optional[Belief]:
    rows = db.query("SELECT data FROM beliefs WHERE id=?", (belief_id,))
    return Belief(**db.loads(rows[0]["data"])) if rows else None


def put_belief(b: Belief) -> Optional[BeliefUpdate]:
    """Write a belief; logs a BeliefUpdate and bumps version only if value/evidence changed."""
    old = get_belief(b.id)
    if old and old.value == b.value and old.evidence_ids == b.evidence_ids and old.status == b.status:
        return None
    b.version = (old.version + 1) if old else 1
    db.execute("INSERT OR REPLACE INTO beliefs(id, student_id, key, data) VALUES(?,?,?,?)",
               (b.id, b.student_id, b.key, db.dumps(b.model_dump())))
    upd = BeliefUpdate(belief_id=b.id, key=b.key, scope=b.scope, old_value=old.value if old else None,
                       new_value=b.value, version=b.version, evidence_ids=b.evidence_ids, at=b.updated_at)
    db.execute("INSERT INTO belief_updates(student_id, data) VALUES(?,?)", (b.student_id, db.dumps(upd.model_dump())))
    db.bump_state_version()
    return upd


def list_beliefs(student_id: str, key: Optional[str] = None) -> list[Belief]:
    sql, params = "SELECT data FROM beliefs WHERE student_id=?", [student_id]
    if key:
        sql += " AND key=?"
        params.append(key)
    return [Belief(**db.loads(r["data"])) for r in db.query(sql, params)]


def list_belief_updates(student_id: str, limit: int = 200) -> list[BeliefUpdate]:
    rows = db.query("SELECT data FROM belief_updates WHERE student_id=? ORDER BY seq DESC LIMIT ?", (student_id, limit))
    return [BeliefUpdate(**db.loads(r["data"])) for r in rows]


# ---- propositions -------------------------------------------------------------
def put_proposition(p: SemanticProposition) -> None:
    db.execute("INSERT OR REPLACE INTO propositions(id, student_id, data) VALUES(?,?,?)",
               (p.id, p.student_id, db.dumps(p.model_dump())))
    db.bump_state_version()


def get_proposition(pid: str) -> Optional[SemanticProposition]:
    rows = db.query("SELECT data FROM propositions WHERE id=?", (pid,))
    return SemanticProposition(**db.loads(rows[0]["data"])) if rows else None


def list_propositions(student_id: str) -> list[SemanticProposition]:
    return [SemanticProposition(**db.loads(r["data"]))
            for r in db.query("SELECT data FROM propositions WHERE student_id=?", (student_id,))]


# ---- recommendations ----------------------------------------------------------
def put_recommendation(r: Recommendation) -> None:
    db.execute("INSERT OR REPLACE INTO recommendations(id, student_id, status, data) VALUES(?,?,?,?)",
               (r.id, r.student_id, r.status, db.dumps(r.model_dump())))


def get_recommendation(rid: str) -> Optional[Recommendation]:
    rows = db.query("SELECT data FROM recommendations WHERE id=?", (rid,))
    return Recommendation(**db.loads(rows[0]["data"])) if rows else None


def delete_recommendation(rid: str) -> None:
    db.execute("DELETE FROM recommendations WHERE id=? AND status='pending'", (rid,))


def list_recommendations(student_id: str, status: Optional[str] = None) -> list[Recommendation]:
    sql, params = "SELECT data FROM recommendations WHERE student_id=?", [student_id]
    if status:
        sql += " AND status=?"
        params.append(status)
    recs = [Recommendation(**db.loads(r["data"])) for r in db.query(sql, params)]
    return sorted(recs, key=lambda r: r.created_at, reverse=True)


# ---- documents ----------------------------------------------------------------
def put_document(d: DocumentSummary, pages: list[str], student_id: str) -> None:
    db.execute("INSERT OR REPLACE INTO documents(id, student_id, data) VALUES(?,?,?)",
               (d.id, student_id, db.dumps(d.model_dump())))
    db.execute("DELETE FROM doc_pages WHERE doc_id=?", (d.id,))
    for i, text in enumerate(pages, start=1):
        db.execute("INSERT INTO doc_pages(doc_id, student_id, page, text) VALUES(?,?,?,?)", (d.id, student_id, i, text))


def get_document(doc_id: str) -> Optional[DocumentSummary]:
    rows = db.query("SELECT data FROM documents WHERE id=?", (doc_id,))
    return DocumentSummary(**db.loads(rows[0]["data"])) if rows else None


def list_documents(student_id: str) -> list[DocumentSummary]:
    docs = [DocumentSummary(**db.loads(r["data"]))
            for r in db.query("SELECT data FROM documents WHERE student_id=?", (student_id,))]
    return sorted(docs, key=lambda d: d.uploaded_at, reverse=True)


def search_pages(student_id: str, terms: list[str], limit: int = 5) -> list[dict]:
    """Keyword search across uploaded document pages (demo-grade retrieval)."""
    rows = db.query("SELECT doc_id, page, text FROM doc_pages WHERE student_id=?", (student_id,))
    scored = []
    for r in rows:
        t = r["text"].lower()
        score = sum(t.count(term.lower()) for term in terms if term)
        if score:
            scored.append({"doc_id": r["doc_id"], "page": r["page"], "text": r["text"], "score": score})
    return sorted(scored, key=lambda x: -x["score"])[:limit]


# ---- connector status ---------------------------------------------------------
def put_status(s: ConnectorStatus) -> None:
    db.execute("INSERT OR REPLACE INTO connector_status(provider, data) VALUES(?,?)", (s.provider, db.dumps(s.model_dump())))


def get_status(provider: str) -> Optional[ConnectorStatus]:
    rows = db.query("SELECT data FROM connector_status WHERE provider=?", (provider,))
    return ConnectorStatus(**db.loads(rows[0]["data"])) if rows else None


# ---- action log (external writes, real or simulated) -------------------------
def log_action(action_id: str, recommendation_id: str, data: dict) -> bool:
    if db.query("SELECT 1 FROM action_log WHERE recommendation_id=?", (recommendation_id,)):
        return False
    db.execute("INSERT INTO action_log(id, recommendation_id, data) VALUES(?,?,?)", (action_id, recommendation_id, db.dumps(data)))
    return True


def list_actions() -> list[dict]:
    return [db.loads(r["data"]) | {"recommendation_id": r["recommendation_id"]}
            for r in db.query("SELECT recommendation_id, data FROM action_log")]
