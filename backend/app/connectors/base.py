"""Connector contract: sync(student_id) -> SyncResult{records, fetched_at, status, errors}.

Each adapter handles its own auth/timeouts. A failure never raises out of sync() and never affects
other providers. Fixture fallbacks are always labeled is_fixture=True / state=demo_data.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional

from .. import synthetic
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


def load_fixture_records(provider: str, student_id: str) -> list[SourceRecord]:
    """Synthetic records for one provider from fixtures/synthetic_world.md, all labeled is_fixture=True."""
    fetched = now_iso()
    out = []
    for raw in synthetic.world()["records"].get(provider, []):
        meta = dict(raw.get("metadata", {}))
        if "end" in meta:
            meta["end"] = resolve_time(meta["end"])
        body = _WHEN.sub(lambda m: human(resolve_rel(m.group(1).strip())), raw.get("body", ""))
        out.append(SourceRecord(
            id=record_id(provider, raw["external_id"], student_id), student_id=student_id, provider=provider,
            external_id=raw["external_id"], kind=raw["kind"], title=raw["title"], body=body,
            source_url=raw.get("source_url"), occurred_at=resolve_time(raw.get("when")),
            fetched_at=fetched, course_id=raw.get("course_id"), concept_ids=raw.get("concept_ids", []),
            metadata=meta | {"demo_label": "Demo data"}, is_fixture=True))
    return out


def _synthetic(provider: str, student_id: str) -> tuple[list[SourceRecord], Optional[str]]:
    """(records, error). Keeps serving the last good file version if the current edit is invalid."""
    try:
        recs = load_fixture_records(provider, student_id)
    except (synthetic.SyntheticDataError, ValueError) as e:
        return [], str(e)
    return recs, synthetic.last_error()


SYNTH_LABEL = "synthetic data from fixtures/synthetic_world.md"


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
                fallback = _synthetic(self.provider, student_id)[0] if settings.demo_mode else []
                status = ConnectorStatus(provider=self.provider, state="failed", mode="fixture" if fallback else "none",
                                         detail=f"Live read failed ({err})." + (" Showing labeled synthetic data." if fallback else ""),
                                         last_synced_at=fetched, record_count=len(fallback), verified_live=False)
                return SyncResult(fallback, fetched, status, [err])
        if settings.demo_mode:
            recs, err = _synthetic(self.provider, student_id)
            if err and not recs:
                status = ConnectorStatus(provider=self.provider, state="failed", mode="fixture", detail=f"Synthetic data error: {err}",
                                         last_synced_at=fetched, record_count=0)
                return SyncResult([], fetched, status, [err])
            detail = f"{self.not_configured_detail()} — showing {SYNTH_LABEL}."
            if err:
                detail += f" Latest edit NOT loaded ({err}); still showing the last valid version."
            status = ConnectorStatus(provider=self.provider, state="demo_data", mode="fixture", detail=detail,
                                     last_synced_at=fetched, record_count=len(recs), verified_live=False)
            return SyncResult(recs, fetched, status, [err] if err else [])
        status = ConnectorStatus(provider=self.provider, state="needs_auth", mode="none",
                                 detail=self.not_configured_detail(), last_synced_at=fetched, record_count=0)
        return SyncResult([], fetched, status)


def clip(text: Optional[str], n: int = 2000) -> str:
    return (text or "")[:n]
