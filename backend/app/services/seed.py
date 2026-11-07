"""Starting data. MentorIA starts PREPOPULATED with the sample files in demo_assets/ (imported in order through the
normal import pipeline), so the dashboard is full from the first load. MENTORIA_PREPOPULATE=false gives an empty start."""
from __future__ import annotations

import logging

from .. import db
from ..config import settings
from ..memory import catalog

log = logging.getLogger("mentoria.seed")


def seed(student_id: str = "demo_student") -> int:
    from . import demo_assets, imports  # local import: avoids a cycle at startup

    n = 0
    for a in demo_assets.list_assets(student_id):
        path = demo_assets.asset_path(a.name)
        imports.import_file(path.read_bytes(), path.name, student_id, False, None)
        n += 1
    log.info("Prepopulated %d sample files", n)
    return n


def reset(student_id: str = "demo_student") -> None:
    db.reset_all()  # keeps the user's LLM privacy mode
    catalog.invalidate()
    if settings.prepopulate:
        seed(student_id)


def ensure_seeded(student_id: str = "demo_student") -> None:
    """On startup: load the sample data once if the database has never been populated."""
    if settings.prepopulate and not db.query("SELECT 1 FROM imports LIMIT 1"):
        seed(student_id)
