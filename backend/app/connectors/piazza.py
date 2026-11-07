"""Piazza adapter. Piazza has no official public API; live mode uses the unofficial `piazza-api`
package only when PIAZZA_ENABLED=true and it is installed. Otherwise: honest fallback."""
from __future__ import annotations

import re

from ..config import settings
from ..memory import catalog
from ..schemas import SourceRecord
from ..timeutil import now_iso
from .base import Connector, clip, record_id


def _available() -> bool:
    try:
        import piazza_api  # noqa: F401
        return True
    except Exception:
        return False


class PiazzaConnector(Connector):
    provider = "piazza"
    label = "Piazza — Course Discussions"

    def configured(self) -> bool:
        return bool(settings.piazza_enabled and settings.piazza_email and settings.piazza_password
                    and settings.piazza_network_ids and _available())

    def not_configured_detail(self) -> str:
        if settings.piazza_enabled and not _available():
            return "Piazza enabled but unofficial `piazza-api` package not installed"
        return "Piazza not enabled (no official API; feature-flagged via PIAZZA_ENABLED)"

    def fetch_live(self, student_id: str) -> list[SourceRecord]:
        from piazza_api import Piazza  # type: ignore

        p = Piazza()
        p.user_login(email=settings.piazza_email, password=settings.piazza_password)
        fetched = now_iso()
        out = []
        for nid in settings.piazza_network_ids:
            net = p.network(nid)
            for post in net.iter_all_posts(limit=15, sleep=0.5):
                hist = (post.get("history") or [{}])[0]
                subject = re.sub(r"<[^>]+>", "", hist.get("subject", "(untitled)"))
                content = re.sub(r"<[^>]+>", " ", hist.get("content", ""))
                is_instr = "instructor-note" in (post.get("tags") or []) or post.get("type") == "note" and \
                    any(t in (post.get("tags") or []) for t in ("instructor-note", "announcement"))
                out.append(SourceRecord(
                    id=record_id("piazza", f"{nid}:{post.get('nr')}", student_id), student_id=student_id, provider="piazza",
                    external_id=f"{nid}:{post.get('nr')}", kind="discussion", title=subject, body=clip(content, 1200),
                    source_url=f"https://piazza.com/class/{nid}/post/{post.get('nr')}", occurred_at=post.get("created"),
                    fetched_at=fetched, course_id=None, concept_ids=catalog.match_concepts(f"{subject} {content}"),
                    metadata={"is_instructor": bool(is_instr), "type": post.get("type")}, is_fixture=False))
        return out
