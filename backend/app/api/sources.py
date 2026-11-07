from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import db
from ..config import settings
from ..memory import store
from ..schemas import DemoAsset, ImportResult, PrivacySettings, PrivacyUpdate, ConnectorStatus, DashboardResponse, DocumentSummary, HealthResponse, SyncResponse
from ..orchestration import llm
from ..services import aggregation, dashboard as dash, demo_assets as demo_assets_svc, imports

router = APIRouter(prefix="/api")
MAX_UPLOAD = 25 * 1024 * 1024


@router.get("/health", response_model=HealthResponse)
def health(student_id: str = "demo_student"):
    mode = llm.get_mode()
    model = {"local": f"local:{settings.llm_local_model}", "cloud": settings.llm_cloud_provider}.get(mode)
    return HealthResponse(status="ok", db="ok" if db.ping() else "error", demo_mode=settings.demo_mode,
                          llm={"enabled": mode != "off", "model": model, "mode": mode},
                          providers=aggregation.statuses(student_id))


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(student_id: str = "demo_student"):
    return dash.dashboard(student_id)


@router.get("/connectors", response_model=list[ConnectorStatus])
def connectors(student_id: str = "demo_student"):
    return aggregation.statuses(student_id)


@router.post("/connectors/sync", response_model=list[SyncResponse])
def sync_all(student_id: str = "demo_student"):
    return aggregation.sync_all(student_id)


@router.post("/connectors/{provider}/sync", response_model=SyncResponse)
def sync_one(provider: str, student_id: str = "demo_student"):
    if provider not in aggregation.PROVIDERS:
        raise HTTPException(404, f"Unknown provider {provider}")
    return aggregation.sync_provider(provider, student_id)


@router.post("/documents/upload", response_model=DocumentSummary)
async def upload(file: UploadFile = File(...), course_id: Optional[str] = Form(None), student_id: str = Form("demo_student")):
    """Legacy PDF route; prefer /api/imports/upload."""
    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Only PDF files are supported")
    res = imports.import_file(data, file.filename or "upload.pdf", student_id, False, course_id or None)
    return res.document


@router.post("/imports/upload", response_model=ImportResult)
async def import_upload(file: UploadFile = File(...), student_id: str = Form("demo_student"),
                        authored_by_me: str = Form("false"), course_id: Optional[str] = Form(None)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File too large (25 MB max)")
    return imports.import_file(data, file.filename or "upload", student_id, authored_by_me.lower() == "true", course_id or None)


@router.get("/imports", response_model=list[ImportResult])
def import_history(student_id: str = "demo_student"):
    return imports.list_imports(student_id)


@router.get("/imports/demo", response_model=list[DemoAsset])
def demo_assets(student_id: str = "demo_student"):
    return demo_assets_svc.list_assets(student_id)


@router.post("/imports/demo/{name}", response_model=ImportResult)
def add_demo_asset(name: str, student_id: str = "demo_student"):
    path = demo_assets_svc.asset_path(name)
    return imports.import_file(path.read_bytes(), path.name, student_id, False, None)


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


SENT_TO_LLM = ("Only your question and NOVA's drafted answer (concept names, estimates, deadlines, and email/assignment "
               "titles it cites). Raw emails, PDFs and the database are never sent.")


def _privacy() -> PrivacySettings:
    mode = llm.get_mode()
    lok, ldet = llm.local_available()
    cok, cdet = llm.cloud_available()
    return PrivacySettings(mode=mode, local_available=lok, local_detail=ldet, cloud_available=cok, cloud_detail=cdet,
                           data_leaves_device=(mode == "cloud"), sent_to_llm=SENT_TO_LLM)


@router.get("/settings/privacy", response_model=PrivacySettings)
def get_privacy():
    return _privacy()


@router.post("/settings/privacy", response_model=PrivacySettings)
def set_privacy(req: PrivacyUpdate):
    llm.set_mode(req.mode)
    return _privacy()
