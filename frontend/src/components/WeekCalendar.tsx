import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { FreeWindow, Recommendation, SourceRecord } from "../api/types";
import { fmtTime } from "../lib/format";
import { ApprovalCard } from "./ApprovalCard";
import { SampleTag } from "./Common";

/* An interactive week (or, on narrow screens, day) calendar:
   events as time blocks, free slots shaded, deadlines in day headers,
   proposed study blocks (dashed, click to approve/reject) and approved ones (solid). */

const HOUR_PX = 44;
const DAY_MS = 86_400_000;

type Selected =
  | { kind: "event"; rec: SourceRecord }
  | { kind: "free"; win: FreeWindow }
  | { kind: "rec"; rec: Recommendation }
  | { kind: "deadline"; rec: SourceRecord };

interface Placed<T> {
  item: T;
  day: string;
  startMin: number;
  endMin: number;
  lane: number;
  lanes: number;
}

/** Calendar parts of an instant in the student's timezone. */
function parts(iso: string | null | undefined, tz: string): { day: string; min: number } | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(d)
      .map((x) => [x.type, x.value]),
  );
  return { day: `${p.year}-${p.month}-${p.day}`, min: Number(p.hour) * 60 + Number(p.minute) };
}

function dayLabel(dayKey: string): { dow: string; date: string } {
  const d = new Date(`${dayKey}T12:00:00Z`);
  return {
    dow: new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: "UTC" }).format(d),
    date: new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" }).format(d),
  };
}

function hourLabel(h: number): string {
  const ampm = h < 12 || h === 24 ? "am" : "pm";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}${ampm}`;
}

/** Assign side-by-side lanes to overlapping blocks within one day. */
function layout<T>(items: { item: T; day: string; startMin: number; endMin: number }[]): Placed<T>[] {
  const out: Placed<T>[] = [];
  const byDay = new Map<string, typeof items>();
  items.forEach((i) => byDay.set(i.day, [...(byDay.get(i.day) ?? []), i]));
  byDay.forEach((list) => {
    list.sort((a, b) => a.startMin - b.startMin || b.endMin - a.endMin);
    let cluster: Placed<T>[] = [];
    let clusterEnd = -1;
    const flush = () => {
      const lanes = Math.max(1, ...cluster.map((c) => c.lane + 1));
      cluster.forEach((c) => (c.lanes = lanes));
      out.push(...cluster);
      cluster = [];
    };
    list.forEach((i) => {
      if (i.startMin >= clusterEnd && cluster.length) flush();
      const used = new Set(cluster.filter((c) => c.endMin > i.startMin).map((c) => c.lane));
      let lane = 0;
      while (used.has(lane)) lane++;
      cluster.push({ ...i, lane, lanes: 1 });
      clusterEnd = Math.max(clusterEnd, i.endMin);
    });
    if (cluster.length) flush();
  });
  return out;
}

const COURSE_COLORS = ["#4f46e5", "#0891b2", "#c2410c", "#15803d", "#a21caf", "#b45309"];
export function courseColor(courseId: string | null): string {
  if (!courseId) return "#64748b";
  let h = 0;
  for (const ch of courseId) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return COURSE_COLORS[h % COURSE_COLORS.length];
}

export function WeekCalendar({
  events,
  deadlines,
  freeWindows,
  tz,
  onChanged,
}: {
  events: SourceRecord[];
  deadlines: SourceRecord[];
  freeWindows: FreeWindow[];
  tz: string;
  onChanged: () => void;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);
  const [offset, setOffset] = useState(0); // days from today
  const [showFree, setShowFree] = useState(true);
  const [selected, setSelected] = useState<Selected | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [planning, setPlanning] = useState(false);
  const [planNote, setPlanNote] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());

  // All recommendations (pending + approved) so approved study blocks stay visible on the calendar.
  const loadRecs = () =>
    api
      .recommendations()
      .then(setRecs)
      .catch(() => undefined);
  useEffect(() => {
    void loadRecs();
  }, [events, deadlines, freeWindows]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setNarrow(e.contentRect.width < 620));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);

  const nDays = narrow ? 1 : 7;
  const days = useMemo(() => {
    const out: string[] = [];
    for (let i = 0; i < nDays; i++) {
      const p = parts(new Date(now + (offset + i) * DAY_MS).toISOString(), tz);
      if (p && !out.includes(p.day)) out.push(p.day);
    }
    return out;
  }, [now, offset, nDays, tz]);
  const todayKey = parts(new Date(now).toISOString(), tz)?.day;
  const nowMin = parts(new Date(now).toISOString(), tz)?.min ?? 0;

  const visibleRecs = recs.filter(
    (r) => r.suggested_start && r.duration_minutes && ["pending", "approved", "executed", "executed_simulated"].includes(r.status),
  );

  // Hour range: 8am–10pm, widened to fit anything outside it.
  const [startH, endH] = useMemo(() => {
    let lo = 8,
      hi = 22;
    const consider = (iso: string | null | undefined, endIso?: string | null) => {
      const s = parts(iso, tz);
      const e = parts(endIso ?? iso, tz);
      if (s && days.includes(s.day)) lo = Math.min(lo, Math.floor(s.min / 60));
      if (e && days.includes(e.day)) hi = Math.max(hi, Math.ceil(e.min / 60));
    };
    events.forEach((e) => consider(e.occurred_at, e.metadata?.end as string));
    visibleRecs.forEach((r) => consider(r.suggested_start, new Date(new Date(r.suggested_start!).getTime() + r.duration_minutes! * 6e4).toISOString()));
    return [Math.max(0, lo), Math.min(24, hi)];
  }, [events, visibleRecs, days, tz]);

  const toY = (min: number) => ((min - startH * 60) / 60) * HOUR_PX;

  type GridItem = { kind: "event"; rec: SourceRecord } | { kind: "rec"; rec: Recommendation };
  const gridItems: { item: GridItem; day: string; startMin: number; endMin: number }[] = [];
  events
    .filter((e) => !e.metadata?.all_day)
    .forEach((e) => {
      const s = parts(e.occurred_at, tz);
      const en = parts((e.metadata?.end as string) ?? e.occurred_at, tz);
      if (!s) return;
      const endMin = en && en.day === s.day ? Math.max(en.min, s.min + 20) : s.min + 60;
      gridItems.push({ item: { kind: "event", rec: e }, day: s.day, startMin: s.min, endMin });
    });
  visibleRecs.forEach((r) => {
    const s = parts(r.suggested_start, tz);
    if (s) gridItems.push({ item: { kind: "rec", rec: r }, day: s.day, startMin: s.min, endMin: s.min + (r.duration_minutes ?? 50) });
  });
  const placedEvents = layout<GridItem>(gridItems);

  const freeByDay = freeWindows
    .map((w) => {
      const s = parts(w.start, tz);
      const e = parts(w.end, tz);
      return s && e ? { win: w, day: s.day, startMin: s.min, endMin: e.day === s.day ? e.min : 24 * 60 } : null;
    })
    .filter((x): x is NonNullable<typeof x> => !!x);

  const deadlinesByDay = new Map<string, SourceRecord[]>();
  deadlines.forEach((d) => {
    const p = parts(d.occurred_at, tz);
    if (p) deadlinesByDay.set(p.day, [...(deadlinesByDay.get(p.day) ?? []), d]);
  });

  // Scroll so the morning is visible.
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = Math.max(0, toY(8 * 60) - 4);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startH]);

  async function planWeek() {
    setPlanning(true);
    setPlanNote(null);
    try {
      const r = await api.chat({ message: "What should I focus on this week?", student_id: "demo_student", mode: "ask" });
      const n = r.proposed_recommendations.filter((x) => x.type === "study_session").length;
      setPlanNote(n ? `${n} study block${n > 1 ? "s" : ""} proposed — click a dashed block to approve` : "No study blocks to propose yet");
      await loadRecs();
      onChanged();
    } catch (e) {
      setPlanNote((e as Error).message);
    } finally {
      setPlanning(false);
    }
  }

  const step = narrow ? 1 : 7;
  const rangeLabel =
    days.length === 1
      ? `${dayLabel(days[0]).dow}, ${dayLabel(days[0]).date}`
      : `${dayLabel(days[0]).date} – ${dayLabel(days[days.length - 1]).date}`;

  return (
    <div className="wcal" ref={wrapRef}>
      <div className="wcal-toolbar">
        <div className="wcal-nav">
          <button className="btn small-btn" onClick={() => setOffset(0)} disabled={offset === 0}>
            Today
          </button>
          <button className="btn small-btn icon-btn" aria-label="Previous" onClick={() => setOffset((o) => o - step)}>
            ‹
          </button>
          <button className="btn small-btn icon-btn" aria-label="Next" onClick={() => setOffset((o) => o + step)}>
            ›
          </button>
          <strong className="wcal-range">{rangeLabel}</strong>
        </div>
        <div className="wcal-actions">
          <label className="wcal-toggle">
            <input type="checkbox" checked={showFree} onChange={(e) => setShowFree(e.target.checked)} /> Free time
          </label>
          <button className="btn small-btn primary" onClick={() => void planWeek()} disabled={planning}>
            {planning ? "Planning…" : "✨ Plan my week"}
          </button>
        </div>
      </div>
      {planNote && <div className="wcal-note">{planNote}</div>}

      <div className="wcal-head" style={{ gridTemplateColumns: `48px repeat(${days.length}, 1fr)` }}>
        <div />
        {days.map((d) => {
          const l = dayLabel(d);
          const dls = deadlinesByDay.get(d) ?? [];
          return (
            <div key={d} className={`wcal-dayhead ${d === todayKey ? "today" : ""}`}>
              <div className="wcal-dow">{l.dow}</div>
              <div className="wcal-date">{l.date}</div>
              {dls.map((dl) => (
                <button
                  key={dl.id}
                  className="wcal-deadline"
                  title={`${dl.title} — due ${fmtTime(dl.occurred_at, tz)}`}
                  onClick={() => setSelected({ kind: "deadline", rec: dl })}
                >
                  ⏰ {dl.title.split(":")[0]}
                </button>
              ))}
            </div>
          );
        })}
      </div>

      <div className="wcal-scroll" ref={scrollRef}>
        <div
          className="wcal-grid"
          style={{ gridTemplateColumns: `48px repeat(${days.length}, 1fr)`, height: (endH - startH) * HOUR_PX }}
        >
          <div className="wcal-hours">
            {Array.from({ length: endH - startH }, (_, i) => (
              <div key={i} className="wcal-hour" style={{ top: i * HOUR_PX }}>
                {hourLabel(startH + i)}
              </div>
            ))}
          </div>
          {days.map((d) => (
            <div key={d} className={`wcal-col ${d === todayKey ? "today" : ""}`}>
              {Array.from({ length: endH - startH }, (_, i) => (
                <div key={i} className="wcal-line" style={{ top: i * HOUR_PX }} />
              ))}
              {showFree &&
                freeByDay
                  .filter((f) => f.day === d)
                  .map((f, i) => (
                    <button
                      key={`f${i}`}
                      className="wcal-free"
                      style={{ top: toY(f.startMin), height: toY(f.endMin) - toY(f.startMin) }}
                      title={`Free ${fmtTime(f.win.start, tz)}–${fmtTime(f.win.end, tz)}`}
                      onClick={() => setSelected({ kind: "free", win: f.win })}
                      aria-label={`Free ${fmtTime(f.win.start, tz)} to ${fmtTime(f.win.end, tz)}`}
                    />
                  ))}
              {placedEvents
                .filter((p) => p.day === d)
                .map((p) => {
                  const top = toY(p.startMin);
                  const height = Math.max(18, toY(p.endMin) - top - 2);
                  const width = `calc(${100 / p.lanes}% - 4px)`;
                  const left = `calc(${(100 / p.lanes) * p.lane}% + 2px)`;
                  if (p.item.kind === "event") {
                    const e = p.item.rec;
                    const color = courseColor(e.course_id);
                    return (
                      <button
                        key={e.id}
                        className={`wcal-ev ${e.is_fixture ? "is-sample" : ""}`}
                        style={{ top, height, width, left, borderLeftColor: color, background: `${color}1a` }}
                        onClick={() => setSelected({ kind: "event", rec: e })}
                        title={`${fmtTime(e.occurred_at, tz)}–${fmtTime(e.metadata?.end as string, tz)} ${e.title}${e.is_fixture ? " · sample data" : ""}`}
                      >
                        <span className="wcal-ev-time">{fmtTime(e.occurred_at, tz)}</span>
                        <span className="wcal-ev-title">{e.title}</span>
                      </button>
                    );
                  }
                  const r = p.item.rec;
                  const planned = r.status !== "pending";
                  return (
                    <button
                      key={r.id}
                      className={`wcal-rec ${planned ? "planned" : "proposed"}`}
                      style={{ top, height, width, left }}
                      onClick={() => setSelected({ kind: "rec", rec: r })}
                      title={`${planned ? "Planned" : "Proposed"}: ${r.title}`}
                    >
                      <span className="wcal-ev-time">
                        {planned ? "✓ " : "＋ "}
                        {fmtTime(r.suggested_start, tz)}
                      </span>
                      <span className="wcal-ev-title">{r.title.replace(/^Study: /, "")}</span>
                    </button>
                  );
                })}
              {d === todayKey && nowMin >= startH * 60 && nowMin <= endH * 60 && (
                <div className="wcal-now" style={{ top: toY(nowMin) }} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="wcal-legend">
        <span><i className="lg lg-ev" /> Event</span>
        <span><i className="lg lg-free" /> Free</span>
        <span><i className="lg lg-prop" /> Proposed</span>
        <span><i className="lg lg-plan" /> Planned</span>
        <span>⏰ Due</span>
      </div>

      {selected && (
        <div className="wcal-detail">
          <button className="wcal-close" aria-label="Close" onClick={() => setSelected(null)}>
            ×
          </button>
          {selected.kind === "event" && (
            <>
              <strong>{selected.rec.title}</strong> <SampleTag show={selected.rec.is_fixture} />
              <div className="muted small">
                {fmtTime(selected.rec.occurred_at, tz)}–{fmtTime(selected.rec.metadata?.end as string, tz)}
                {selected.rec.metadata?.location ? ` · ${String(selected.rec.metadata.location)}` : ""}
              </div>
            </>
          )}
          {selected.kind === "deadline" && (
            <>
              <strong>⏰ {selected.rec.title}</strong>
              <div className="muted small">
                Due {fmtTime(selected.rec.occurred_at, tz)} · {String(selected.rec.metadata?.course_name ?? selected.rec.course_id ?? "")}
              </div>
            </>
          )}
          {selected.kind === "free" && (
            <>
              <strong>Free {fmtTime(selected.win.start, tz)}–{fmtTime(selected.win.end, tz)}</strong>
              <div className="muted small">{Math.round(selected.win.minutes / 6) / 10} h open.</div>
              <button className="btn small-btn primary" onClick={() => void planWeek()} disabled={planning}>
                {planning ? "Planning…" : "✨ Suggest study blocks"}
              </button>
            </>
          )}
          {selected.kind === "rec" && (
            <ApprovalCard
              key={selected.rec.id + selected.rec.status}
              rec={selected.rec}
              tz={tz}
              compact
              onChanged={() => {
                void loadRecs();
                onChanged();
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
