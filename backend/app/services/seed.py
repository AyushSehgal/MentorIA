"""Reset: MentorIA starts empty. Data enters only through the Add data page (imports) or live connectors."""
from __future__ import annotations

from .. import db
from ..memory import catalog


def reset(student_id: str = "demo_student") -> None:
    db.reset_all()  # keeps the user's LLM privacy mode
    catalog.invalidate()


def ensure_seeded(student_id: str = "demo_student") -> None:
    """Kept for compatibility: an empty database is the intended starting state."""
    return None
