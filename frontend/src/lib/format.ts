export const FALLBACK_TZ = "America/New_York";

function safeDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

export function fmtDateTime(iso: string | null | undefined, tz: string = FALLBACK_TZ): string {
  const d = safeDate(iso);
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    }).format(d);
  } catch {
    return d.toLocaleString();
  }
}

export function fmtTime(iso: string | null | undefined, tz: string = FALLBACK_TZ): string {
  const d = safeDate(iso);
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: tz, hour: "numeric", minute: "2-digit" }).format(d);
  } catch {
    return d.toLocaleTimeString();
  }
}

export function dayKey(iso: string | null | undefined, tz: string = FALLBACK_TZ): string {
  const d = safeDate(iso);
  if (!d) return "Undated";
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "long", month: "short", day: "numeric" }).format(d);
  } catch {
    return d.toDateString();
  }
}

export function relative(iso: string | null | undefined): string {
  const d = safeDate(iso);
  if (!d) return "no date";
  const diffMs = d.getTime() - Date.now();
  const abs = Math.abs(diffMs);
  const hours = abs / 36e5;
  let s: string;
  if (hours < 1) s = `${Math.max(1, Math.round(abs / 6e4))} min`;
  else if (hours < 48) s = `${Math.round(hours)} h`;
  else s = `${Math.round(hours / 24)} days`;
  return diffMs >= 0 ? `in ${s}` : `${s} ago`;
}

export function pct(v: number | null | undefined): string {
  if (v === null || v === undefined || isNaN(v)) return "—";
  return `${Math.round(v * 100)}%`;
}

export function masteryColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return "var(--muted-2)";
  if (v < 0.4) return "var(--bad)";
  if (v < 0.7) return "var(--warn)";
  return "var(--good)";
}

export function providerLabel(p: string): string {
  switch (p) {
    case "canvas":
      return "Canvas";
    case "google_calendar":
      return "Google Calendar";
    case "gmail":
      return "Gmail";
    case "piazza":
      return "Piazza";
    case "edstem":
      return "Ed Discussion";
    case "documents":
      return "Documents";
    default:
      return p;
  }
}

/** Compact "Tue 11:59 PM" style label. */
export function fmtShort(iso: string | null | undefined, tz: string = FALLBACK_TZ): string {
  const d = safeDate(iso);
  if (!d) return "no date";
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "short", hour: "numeric", minute: "2-digit" }).format(d);
  } catch {
    return d.toLocaleString();
  }
}

/** Compact "Tue Nov 10" style label. */
export function fmtDay(iso: string | null | undefined, tz: string = FALLBACK_TZ): string {
  const d = safeDate(iso);
  if (!d) return "no date";
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric" }).format(d);
  } catch {
    return d.toDateString();
  }
}
