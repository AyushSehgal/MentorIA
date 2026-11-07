from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import settings

_REL = re.compile(r"^d([+-]\d+)\s+(\d{1,2}):(\d{2})$")


def now() -> datetime:
    return datetime.now(settings.tz)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def now_iso() -> str:
    return iso(now())


def parse(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=settings.tz)
    return dt


def resolve_rel(spec: str, base: Optional[datetime] = None) -> datetime:
    """'d+3 16:00' -> today+3 days at 16:00 in the student timezone (fixtures only)."""
    m = _REL.match(spec.strip())
    if not m:
        raise ValueError(f"bad relative time {spec!r}")
    base = (base or now()).astimezone(settings.tz)
    day = (base + timedelta(days=int(m.group(1)))).date()
    return datetime(day.year, day.month, day.day, int(m.group(2)), int(m.group(3)), tzinfo=settings.tz)


def human(dt: datetime) -> str:
    local = dt.astimezone(settings.tz)
    return local.strftime("%A, %B %-d, %Y at %-I:%M %p ") + (local.tzname() or "")


def utc_iso(dt: datetime) -> str:
    return iso(dt.astimezone(timezone.utc))
