"""Canvas LMS read-only adapter (REST API v1 with a personal access token)."""
from __future__ import annotations

import re

import requests

from ..config import settings
from ..memory import catalog
from ..schemas import SourceRecord
from ..timeutil import now_iso
from .base import Connector, clip, record_id


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _excluded(course: dict) -> bool:
    """CANVAS_EXCLUDE_COURSES: comma-separated course names, codes or ids (case-insensitive, exact) that are never synced."""
    keys = {str(course.get(k, "")).strip().lower() for k in ("name", "course_code", "id")}
    return bool(keys & set(settings.canvas_exclude_courses))


class CanvasConnector(Connector):
    provider = "canvas"
    label = "Canvas — Due Soon"

    def configured(self) -> bool:
        return bool(settings.canvas_base_url and settings.canvas_token)

    def not_configured_detail(self) -> str:
        return "Canvas not configured (set CANVAS_BASE_URL and CANVAS_API_TOKEN)"

    def _get(self, path: str, params: dict | None = None) -> list | dict:
        r = requests.get(f"{settings.canvas_base_url}/api/v1{path}", params=params,
                         headers={"Authorization": f"Bearer {settings.canvas_token}"}, timeout=10)
        r.raise_for_status()
        return r.json()

    def fetch_live(self, student_id: str) -> list[SourceRecord]:
        fetched = now_iso()
        courses = self._get("/users/self/courses", {"enrollment_state": "active", "per_page": 30})
        out: list[SourceRecord] = []
        # Drop excluded courses before the 12-course cap, so an exclusion never pushes out a course you want.
        courses = [c for c in courses if isinstance(c, dict) and "id" in c and not _excluded(c)]
        for c in courses[:12]:
            name = c.get("name") or c.get("course_code") or str(c["id"])
            course_id = catalog.course_for_text(name) or f"canvas_{c['id']}"
            try:
                assignments = self._get(f"/courses/{c['id']}/assignments",
                                        {"bucket": "future", "per_page": 30, "include[]": "submission", "order_by": "due_at"})
            except requests.HTTPError:
                continue  # some courses hide assignments; skip just that course
            for a in assignments:
                desc = _strip_html(a.get("description") or "")
                sub = a.get("submission") or {}
                out.append(SourceRecord(
                    id=record_id("canvas", str(a["id"]), student_id), student_id=student_id, provider="canvas",
                    external_id=str(a["id"]), kind="assignment", title=a.get("name", "Untitled"), body=clip(desc, 800),
                    source_url=a.get("html_url"), occurred_at=a.get("due_at"), fetched_at=fetched, course_id=course_id,
                    concept_ids=catalog.match_concepts(f"{a.get('name', '')} {desc}"),
                    metadata={"course_name": name, "points_possible": a.get("points_possible"),
                              "completed": sub.get("workflow_state") in {"submitted", "graded"}},
                    is_fixture=False))
        return out
