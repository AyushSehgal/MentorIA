"""Connector contract: sync(student_id) -> SyncResult{records, fetched_at, status, errors}.

Each adapter handles its own auth/timeouts. A failure never raises out of sync() and never affects
other providers. Fixture fallbacks are always labeled is_fixture=True / state=demo_data.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional

from ..config import settings
from ..schemas import ConnectorStatus, SourceRecord
from ..timeutil import human, iso, now_iso, parse, resolve_rel

_WHEN = re.compile(r"\{when:([^}]+)\}")


@dataclass
class SyncResult:
    records: list[SourceRecord]
    fetched_at: str
    status: ConnectorStatus
    errors: list[str] = field(default_factory=list)


def record_id(provider: str, external_id: str, student_id: str) -> str:
    h = hashlib.sha1(f"{student_id}:{provider}:{external_id}".encode()).hexdigest()[:10]
    return f"src_{provider}_{h}"


def resolve_time(spec: Optional[str]) -> Optional[str]:
    """'d+3 16:00' (relative to today, student timezone) or an ISO timestamp -> ISO string; blank -> None."""
    spec = (spec or "").strip()
    if not spec:
        return None
    if spec.startswith("d"):
        return iso(resolve_rel(spec))
    dt = parse(spec)
    if dt is None:
        raise ValueError(f"Unrecognized time '{spec}' (use 'd+N HH:MM' or ISO 8601)")
    return iso(dt)


class Connector:
    provider: str = ""
    label: str = ""

    def configured(self) -> bool:
        return False

    def not_configured_detail(self) -> str:
        return "Not configured"

    def fetch_live(self, student_id: str) -> list[SourceRecord]:
        raise NotImplementedError

    def sync(self, student_id: str) -> SyncResult:
        fetched = now_iso()
        if self.configured():
            try:
                records = self.fetch_live(student_id)
                status = ConnectorStatus(provider=self.provider, state="connected", mode="live",
                                         detail=f"Live read OK ({len(records)} records)", last_synced_at=fetched,
                                         record_count=len(records), verified_live=True)
                return SyncResult(records, fetched, status)
            except Exception as e:  # isolate provider failures
                err = f"{type(e).__name__}: {str(e)[:200]}"
                status = ConnectorStatus(provider=self.provider, state="failed", mode="none",
                                         detail=f"Live read failed ({err}). Items added from files are unaffected.",
                                         last_synced_at=fetched, record_count=0, verified_live=False)
                return SyncResult([], fetched, status, [err])
        status = ConnectorStatus(provider=self.provider, state="not_available", mode="none",
                                 detail=f"{self.not_configured_detail()}. Add exported files on the Add data page instead.",
                                 last_synced_at=fetched, record_count=0)
        return SyncResult([], fetched, status)


def clip(text: Optional[str], n: int = 2000) -> str:
    return (text or "")[:n]
