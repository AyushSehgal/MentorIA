from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import db
from ..config import FIXTURES_DIR, settings
from ..memory import store
from ..schemas import ConnectorStatus, DashboardResponse, DocumentSummary, HealthResponse, SyncResponse
from ..services import aggregation, dashboard as dash, seed
from ..services.document_ingest import ingest_pdf

router = APIRouter(prefix="/api")
DEMO_DOCS = {"graded_quiz": "systems_quiz3_graded.pdf", "ungraded_sheet": "systems_vm_practice_ungraded.pdf"}
MAX_UPLOAD = 25 * 1024 * 1024


@router.get("/health", response_model=HealthResponse)
def health(student_id: str = "demo_student"):
    return HealthResponse(status="ok", db="ok" if db.ping() else "error", demo_mode=settings.demo_mode,
                          llm={"enabled": settings.llm_enabled, "model": settings.llm_model if settings.llm_enabled else None},
                          providers=aggregation.statuses(student_id))


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(student_id: str = "demo_student"):
    return dash.dashboard(student_id)


@router.get("/connectors", response_model=list[ConnectorStatus])
def connectors(student_id: str = "demo_student"):
    return aggregation.statuses(student_id)


@router.post("/connectors/sync", response_model=list[SyncResponse])
def sync_all(student_id: str = "demo_student"):
    if settings.demo_mode:
        try:
            seed.ingest_self_reports(student_id)  # new self-report rows in the synthetic file
        except Exception:
            pass  # a bad edit is reported on the source cards; don't block the sync
    return aggregation.sync_all(student_id)


@router.post("/connectors/{provider}/sync", response_model=SyncResponse)
def sync_one(provider: str, student_id: str = "demo_student"):
    if provider not in aggregation.PROVIDERS:
        raise HTTPException(404, f"Unknown provider {provider}")
    return aggregation.sync_provider(provider, student_id)


@router.post("/documents/upload", response_model=DocumentSummary)
async def upload(file: UploadFile = File(...), course_id: Optional[str] = Form(None), student_id: str = Form("demo_student")):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "PDF too large (25 MB max)")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Only PDF files are supported")
    return ingest_pdf(data, file.filename or "upload.pdf", student_id, course_id or None, is_fixture=False)


@router.post("/documents/demo/{name}", response_model=DocumentSummary)
def demo_doc(name: str, student_id: str = "demo_student"):
    if name not in DEMO_DOCS:
        raise HTTPException(404, "Unknown demo document")
    path = FIXTURES_DIR / "demo_docs" / DEMO_DOCS[name]
    return ingest_pdf(path.read_bytes(), path.name, student_id, None, is_fixture=True)


@router.get("/documents", response_model=list[DocumentSummary])
def documents(student_id: str = "demo_student"):
    return store.list_documents(student_id)


@router.get("/documents/{doc_id}/file")
def document_file(doc_id: str):
    d = store.get_document(doc_id)
    path = settings.upload_dir / f"{doc_id}.pdf"
    if not d or not path.exists():
        raise HTTPException(404, "Document not found")
    return FileResponse(path, media_type="application/pdf", filename=d.filename,
                        headers={"Content-Disposition": f'inline; filename="{d.filename}"'})
