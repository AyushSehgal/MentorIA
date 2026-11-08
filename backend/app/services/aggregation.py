"""Connector aggregation: sync → normalize → dedup → persist. Provider failures are isolated."""
from __future__ import annotations

from datetime import datetime, timedelta

from .. import db
from ..connectors import CONNECTORS
from ..schemas import ConnectorStatus, FreeWindow, SourceRecord, SyncResponse
from ..timeutil import iso, now, parse
from ..memory import store, updates

PROVIDERS = ["canvas", "google_calendar", "gmail", "piazza", "edstem"]


def sync_provider(provider: str, student_id: str) -> SyncResponse:
    conn = CONNECTORS[provider]
    try:
        result = conn.sync(student_id)
    except Exception as e:  # defensive: adapters should not raise, but never let one break others
        status = ConnectorStatus(provider=provider, state="failed", mode="none", detail=f"Adapter crashed: {e}")
        store.put_status(status)
        return SyncResponse(provider=provider, status=status, records_added=0,
                            records_total=len(store.list_records(student_id, provider=provider)), errors=[str(e)])
    added = 0
    if result.records or result.status.state in ("connected", "demo_data"):
        # Replace this provider's records with the fresh snapshot (removes deleted events / stale fixtures).
        keep = {r.external_id for r in result.records} | {r.external_id for r in store.list_records(student_id, provider=provider)
                                                           if r.metadata.get("imported")}
        store.delete_records(student_id, provider, keep_external_ids=keep)
        added, _ = updates.ingest_records(result.records)
    store.put_status(result.status)
    updates.recompute_workload(student_id)
    db.bump_state_version()
    return SyncResponse(provider=provider, status=result.status, records_added=added,
                        records_total=len(store.list_records(student_id, provider=provider)), errors=result.errors)


def sync_all(student_id: str) -> list[SyncResponse]:
    return [sync_provider(p, student_id) for p in PROVIDERS]


def statuses(student_id: str) -> list[ConnectorStatus]:
    out = []
    for p in PROVIDERS:
        s = store.get_status(p)
        imported = [r for r in store.list_records(student_id, provider=p) if r.metadata.get("imported")]
        if s and s.state == "connected":
            out.append(s)
        elif imported:
            detail = f"{len(imported)} item(s) added from files — not a live connection."
            if s and s.state == "failed":
                detail += f" Live sync failed: {s.detail}"
            out.append(ConnectorStatus(provider=p, state="imported", mode="import", detail=detail, record_count=len(imported),
                                       last_synced_at=max((r.fetched_at for r in imported), default=None), verified_live=False))
        else:
            out.append(s or ConnectorStatus(provider=p, state="not_available", mode="none",
                                            detail="Not connected. Add exported files on the Add data page."))
    docs = store.list_documents(student_id)
    out.append(ConnectorStatus(provider="documents", state="connected", mode="live",
                               detail=f"Local PDF uploads ({len(docs)} document(s))", record_count=len(docs),
                               last_synced_at=docs[0].uploaded_at if docs else None, verified_live=True))
    return out


def event_bounds(r: SourceRecord) -> tuple[datetime, datetime] | None:
    s = parse(r.occurred_at)
    e = parse(r.metadata.get("end")) if r.metadata.get("end") else None
    if not s:
        return None
    if r.metadata.get("all_day"):
        return None  # all-day events don't block study windows
    return s, (e or s + timedelta(hours=1))


def free_windows(student_id: str, days: int = 7, day_start: int = 9, day_end: int = 21,
                 min_minutes: int = 45, extra_busy: list[tuple[datetime, datetime]] | None = None) -> list[FreeWindow]:
    busy = [b for r in store.list_records(student_id, kind="calendar_event")
            if r.metadata.get("transparency") != "transparent" and (b := event_bounds(r))]
    busy += extra_busy or []
    busy.sort()
    start_now = now()
    minute = 30 * ((start_now.minute // 30) + 1)
    cursor0 = start_now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minute)
    out: list[FreeWindow] = []
    for d in range(days):
        day = (start_now + timedelta(days=d)).date()
        ws = datetime(day.year, day.month, day.day, day_start, tzinfo=start_now.tzinfo)
        we = datetime(day.year, day.month, day.day, day_end, tzinfo=start_now.tzinfo)
        cur = max(ws, cursor0)
        for bs, be in busy:
            if be <= cur or bs >= we:
                continue
            if bs > cur and (bs - cur) >= timedelta(minutes=min_minutes):
                out.append(FreeWindow(start=iso(cur), end=iso(bs), minutes=int((bs - cur).total_seconds() // 60)))
            cur = max(cur, be)
        if we > cur and (we - cur) >= timedelta(minutes=min_minutes):
            out.append(FreeWindow(start=iso(cur), end=iso(we), minutes=int((we - cur).total_seconds() // 60)))
    return out
