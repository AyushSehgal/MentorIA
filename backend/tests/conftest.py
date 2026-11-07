import pytest
from fastapi.testclient import TestClient

from app import db, synthetic
from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", tmp_path / "test.db")
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "llm_mode", "off")
    db.close()
    synthetic.reset_cache()
    from app.main import app
    with TestClient(app) as c:
        c.post("/api/demo/reset")
        yield c
    db.close()
    synthetic.reset_cache()
