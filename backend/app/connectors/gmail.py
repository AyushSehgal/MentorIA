"""Gmail read-only adapter. Least-privilege: only messages matching an academic-announcement query,
bodies clipped, never sent anywhere except the local DB. Content is treated as untrusted text."""
from __future__ import annotations

import base64
from email.utils import parsedate_to_datetime

import requests

from ..memory import catalog
from ..schemas import SourceRecord
from ..timeutil import iso, now_iso
from . import google_auth
from .base import Connector, clip, record_id

API = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
QUERY = ('newer_than:21d (seminar OR talk OR colloquium OR lecture OR workshop OR "reading group" '
         'OR "research assistant" OR "speaker" OR symposium) -category:promotions')


def _body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"] + "==").decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        t = _body(part)
        if t:
            return t
    return ""


class GmailConnector(Connector):
    provider = "gmail"
    label = "Gmail — Academic Opportunities"

    def configured(self) -> bool:
        return google_auth.configured()

    def not_configured_detail(self) -> str:
        return "Gmail not authorized (run scripts/google_auth.py)"

    def fetch_live(self, student_id: str) -> list[SourceRecord]:
        hdrs = google_auth.headers()
        r = requests.get(API, headers=hdrs, params={"q": QUERY, "maxResults": 15}, timeout=10)
        r.raise_for_status()
        fetched = now_iso()
        out = []
        for m in r.json().get("messages", []):
            mr = requests.get(f"{API}/{m['id']}", headers=hdrs, params={"format": "full"}, timeout=10)
            mr.raise_for_status()
            msg = mr.json()
            h = {x["name"].lower(): x["value"] for x in msg.get("payload", {}).get("headers", [])}
            subject = h.get("subject", "(no subject)")
            body = _body(msg.get("payload", {})) or msg.get("snippet", "")
            try:
                sent = iso(parsedate_to_datetime(h["date"]))
            except Exception:
                sent = None
            out.append(SourceRecord(
                id=record_id("gmail", m["id"], student_id), student_id=student_id, provider="gmail",
                external_id=m["id"], kind="event_announcement", title=subject, body=clip(body, 3000),
                source_url=f"https://mail.google.com/mail/u/0/#all/{m['id']}", occurred_at=sent, fetched_at=fetched,
                course_id=None, concept_ids=catalog.match_concepts(f"{subject} {body[:1500]}"),
                metadata={"from": h.get("from", "")}, is_fixture=False))
        return out
