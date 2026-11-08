"""Ed Discussion read-only adapter (personal API token from edstem.org/us/settings/api-tokens).

Best effort: Ed's REST API is not officially documented, so a shape change fails this provider only (isolated by
Connector.sync). Read-only: MentorIA never posts, replies or votes. Private threads are skipped.
"""
from __future__ import annotations

import re

import requests

from ..config import settings
from ..memory import catalog
from ..schemas import SourceRecord
from ..timeutil import now_iso
from .base import Connector, clip, record_id

THREADS_PER_COURSE = 30
STAFF_ROLES = {"admin", "staff", "mentor", "tutor"}


def course_code(code: str) -> str:
    """Ed stores "11868" or "11-868"; MentorIA courses use "11-868"."""
    digits = re.sub(r"\D", "", code or "")
    return f"{digits[:2]}-{digits[2:]}" if len(digits) == 5 else (code or "").strip()


def _excluded(course: dict) -> bool:
    """EDSTEM_EXCLUDE_COURSES: comma-separated course names, codes or ids (case-insensitive, exact) never synced."""
    keys = {str(course.get(k, "")).strip().lower() for k in ("name", "code", "id")} | {course_code(course.get("code", "")).lower()}
    return bool(keys & set(settings.edstem_exclude_courses))


class EdStemConnector(Connector):
    provider = "edstem"
    label = "Ed Discussion — Course Discussions"

    def configured(self) -> bool:
        return bool(settings.edstem_token)

    def not_configured_detail(self) -> str:
        return "Ed Discussion not configured (set EDSTEM_API_TOKEN)"

    def _get(self, path: str, params: dict | None = None) -> dict:
        r = requests.get(f"{settings.edstem_base_url}/api{path}", params=params,
                         headers={"Authorization": f"Bearer {settings.edstem_token}"}, timeout=10)
        r.raise_for_status()
        return r.json()

    def fetch_live(self, student_id: str) -> list[SourceRecord]:
        fetched = now_iso()
        me = self._get("/user")
        courses = [e["course"] for e in me.get("courses", [])
                   if isinstance(e, dict) and isinstance(e.get("course"), dict) and e["course"].get("status") == "active"
                   and not _excluded(e["course"])]
        out: list[SourceRecord] = []
        for c in courses:
            code = course_code(c.get("code", ""))
            name = f"{code} {c.get('name', '')}".strip() if code else c.get("name", str(c["id"]))
            course_id = code if catalog.course(code) else None  # only an exact course-number match links to MentorIA
            data = self._get(f"/courses/{c['id']}/threads", {"limit": THREADS_PER_COURSE, "sort": "new"})
            roles = {u.get("id"): (u.get("course_role") or "") for u in data.get("users", [])}
            for t in data.get("threads", []):
                if t.get("is_private") or t.get("deleted_at"):
                    continue
                title = t.get("title") or "(untitled)"
                body = t.get("document") or ""
                staff = roles.get(t.get("user_id")) in STAFF_ROLES or t.get("type") == "announcement"
                out.append(SourceRecord(
                    id=record_id("edstem", str(t["id"]), student_id), student_id=student_id, provider="edstem",
                    external_id=str(t["id"]), kind="discussion", title=title, body=clip(body, 1200),
                    source_url=f"https://edstem.org/us/courses/{c['id']}/discussion/{t['id']}",
                    occurred_at=t.get("created_at"), fetched_at=fetched, course_id=course_id,
                    concept_ids=catalog.match_concepts(f"{title} {body[:1500]}", course_id) if course_id else [],
                    metadata={"is_instructor": bool(staff), "type": t.get("type", ""), "category": t.get("category", ""),
                              "course_name": name, "is_answered": bool(t.get("is_answered")),
                              "reply_count": t.get("reply_count", 0)},
                    is_fixture=False))
        return out
