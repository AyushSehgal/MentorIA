"""Google Calendar adapter: read upcoming events; create events ONLY via an approved recommendation."""
from __future__ import annotations

from datetime import timedelta

import requests

from ..config import settings
from ..memory import catalog
from ..schemas import SourceRecord
from ..timeutil import iso, now, now_iso, parse
from . import google_auth
from .base import Connector, clip, record_id

API = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class GoogleCalendarConnector(Connector):
    provider = "google_calendar"
    label = "Google Calendar — This Week"

    def configured(self) -> bool:
        return google_auth.configured()

    def not_configured_detail(self) -> str:
        return "Google not authorized (set GOOGLE_CLIENT_ID/SECRET and run scripts/google_auth.py)"

    def fetch_live(self, student_id: str) -> list[SourceRecord]:
        start = now()
        r = requests.get(API, headers=google_auth.headers(), timeout=10, params={
            "timeMin": iso(start), "timeMax": iso(start + timedelta(days=7)), "singleEvents": "true",
            "orderBy": "startTime", "maxResults": 100, "timeZone": settings.timezone})
        r.raise_for_status()
        fetched = now_iso()
        out = []
        for ev in r.json().get("items", []):
            s = ev.get("start", {})
            e = ev.get("end", {})
            all_day = "date" in s and "dateTime" not in s
            title = ev.get("summary", "(busy)")
            out.append(SourceRecord(
                id=record_id("google_calendar", ev["id"], student_id), student_id=student_id, provider="google_calendar",
                external_id=ev["id"], kind="calendar_event", title=title, body=clip(ev.get("description"), 500),
                source_url=ev.get("htmlLink"), occurred_at=s.get("dateTime") or s.get("date"), fetched_at=fetched,
                course_id=catalog.course_for_text(title), concept_ids=[],
                metadata={"end": e.get("dateTime") or e.get("date"), "all_day": all_day,
                          "transparency": ev.get("transparency", "opaque"), "created_by_nova":
                          (ev.get("extendedProperties", {}).get("private", {}).get("nova_recommendation_id"))},
                is_fixture=False))
        return out


def write_enabled() -> bool:
    return (settings.google_calendar_write_enabled and google_auth.configured()
            and google_auth.WRITE_SCOPE in google_auth.granted_scopes())


def create_event(recommendation_id: str, title: str, start_iso: str, duration_minutes: int, description: str) -> dict:
    """Create once: searches for an existing event tagged with this recommendation id first."""
    hdrs = google_auth.headers()
    found = requests.get(API, headers=hdrs, timeout=10, params={
        "privateExtendedProperty": f"nova_recommendation_id={recommendation_id}", "maxResults": 1})
    found.raise_for_status()
    if found.json().get("items"):
        ev = found.json()["items"][0]
        return {"id": ev["id"], "htmlLink": ev.get("htmlLink"), "duplicate": True}
    start = parse(start_iso)
    body = {"summary": title, "description": description,
            "start": {"dateTime": iso(start), "timeZone": settings.timezone},
            "end": {"dateTime": iso(start + timedelta(minutes=duration_minutes)), "timeZone": settings.timezone},
            "extendedProperties": {"private": {"nova_recommendation_id": recommendation_id}}}
    r = requests.post(API, headers=hdrs, json=body, timeout=10)
    r.raise_for_status()
    ev = r.json()
    return {"id": ev["id"], "htmlLink": ev.get("htmlLink"), "duplicate": False}
