"""PDF ingestion with page references.

Grading evidence is extracted ONLY from explicit markers per question block:
  "Result: Correct|Incorrect"  or  "Score: x/y" (x==y → correct, x==0 → incorrect, partial → pending_review)
Topic mapping: explicit "Topic:" line → accepted; otherwise inferred from question text → pending_review.
A question sheet without grading markers is indexed as study material and changes no beliefs.
"""
from __future__ import annotations

import hashlib
import io
import re
from datetime import datetime
from typing import Optional

from pypdf import PdfReader

from ..config import settings
from ..memory import catalog, store, updates
from ..schemas import DocumentQuestion, DocumentSummary, Observation, SourceRecord
from ..timeutil import iso, now_iso

Q_SPLIT = re.compile(r"(?m)^\s*(?:Q|Question\s*)(\d{1,2})\s*[.:)\]]")
TOPIC_RE = re.compile(r"(?im)^\s*Topic\s*:\s*(.+)$")
RESULT_RE = re.compile(r"(?im)^\s*Result\s*:\s*(correct|incorrect)\b")
SCORE_RE = re.compile(r"(?im)^\s*(?:Score|Points)\s*:\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)")
ANSWER_RE = re.compile(r"(?im)^\s*Student answer\s*:\s*(.+)$")
DATE_RE = re.compile(r"(?im)^.*\bDate\s*:\s*(\d{4}-\d{2}-\d{2})")
COURSE_RE = re.compile(r"(?im)^\s*Course\s*:\s*(.+)$")


def _grade(block: str) -> tuple[Optional[bool], Optional[str], bool]:
    """(correct, evidence_text, ambiguous)."""
    r = RESULT_RE.search(block)
    s = SCORE_RE.search(block)
    if r:
        txt = r.group(0).strip() + (f" ({s.group(0).strip()})" if s else "")
        return r.group(1).lower() == "correct", txt, False
    if s:
        got, out_of = float(s.group(1)), float(s.group(2))
        if out_of > 0 and got == out_of:
            return True, s.group(0).strip(), False
        if got == 0:
            return False, s.group(0).strip(), False
        return None, s.group(0).strip() + " (partial credit — needs review)", True
    return None, None, False


def parse_pdf(data: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(data))
    return [(p.extract_text() or "") for p in reader.pages]


def ingest_pdf(data: bytes, filename: str, student_id: str, course_id: Optional[str] = None,
               is_fixture: bool = False) -> DocumentSummary:
    sha = hashlib.sha1(data).hexdigest()[:12]
    doc_id = f"doc_{sha}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / f"{doc_id}.pdf").write_bytes(data)
    file_url = f"/api/documents/{doc_id}/file"
    src_id = f"src_pdf_{sha}"
    try:
        pages = parse_pdf(data)
    except Exception as e:
        d = DocumentSummary(id=doc_id, filename=filename, title=filename, course_id=course_id, page_count=0, status="failed",
                            kind="study_material", uploaded_at=now_iso(), is_fixture=is_fixture, source_record_id=src_id,
                            error=f"Could not read PDF: {e}", file_url=file_url)
        store.put_document(d, [], student_id)
        return d

    full = "\n".join(pages)
    title = next((ln.strip() for ln in full.splitlines() if ln.strip()), filename)[:140]
    if not course_id:
        cm = COURSE_RE.search(full)
        course_id = catalog.course_for_text(cm.group(1) if cm else title) or catalog.course_for_text(full[:500])
    dm = DATE_RE.search(full)
    assessed_at = iso(datetime.fromisoformat(dm.group(1)).replace(hour=12, tzinfo=settings.tz)) if dm else now_iso()
    if not pages or not full.strip():
        d = DocumentSummary(id=doc_id, filename=filename, title=filename, course_id=course_id, page_count=len(pages),
                            status="failed", kind="study_material", uploaded_at=now_iso(), is_fixture=is_fixture,
                            source_record_id=src_id, error="No extractable text (scanned PDF?). No grades inferred.",
                            file_url=file_url)
        store.put_document(d, pages, student_id)
        return d

    questions: list[DocumentQuestion] = []
    observations: list[Observation] = []
    for page_no, text in enumerate(pages, start=1):
        parts = Q_SPLIT.split(text)
        # parts = [pre, num, block, num, block, ...]
        for i in range(1, len(parts) - 1, 2):
            qid, block = f"Q{int(parts[i])}", parts[i + 1]
            tm = TOPIC_RE.search(block)
            topic = tm.group(1).strip() if tm else None
            concept_id = catalog.map_topic(topic, course_id) if topic else None
            inferred = False
            if not concept_id:
                guess = catalog.match_concepts(block, course_id)
                concept_id, inferred = (guess[0] if guess else None), bool(guess)
            correct, ev_text, ambiguous = _grade(block)
            ans = ANSWER_RE.search(block)
            if correct is None and not ambiguous:
                questions.append(DocumentQuestion(question_id=qid, page=page_no, concept_id=concept_id, topic_text=topic,
                                                  correct=None, evidence_text="No grading marker on this question", status="no_grade"))
                continue
            status = "accepted" if (correct is not None and concept_id and not inferred) else "pending_review"
            oid = f"obs_{doc_id}_{qid}_{concept_id or 'unmapped'}"
            evidence_text = f"{qid}: {ev_text}" + (f" — student answered “{ans.group(1).strip()[:80]}”" if ans else "")
            observations.append(Observation(
                event_id=oid, student_id=student_id, source_record_id=src_id, source="pdf_assessment",
                event_type="assessment_answer", course_id=course_id, concept_id=concept_id, occurred_at=assessed_at,
                payload={"correct": correct, "question_id": qid, "page": page_no, "evidence_text": evidence_text,
                         "topic": topic, "document_id": doc_id, "document_title": title,
                         "review_reason": None if status == "accepted" else
                         ("partial credit" if ambiguous else "topic inferred, not explicit" if inferred else "no concept mapping")},
                extraction_confidence=0.9 if status == "accepted" else 0.5, status=status, is_fixture=is_fixture))
            questions.append(DocumentQuestion(question_id=qid, page=page_no, concept_id=concept_id, topic_text=topic,
                                              correct=correct, evidence_text=evidence_text, status=status, observation_id=oid))

    graded = bool(observations)
    store.upsert_record(SourceRecord(
        id=src_id, student_id=student_id, provider="documents", external_id=doc_id,
        kind="assessment" if graded else "document", title=title, body=full[:1500], source_url=file_url,
        occurred_at=assessed_at if graded else None, fetched_at=now_iso(), course_id=course_id,
        concept_ids=sorted({q.concept_id for q in questions if q.concept_id}),
        metadata={"filename": filename, "pages": len(pages)}, is_fixture=is_fixture))
    accepted, _dup, pending, _ = updates.ingest_observations(observations)
    d = DocumentSummary(id=doc_id, filename=filename, title=title, course_id=course_id, page_count=len(pages), status="parsed",
                        kind="graded_assessment" if graded else "study_material",
                        observations_created=sum(1 for o in observations if o.status == "accepted"),
                        pending_review=sum(1 for o in observations if o.status == "pending_review"),
                        questions=questions, uploaded_at=(store.get_document(doc_id).uploaded_at if store.get_document(doc_id) else now_iso()),
                        is_fixture=is_fixture, source_record_id=src_id, file_url=file_url)
    store.put_document(d, pages, student_id)
    return d
