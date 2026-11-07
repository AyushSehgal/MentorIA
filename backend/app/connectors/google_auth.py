"""Minimal Google OAuth token handling (server-side token file; refresh via oauth2 token endpoint)."""
from __future__ import annotations

import json
import time

import requests

from ..config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly",
          "https://www.googleapis.com/auth/gmail.readonly"]
WRITE_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret and settings.google_token_file.exists())


def _load() -> dict:
    return json.loads(settings.google_token_file.read_text())


def access_token() -> str:
    tok = _load()
    if tok.get("access_token") and tok.get("expires_at", 0) > time.time() + 60:
        return tok["access_token"]
    if not tok.get("refresh_token"):
        raise RuntimeError("Google token file has no refresh_token; re-run scripts/google_auth.py")
    r = requests.post(TOKEN_URL, data={"client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
                                       "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    tok["access_token"] = data["access_token"]
    tok["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    if "scope" in data:
        tok["scope"] = data["scope"]
    settings.google_token_file.write_text(json.dumps(tok))
    return tok["access_token"]


def granted_scopes() -> set[str]:
    try:
        return set((_load().get("scope") or "").split())
    except Exception:
        return set()


def headers() -> dict:
    return {"Authorization": f"Bearer {access_token()}"}
