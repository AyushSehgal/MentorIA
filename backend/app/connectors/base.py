"""Connector contract: sync(student_id) -> SyncResult{records, fetched_at, status, errors}.

Each adapter handles its own auth/timeouts. A failure never raises out of sync() and never affects
other providers. Fixture fallbacks are always labeled is_fixture=True / state=demo_data.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from ..config import FIXTURES_DIR, settings
from ..schemas import ConnectorStatus, SourceRecord
from ..timeutil import human, iso, now_iso, resolve_rel

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


def load_fixture_records(provider: str, student_id: str) -> list[SourceRecord]:
    data = json.loads((FIXTURES_DIR / "source_records.json").read_text()).get(provider, [])
    fetched = now_iso()
    out = []
    for raw in data:
        meta = dict(raw.get("metadata", {}))
        for k in list(meta):
            if k.endswith("_rel"):
                meta[k[:-4]] = iso(resolve_rel(meta.pop(k)))
        body = _WHEN.sub(lambda m: human(resolve_rel(m.group(1))), raw.get("body", ""))
        out.append(SourceRecord(
            id=record_id(provider, raw["external_id"], student_id), student_id=student_id, provider=provider,
            external_id=raw["external_id"], kind=raw["kind"], title=raw["title"], body=body,
            source_url=raw.get("source_url"),
            occurred_at=iso(resolve_rel(raw["occurred_at_rel"])) if raw.get("occurred_at_rel") else None,
            fetched_at=fetched, course_id=raw.get("course_id"), concept_ids=raw.get("concept_ids", []),
            metadata=meta | {"demo_label": "Demo data"}, is_fixture=True))
    return out


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
                fallback = load_fixture_records(self.provider, student_id) if settings.demo_mode else []
                status = ConnectorStatus(provider=self.provider, state="failed", mode="fixture" if fallback else "none",
                                         detail=f"Live read failed ({err})." + (" Showing labeled demo data." if fallback else ""),
                                         last_synced_at=fetched, record_count=len(fallback), verified_live=False)
                return SyncResult(fallback, fetched, status, [err])
        if settings.demo_mode:
            recs = load_fixture_records(self.provider, student_id)
            status = ConnectorStatus(provider=self.provider, state="demo_data", mode="fixture",
                                     detail=f"{self.not_configured_detail()} — showing labeled demo data.",
                                     last_synced_at=fetched, record_count=len(recs), verified_live=False)
            return SyncResult(recs, fetched, status)
        status = ConnectorStatus(provider=self.provider, state="needs_auth", mode="none",
                                 detail=self.not_configured_detail(), last_synced_at=fetched, record_count=0)
        return SyncResult([], fetched, status)


def clip(text: Optional[str], n: int = 2000) -> str:
    return (text or "")[:n]
