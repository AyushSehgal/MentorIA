"""Manual data import: the only way data enters MentorIA until a live connector is configured.

Accepted files:
  .pdf  course overview (defines a course + concepts), graded assessment, study material, or the student's own writing
  .eml  an email; if the student sent it, explicit goals/interests in it are learned; otherwise it's an inbox item
  .ics  calendar events
  .md   a MentorIA source pack (Canvas assignments, Piazza posts, calendar, emails, courses/concepts, self-reports)

Every import is idempotent (re-adding a file changes nothing) and returns a human-readable list of what changed.
Files containing the marker MENTORIA-DEMO-ASSET are labeled demo data (is_fixture=True).
"""
from __future__ import annotations

import email
import email.policy
import hashlib
import re
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .. import db, synthetic
from ..config import settings
from ..connectors.base import record_id, resolve_time
from ..memory import catalog, propositions, store, updates
from ..schemas import DocumentSummary, ImportResult, Observation, SourceRecord
from ..timeutil import human, iso, now_iso, parse, resolve_rel
from .document_ingest import ingest_pdf, parse_pdf

DEMO_MARKER = "MENTORIA-DEMO-ASSET"
_WHEN = re.compile(r"\{when:([^}]+)\}")


class Tracker:
    """Collects human-readable changes so the UI can show what each file taught MentorIA."""

    def __init__(self, student_id: str):
        self.student_id = student_id
        self.changes: list[str] = []
        self.warnings: list[str] = []
        self.records_added = self.observations_added = self.concepts_added = self.goals_added = 0
        self._props_before = {p.id: len(p.evidence_ids) for p in store.list_propositions(student_id)}
        self._fingerprint = self.fingerprint()

    def fingerprint(self) -> tuple:
        return (len(store.list_observations(self.student_id)), len(store.list_records(self.student_id)),
                len(catalog.concepts()), len(catalog.courses()), len(catalog.load()["edges"]),
                sum(len(p.evidence_ids) for p in store.list_propositions(self.student_id)))

    def finish_goals(self) -> None:
        for p in store.list_propositions(self.student_id):
            before = self._props_before.get(p.id)
            if before is None:
                self.goals_added += 1
                self.changes.append(f"Learned a new {p.category}: “{p.statement}”")
            elif len(p.evidence_ids) > before:
                self.goals_added += 1
                self.changes.append(f"Reinforced {p.category} — now stated in {len(p.evidence_ids)} sources: “{p.statement}”")


def _sha(data: bytes | str, n: int = 12) -> str:
    return hashlib.sha1(data if isinstance(data, bytes) else data.encode()).hexdigest()[:n]


def _add_records(t: Tracker, records: list[SourceRecord], label: str) -> None:
    added = sum(1 for r in records if store.upsert_record(r))
    t.records_added += added
    if records:
        t.changes.append(f"{label}: {added} new" + (f", {len(records) - added} updated" if len(records) - added else ""))
    updates.recompute_workload(t.student_id)


def _learn_from_text(t: Tracker, text: str, source: str, ref_prefix: str, payload_extra: dict, at: str,
                     source_record_id: Optional[str], is_fixture: bool) -> None:
    obs = []
    text = re.sub(r"[ \t]*\n(?!\s*\n)[ \t]*", " ", text)  # PDF/email line wraps are not sentence breaks
    for kind, sentence in propositions.extract(text):
        obs.append(Observation(
            event_id=f"obs_{ref_prefix}_{kind}_{_sha(sentence, 8)}", student_id=t.student_id,
            source_record_id=source_record_id, source=source, event_type=kind, occurred_at=at,
            payload={"statement": sentence, "concept_ids": catalog.match_concepts(sentence)} | payload_extra,
            extraction_confidence=0.9, status="accepted", is_fixture=is_fixture))
    acc, _, _, _ = updates.ingest_observations(obs)
    t.observations_added += acc


# ---- PDF ----------------------------------------------------------------------------
_OVERVIEW = re.compile(r"(?im)^\s*Course ID\s*:\s*(\S+)")


def _course_overview(t: Tracker, text: str, is_fixture: bool) -> Optional[str]:
    m = _OVERVIEW.search(text)
    if not m or not re.search(r"(?im)^\s*Concept\s*:", text):
        return None
    field = lambda name: (re.search(rf"(?im)^\s*{name}\s*:\s*(.+)$", text) or [None, ""])[1].strip()  # noqa: E731
    cid = m.group(1).strip()
    course_line = field("Course")
    code, _, title = course_line.partition(" ")
    if not re.match(r"^\d{2}-\d{3}$", code):
        code, title = "", course_line
    label = f"{title} ({code})" if code else title
    new = catalog.upsert_course({"id": cid, "label": label, "code": code, "domain": field("Domain").lower(),
                                 "aliases": [a.strip() for a in field("Also known as").split(",") if a.strip()],
                                 "source": field("Source"), "is_fixture": is_fixture})
    t.changes.append(f"{'Added' if new else 'Updated'} course {label}")
    n_new = 0
    for line in re.findall(r"(?im)^\s*Concept\s*:\s*(.+)$", text):
        parts = [p.strip() for p in line.split("|")]
        info = {k.strip().lower(): v.strip() for k, _, v in (p.partition(":") for p in parts[1:])}
        if not info.get("id"):
            t.warnings.append(f"Concept line without id ignored: {parts[0]}")
            continue
        if catalog.upsert_concept({"id": info["id"], "course_id": cid, "label": parts[0],
                                   "aliases": [a.strip() for a in info.get("aliases", "").split(",") if a.strip()]}):
            n_new += 1
    t.concepts_added += n_new
    t.changes.append(f"{n_new} new concepts in {code or label}" if n_new else f"Concepts in {code or label} already known")
    shared = []
    for line in re.findall(r"(?im)^\s*Shared concept\s*:\s*(\w+)", text):
        if catalog.concept(line) is None:
            t.warnings.append(f"Shared concept '{line}' skipped (add the course that teaches it first)")
        elif catalog.share_concept(line, cid):
            shared.append(catalog.concept_label(line))
    if shared:
        t.changes.append(f"{len(shared)} concepts shared with other courses (one estimate, shared evidence): " + ", ".join(shared))
    known = {c["id"] for c in catalog.concepts()}
    n_edges = 0
    for line in re.findall(r"(?im)^\s*Relation\s*:\s*(.+)$", text):
        mm = re.match(r"(\w+)\s*->\s*(\w+)\s*\|\s*(\w+)", line)
        if not mm:
            continue
        a, b, rel = mm.groups()
        if a not in known or b not in known:
            t.warnings.append(f"Relation {a} -> {b} skipped (unknown concept; add the other course's overview first)")
            continue
        if rel not in ("prerequisite_of", "related_to"):
            continue
        n_edges += catalog.upsert_edge({"source": f"concept:{a}", "target": f"concept:{b}", "relation": rel,
                                        "provenance": "fixture" if is_fixture else "verified"})
    if n_edges:
        t.changes.append(f"{n_edges} concept relations (as stated in this document)")
    readings = []
    for line in re.findall(r"(?im)^\s*Reading\s*:\s*(.+)$", text):
        parts = [p.strip() for p in line.split("|")]
        info = {k.strip().lower(): v.strip() for k, _, v in (p.partition(":") for p in parts[1:])}
        title = parts[0]
        readings.append(SourceRecord(
            id=record_id("documents", f"reading:{cid}:{_sha(title, 8)}", t.student_id), student_id=t.student_id,
            provider="documents", external_id=f"reading:{cid}:{_sha(title, 8)}", kind="reading", title=title,
            source_url=info.get("url") or None, fetched_at=now_iso(), course_id=cid,
            concept_ids=[c.strip() for c in info.get("concepts", "").split(",") if catalog.concept(c.strip())],
            metadata={"course_code": code, "imported": True}, is_fixture=is_fixture))
    if readings:
        _add_records(t, readings, f"Readings from the {code or label} reading list")
    return cid


def _import_pdf(t: Tracker, data: bytes, filename: str, authored: bool, course_id: Optional[str]) -> tuple[str, str, Optional[DocumentSummary]]:
    try:
        pages = parse_pdf(data)
    except Exception as e:
        raise HTTPException(400, f"Could not read PDF: {e}")
    text = "\n".join(pages)
    is_fixture = DEMO_MARKER.encode() in data  # marker lives in the PDF metadata, not the visible text
    overview = _course_overview(t, text, is_fixture)
    doc = ingest_pdf(data, filename, t.student_id, course_id, is_fixture=is_fixture)
    if overview:
        return "course_overview", doc.title, doc
    if doc.status == "failed":
        t.warnings.append(doc.error or "PDF could not be parsed")
        return "study_material", doc.title, doc
    personal = authored or re.search(r"(?im)^\s*Document type\s*:\s*personal", text)
    if personal:
        for page_no, page in enumerate(pages, start=1):
            _learn_from_text(t, page, "document", f"{doc.id}_p{page_no}",
                             {"page": page_no, "document_id": doc.id, "document_title": doc.title},
                             doc.uploaded_at, doc.source_record_id, is_fixture)
        if not t.observations_added and not t._props_before:
            t.warnings.append("No explicit goals, interests or preferences found (look for sentences like “I want to…”).")
        return "personal_document", doc.title, doc
    if doc.kind == "graded_assessment":
        acc = sum(1 for q in doc.questions if q.status == "accepted")
        wrong = [q.question_id for q in doc.questions if q.status == "accepted" and q.correct is False]
        t.changes.append(f"{acc} graded answers became evidence" + (f" ({len(wrong)} incorrect: {', '.join(wrong)})" if wrong else ""))
        touched = sorted({q.concept_id for q in doc.questions if q.status == "accepted" and q.concept_id})
        for cid in touched:
            b = store.get_belief(updates.mastery_belief_id(t.student_id, cid))
            if b is not None:
                t.changes.append(f"Mastery estimate for {catalog.concept_label(cid)}: {float(b.value):.2f}")
        unmapped = [q.question_id for q in doc.questions if q.status == "pending_review" and not q.concept_id]
        partial = [q.question_id for q in doc.questions if q.status == "pending_review" and q.concept_id]
        if unmapped:
            t.warnings.append(f"{len(unmapped)} answer(s) couldn't be matched to a known concept ({', '.join(unmapped)}). "
                              "Add the course overview first, then add this file again.")
        if partial:
            t.changes.append(f"{len(partial)} answer(s) held for review (e.g. partial credit): {', '.join(partial)}")
        t.observations_added += acc
        return "graded_assessment", doc.title, doc
    t.changes.append(f"Indexed {doc.page_count} page(s) as study material — knowledge estimates unchanged")
    return "study_material", doc.title, doc


# ---- EML ----------------------------------------------------------------------------
def _body_text(msg) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", " ", content)
    return content.strip()


def _import_eml(t: Tracker, data: bytes, filename: str) -> tuple[str, str]:
    try:
        msg = email.message_from_bytes(data, policy=email.policy.default)
    except Exception as e:
        raise HTTPException(400, f"Could not parse email: {e}")
    subject = str(msg.get("Subject", "(no subject)"))
    sender = parseaddr(str(msg.get("From", "")))[1].lower()
    body = _body_text(msg)
    is_fixture = DEMO_MARKER in data.decode("utf-8", "replace")
    try:
        sent = iso(parsedate_to_datetime(str(msg["Date"]))) if msg.get("Date") else now_iso()
    except Exception:
        sent = now_iso()
    ext_id = "file:" + (str(msg.get("Message-ID", "")).strip("<> ") or _sha(data))
    from_student = sender == settings.student_email.lower()
    rec = SourceRecord(
        id=record_id("gmail", ext_id, t.student_id), student_id=t.student_id, provider="gmail", external_id=ext_id,
        kind="message" if from_student else "event_announcement", title=subject, body=body[:3000], source_url=None,
        occurred_at=sent, fetched_at=now_iso(), course_id=catalog.course_for_text(f"{subject} {body[:500]}"),
        concept_ids=catalog.match_concepts(f"{subject} {body[:1500]}"),
        metadata={"from": sender, "to": parseaddr(str(msg.get("To", "")))[1], "imported": True, "filename": filename,
                  "sent_by_student": from_student},
        is_fixture=is_fixture)
    _add_records(t, [rec], "Emails")
    if from_student:
        t.changes.append("You sent this email, so MentorIA read it for your stated goals and interests")
        _learn_from_text(t, body, "email", f"eml_{_sha(ext_id, 10)}", {"subject": subject}, sent, rec.id, is_fixture)
    else:
        t.changes.append(f"Added to Gmail opportunities (from {sender or 'unknown sender'})")
    return "email", subject


# ---- ICS ----------------------------------------------------------------------------
def _ics_time(value: str, params: str) -> Optional[str]:
    value = value.strip()
    tz = re.search(r"TZID=([^;:]+)", params)
    try:
        if len(value) == 8:  # all-day
            return datetime.strptime(value, "%Y%m%d").replace(tzinfo=settings.tz).isoformat()
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
        dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
        return dt.replace(tzinfo=ZoneInfo(tz.group(1)) if tz else settings.tz).isoformat()
    except Exception:
        return None


def _import_ics(t: Tracker, data: bytes, filename: str) -> tuple[str, str]:
    text = data.decode("utf-8", "replace")
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold
    is_fixture = DEMO_MARKER in text
    events = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        props: dict[str, tuple[str, str]] = {}
        for line in block.strip().splitlines():
            key, _, value = line.partition(":")
            name, _, params = key.partition(";")
            props[name.upper()] = (params, value)
        start = _ics_time(props.get("DTSTART", ("", ""))[1], props.get("DTSTART", ("", ""))[0])
        if not start:
            t.warnings.append(f"Skipped an event without a readable start time ({props.get('SUMMARY', ('', '?'))[1]})")
            continue
        end = _ics_time(props.get("DTEND", ("", ""))[1], props.get("DTEND", ("", ""))[0])
        title = props.get("SUMMARY", ("", "(busy)"))[1].replace("\\,", ",")
        uid = "file:" + (props.get("UID", ("", ""))[1] or _sha(f"{title}{start}"))
        events.append(SourceRecord(
            id=record_id("google_calendar", uid, t.student_id), student_id=t.student_id, provider="google_calendar",
            external_id=uid, kind="calendar_event", title=title,
            body=props.get("DESCRIPTION", ("", ""))[1].replace("\\n", "\n")[:500], occurred_at=start, fetched_at=now_iso(),
            course_id=catalog.course_for_text(title), concept_ids=[],
            metadata={"end": end, "all_day": len(props.get("DTSTART", ("", ""))[1].strip()) == 8, "imported": True,
                      "location": props.get("LOCATION", ("", ""))[1]},
            is_fixture=is_fixture))
    if not events:
        raise HTTPException(400, "No calendar events found in this .ics file")
    _add_records(t, events, "Calendar events")
    return "calendar", f"Calendar ({len(events)} events)"


# ---- MD source pack -------------------------------------------------------------------
def _import_pack(t: Tracker, data: bytes, filename: str) -> tuple[str, str]:
    text = data.decode("utf-8", "replace")
    is_fixture = DEMO_MARKER in text or "synthetic" in text[:400].lower()
    try:
        world = synthetic.parse_world(text, known_courses={c["id"] for c in catalog.courses()},
                                      known_concepts={c["id"]: c["course_id"] for c in catalog.concepts()})
    except synthetic.SyntheticDataError as e:
        raise HTTPException(400, f"{filename}: {e}")
    for c in world["courses"]:
        new = catalog.upsert_course(c | {"is_fixture": is_fixture})
        t.changes.append(f"{'Added' if new else 'Updated'} course {c['label']}")
    n_new = sum(catalog.upsert_concept(c) for c in world["concepts"])
    t.concepts_added += n_new
    if world["concepts"]:
        t.changes.append(f"{n_new} new concepts")
    for e in world["edges"]:
        catalog.upsert_edge(e | {"provenance": "fixture" if is_fixture else "verified"})
    labels = {"canvas": "Canvas assignments", "google_calendar": "Calendar events", "gmail": "Emails", "piazza": "Piazza posts"}
    for provider, raws in world["records"].items():
        recs = []
        for raw in raws:
            meta = dict(raw.get("metadata", {})) | {"imported": True, "filename": filename}
            if "end" in meta:
                meta["end"] = resolve_time(meta["end"])
            body = _WHEN.sub(lambda m: human(resolve_rel(m.group(1).strip())), raw.get("body", ""))
            recs.append(SourceRecord(
                id=record_id(provider, raw["external_id"], t.student_id), student_id=t.student_id, provider=provider,
                external_id=raw["external_id"], kind=raw["kind"], title=raw["title"], body=body,
                source_url=raw.get("source_url"),
                occurred_at=resolve_time(raw.get("when")), fetched_at=now_iso(), course_id=raw.get("course_id"),
                concept_ids=raw.get("concept_ids") or catalog.match_concepts(f"{raw['title']} {body}"),
                metadata=meta, is_fixture=is_fixture))
        if recs:
            _add_records(t, recs, labels[provider])
    obs = [Observation(event_id=raw["event_id"], student_id=t.student_id, source=raw["source"], event_type=raw["event_type"],
                       course_id=raw.get("course_id"), concept_id=raw.get("concept_id"), occurred_at=resolve_time(raw["when"]),
                       payload=raw["payload"], extraction_confidence=1.0, status="accepted", is_fixture=is_fixture)
           for raw in world["profile"]["seed_observations"]]
    acc, _, _, _ = updates.ingest_observations(obs)
    t.observations_added += acc
    return "source_pack", filename


# ---- entry points ---------------------------------------------------------------------
def import_file(data: bytes, filename: str, student_id: str, authored_by_me: bool = False,
                course_id: Optional[str] = None) -> ImportResult:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    t = Tracker(student_id)
    doc = None
    if ext == "pdf" or data.startswith(b"%PDF"):
        kind, title, doc = _import_pdf(t, data, filename, authored_by_me, course_id)
    elif ext == "eml":
        kind, title = _import_eml(t, data, filename)
    elif ext == "ics":
        kind, title = _import_ics(t, data, filename)
    elif ext in ("md", "markdown"):
        kind, title = _import_pack(t, data, filename)
    else:
        raise HTTPException(400, "Unsupported file type. Add a .pdf, .eml, .ics or MentorIA .md source pack.")
    t.finish_goals()
    if t.fingerprint() == t._fingerprint:
        t.changes = ["Already added — nothing new was learned from this file."]
        t.records_added = t.observations_added = t.concepts_added = t.goals_added = 0
    is_fixture = DEMO_MARKER.encode() in data or bool(doc and doc.is_fixture)
    result = ImportResult(
        id=f"imp_{_sha(data)}", filename=filename, kind=kind, title=title, summary=t.changes[0], changes=t.changes,
        records_added=t.records_added, observations_added=t.observations_added, concepts_added=t.concepts_added,
        goals_added=t.goals_added, document=store.get_document(doc.id) if doc else None, is_fixture=is_fixture,
        imported_at=now_iso(), warnings=t.warnings)
    db.execute("INSERT OR REPLACE INTO imports(id, student_id, imported_at, data) VALUES(?,?,?,?)",
               (result.id, student_id, result.imported_at, db.dumps(result.model_dump())))
    db.bump_state_version()
    return result


def list_imports(student_id: str) -> list[ImportResult]:
    rows = db.query("SELECT data FROM imports WHERE student_id=? ORDER BY imported_at DESC", (student_id,))
    return [ImportResult(**db.loads(r["data"])) for r in rows]


def imported_ids(student_id: str) -> set[str]:
    return {r["id"] for r in db.query("SELECT id FROM imports WHERE student_id=?", (student_id,))}
