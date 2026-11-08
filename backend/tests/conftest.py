from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import FIXTURES_DIR, settings
from app.memory import catalog

SID = "demo_student"
PACK = FIXTURES_DIR / "synthetic_world.md"
DOCS = {"graded": FIXTURES_DIR / "demo_docs" / "systems_quiz3_graded.pdf",
        "ungraded": FIXTURES_DIR / "demo_docs" / "systems_vm_practice_ungraded.pdf"}


def upload(client, path: Path | None, authored: bool = False, data: bytes | None = None, name: str | None = None):
    return client.post("/api/imports/upload", files={"file": (name or path.name, data if data is not None else path.read_bytes())},
                       data={"student_id": SID, "authored_by_me": "true" if authored else "false"})


def load_doc(client, which: str) -> dict:
    """Import one of the legacy systems-course PDFs and return its DocumentSummary."""
    r = upload(client, DOCS[which])
    assert r.status_code == 200, r.text
    return r.json()["document"]


@pytest.fixture(autouse=True)
def no_real_credentials(tmp_path, monkeypatch):
    """Tests never touch real accounts, whatever the developer's .env holds (it is loaded at import time).
    Without this, a configured Google token made test_approval_idempotent create a real calendar event."""
    for name, value in (("canvas_base_url", ""), ("canvas_token", ""), ("google_client_id", ""),
                        ("google_client_secret", ""), ("google_calendar_write_enabled", False),
                        ("edstem_token", ""), ("piazza_enabled", False), ("openrouter_api_key", "")):
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(settings, "google_token_file", tmp_path / "no_google_token.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture()
def empty_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", tmp_path / "test.db")
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "llm_mode", "off")
    monkeypatch.setattr(settings, "prepopulate", False)
    db.close()
    catalog.invalidate()
    from app.main import app
    with TestClient(app) as c:
        c.post("/api/demo/reset")
        yield c
    db.close()
    catalog.invalidate()


@pytest.fixture()
def client(empty_client):
    """MentorIA with the synthetic 'systems + robot learning' pack imported (the pre-v1.2 scenario)."""
    r = upload(empty_client, PACK)
    assert r.status_code == 200, r.text
    return empty_client
