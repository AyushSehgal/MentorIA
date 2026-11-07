"""Demo asset catalog for the Add data page. Assets are regenerated once per day so their dates stay current."""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from .. import demo_content
from ..config import settings
from ..schemas import DemoAsset
from . import imports

_lock = threading.Lock()


def ensure_generated() -> Path:
    out = demo_content.OUT
    manifest = out / "manifest.json"
    today = datetime.now(settings.tz).date().isoformat()
    with _lock:
        stale = True
        if manifest.exists():
            m = json.loads(manifest.read_text())
            stale = (m.get("generated_on") != today or m.get("student_email") != settings.student_email
                     or m.get("student_name") != settings.student_name)
        if stale:
            demo_content.generate(out)
    return out


def _manifest() -> list[dict]:
    return json.loads((ensure_generated() / "manifest.json").read_text())["assets"]


def asset_path(name: str) -> Path:
    if name not in {a["name"] for a in _manifest()}:
        raise HTTPException(404, "Unknown demo asset")
    return demo_content.OUT / name


def list_assets(student_id: str) -> list[DemoAsset]:
    added = imports.imported_ids(student_id)
    out = []
    for a in _manifest():
        sha = hashlib.sha1((demo_content.OUT / a["name"]).read_bytes()).hexdigest()[:12]
        out.append(DemoAsset(**a, added=f"imp_{sha}" in added))
    return sorted(out, key=lambda a: a.step)
