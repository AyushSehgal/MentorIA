import { useState } from "react";
import { api, DEFAULT_STUDENT } from "../api/client";
import type { DashboardResponse, KnowledgeCounts, SourceRecord, Suggestion } from "../api/types";
import { ChatPanel } from "../components/ChatPanel";
import { WeekCalendar } from "../components/WeekCalendar";
import { Bar, Block, Empty, ExpandItem, Facts, MoreList } from "../components/Common";
import { fmtDay, fmtShort, pct } from "../lib/format";


function isEmpty(k: KnowledgeCounts | undefined) {
  return !k || Object.values(k).every((v) => !v);
}

export function Dashboard({
  data,
  error,
  loading,
  onRefresh,
}: {
  data: DashboardResponse | null;
  error: string | null;
  loading: boolean;
  onRefresh: () => void;
  navigate: (p: string) => void;
}) {
  const tz = data?.student.timezone ?? "America/New_York";
  const empty = data ? isEmpty(data.knowledge) : false;
  return (
    <div className="dash">
      <div className="dash-main">
        {!data && loading && <div className="card"><p className="empty">Loading…</p></div>}
        {!data && error && <div className="card"><p className="error-text">Dashboard unavailable: {error}</p></div>}
        {data && (
          <>
            {empty ? (
              <div className="card empty-hero">
                <h2>No data yet</h2>
              </div>
            ) : (
              <>
                <RecapBlock data={data} tz={tz} onRefresh={onRefresh} />
                <CalendarBlock data={data} tz={tz} onRefresh={onRefresh} />
                <div className="grid-2">
                  <AssignmentsBlock data={data} tz={tz} />
                  <OpportunitiesBlock data={data} tz={tz} />
                  <DiscussionsBlock data={data} tz={tz} />
                </div>
                <DocumentsBlock data={data} tz={tz} />
              </>
            )}
          </>
        )}
      </div>
      <aside className="dash-side">
        <ChatPanel tz={tz} onMemoryChanged={onRefresh} />
      </aside>
    </div>
  );
}

type RecapBox = { key: string; label: string; text: string; sub?: string; tone: "goal" | "focus" | "due" | "warn" };

/** Collapse many insights into at most four plain boxes: goal, focus, due soon, watch out. */
function recapBoxes(data: DashboardResponse, tz: string): RecapBox[] {
  const ins = data.insights;
  const boxes: RecapBox[] = [];
  const goal = ins.find((i) => i.kind === "goal");
  if (goal) {
    const n = goal.evidence.length;
    boxes.push({ key: "goal", label: "Your goal", text: goal.detail, sub: n > 1 ? `Stated in ${n} places` : undefined, tone: "goal" });
  }
  const focus = ins.filter((i) => i.kind === "focus_area").map((i) => i.title.replace(/^Focus #\d+: /, ""));
  if (focus.length) {
    boxes.push({ key: "focus", label: "Focus this week", text: focus.slice(0, 2).join(" · "), sub: "Weakest topics with deadlines coming up", tone: "focus" });
  }
  const due = data.cards.canvas.items
    .filter((a) => a.kind === "assignment" && !a.metadata?.completed && a.occurred_at && new Date(a.occurred_at).getTime() > Date.now())
    .sort((a, b) => (a.occurred_at ?? "").localeCompare(b.occurred_at ?? ""));
  if (due.length) {
    boxes.push({
      key: "due",
      label: "Due next",
      text: due[0].title,
      sub: `${fmtShort(due[0].occurred_at, tz)}${due.length > 1 ? ` · +${due.length - 1} more coming up` : ""}`,
      tone: "due",
    });
  }
  const blind = ins.find((i) => i.kind === "blind_spot");
  if (blind) {
    boxes.push({ key: "warn", label: "Watch out", text: blind.title.replace(/^Possible blind spot: /, ""), sub: "You feel more confident than your graded work shows", tone: "warn" });
  }
  return boxes.slice(0, 4);
}

const SUGGESTION_ICON: Record<Suggestion["kind"], string> = { event: "✉️", reading: "📄", resource: "💬", study: "📖" };

function SuggestionBox({ s, tz, onRefresh }: { s: Suggestion; tz: string; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const rec = s.recommendation;
  async function approve() {
    if (!rec) return;
    setBusy(true);
    try {
      const r = await api.approve(rec.id, {
        student_id: DEFAULT_STUDENT,
        confirm: { title: rec.title, suggested_start: rec.suggested_start, duration_minutes: rec.duration_minutes },
      });
      setDone(r.simulated ? "✓ Added to your plan (calendar not connected, nothing written)" : "✓ Added to your calendar");
      setTimeout(onRefresh, 2200); // let the confirmation show before the box leaves
    } catch (e) {
      setDone((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function reject() {
    setBusy(true);
    try {
      if (rec) await api.reject(rec.id);
      else await api.dismissSuggestion(s.id);
      setDone("Dismissed");
      setTimeout(onRefresh, 1200);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className={`recap-box sugg sugg-${s.kind}`}>
      <div className="recap-label">
        <span aria-hidden>{SUGGESTION_ICON[s.kind]}</span> {s.source_label}
      </div>
      <div className="recap-text">{s.title}</div>
      <div className="recap-sub">
        {s.when ? `${fmtShort(s.when, tz)} · ` : ""}
        {s.why}
      </div>
      {done ? (
        <div className="sugg-done">{done}</div>
      ) : (
        <div className="sugg-actions">
          {rec ? (
            <button className="btn small-btn primary" disabled={busy} onClick={() => void approve()}>
              {s.kind === "event" ? "Add to calendar" : "Approve"}
            </button>
          ) : (
            s.url && (
              <a className="btn small-btn primary" href={s.url} target="_blank" rel="noreferrer">
                {s.kind === "reading" ? "Open paper" : "Open"}
              </a>
            )
          )}
          <button className="btn small-btn" disabled={busy} onClick={() => void reject()}>
            {rec ? "Not now" : "Dismiss"}
          </button>
        </div>
      )}
    </div>
  );
}

function RecapBlock({ data, tz, onRefresh }: { data: DashboardResponse; tz: string; onRefresh: () => void }) {
  const [open, setOpen] = useState(false);
  const boxes = recapBoxes(data, tz);
  const sugg = data.suggestions ?? [];
  if (!boxes.length && !sugg.length) return null;
  return (
    <section className="recap">
      <button className={`btn recap-btn ${open ? "" : "primary"}`} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? "Hide recap" : "Quick Recap"}
        {!open && sugg.length > 0 && <span className="recap-count">{sugg.length} suggestions</span>}
      </button>
      {open && (
        <>
          {boxes.length > 0 && (
            <div className="recap-section">
              <h3 className="recap-heading">At a glance</h3>
              <div className="recap-grid">
                {boxes.map((b) => (
                  <div key={b.key} className={`recap-box tone-${b.tone}`}>
                    <div className="recap-label">{b.label}</div>
                    <div className="recap-text">{b.text}</div>
                    {b.sub && <div className="recap-sub">{b.sub}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {sugg.length > 0 && (
            <div className="recap-section">
              <h3 className="recap-heading">Suggested for you</h3>
              <div className="recap-grid">
                {sugg.map((sg) => (
                  <SuggestionBox key={sg.id} s={sg} tz={tz} onRefresh={onRefresh} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function AssignmentsBlock({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.canvas;
  const items = [...card.items].sort((a, b) => {
    const ca = a.metadata?.completed ? 1 : 0;
    const cb = b.metadata?.completed ? 1 : 0;
    if (ca !== cb) return ca - cb;
    return (a.occurred_at ?? "9999").localeCompare(b.occurred_at ?? "9999");
  });
  return (
    <Block icon="📚" title="Assignments" status={card.status}>
      {items.length === 0 ? (
        <Empty>No assignments yet</Empty>
      ) : (
        <MoreList
          className="xitems"
          items={items}
          render={(r) => {
            const done = !!r.metadata?.completed;
            const dueMs = r.occurred_at ? new Date(r.occurred_at).getTime() - Date.now() : null;
            const urgent = !done && dueMs !== null && dueMs >= 0 && dueMs < 3 * 864e5;
            return (
              <ExpandItem key={r.id} title={r.title} done={done} badge={urgent ? "soon" : done ? "✓" : undefined}>
                <Facts
                  rows={[
                    ["Course", courseShort(r)],
                    ["Due", done ? "Submitted" : fmtShort(r.occurred_at, tz)],
                    ["Points", r.metadata?.points_possible ? String(r.metadata.points_possible) : null],
                  ]}
                />
                {r.body && <p className="small">{r.body}</p>}
                {r.source_url && (
                  <a className="small" href={r.source_url} target="_blank" rel="noreferrer">
                    Open in Canvas ↗
                  </a>
                )}
              </ExpandItem>
            );
          }}
        />
      )}
    </Block>
  );
}

function courseShort(r: SourceRecord): string {
  const name = String(r.metadata?.course_name ?? r.course_id ?? "");
  const code = name.match(/\d{2}-\d{3}/);
  return code ? code[0] : name || "—";
}

function CalendarBlock({ data, tz, onRefresh }: { data: DashboardResponse; tz: string; onRefresh: () => void }) {
  const card = data.cards.google_calendar;
  const deadlines = data.cards.canvas.items.filter((a) => a.kind === "assignment" && !a.metadata?.completed);
  const [open, setOpen] = useState(false);
  const days = Array.from({ length: 7 }, (_, i) => {
    const iso = new Date(Date.now() + i * 864e5).toISOString();
    const key = fmtDay(iso, tz);
    return {
      key,
      label: key,
      events: card.items.filter((e) => fmtDay(e.occurred_at, tz) === key).length,
      due: deadlines.filter((d) => fmtDay(d.occurred_at, tz) === key).length,
    };
  });
  const empty = card.items.length === 0 && deadlines.length === 0;
  return (
    <Block
      icon="📅"
      title="Calendar"
      status={card.status}
      className="block-wide"
      actions={
        !empty && (
          <button className="btn small-btn" onClick={() => setOpen((o) => !o)}>
            {open ? "Close" : "Open calendar"}
          </button>
        )
      }
    >
      {empty ? (
        <Empty>No events yet</Empty>
      ) : open ? (
        <WeekCalendar events={card.items} deadlines={deadlines} freeWindows={card.free_windows} tz={tz} onChanged={onRefresh} />
      ) : (
        <div className="week-strip">
          {days.map((d, i) => (
            <button key={d.key} className={`strip-day ${i === 0 ? "today" : ""}`} onClick={() => setOpen(true)} title="Open calendar">
              <span className="strip-label">{i === 0 ? "Today" : d.label.split(",")[0]}</span>
              <span className="strip-count">{d.events || "–"}</span>
              <span className="strip-sub">{d.events === 1 ? "event" : "events"}</span>
              {d.due > 0 && <span className="strip-due">⏰ {d.due} due</span>}
            </button>
          ))}
        </div>
      )}
    </Block>
  );
}

function OpportunitiesBlock({ data }: { data: DashboardResponse; tz?: string }) {
  const card = data.cards.gmail;
  const opps = [...card.opportunities].sort((a, b) => b.relevance_score - a.relevance_score);
  return (
    <Block icon="✉️" title="Opportunities" status={card.status}>
      {opps.length === 0 ? (
        <Empty>No emails yet</Empty>
      ) : (
        <MoreList
          className="xitems"
          items={opps}
          render={(o) => (
            <ExpandItem key={o.record.id} title={o.record.title} badge={o.relevance_score >= 0.5 ? "★ match" : undefined}>
              <Facts
                rows={[
                  ["When", o.timing_label],
                  ["Speaker", o.speaker],
                  ["Where", o.venue],
                  ["Match", <><Bar value={o.relevance_score} /> {pct(o.relevance_score)}</>],
                ]}
              />
              <ul className="why-list">
                {o.relevance_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              {o.url && (
                <a className="small" href={o.url} target="_blank" rel="noreferrer">
                  Event link ↗
                </a>
              )}
            </ExpandItem>
          )}
        />
      )}
    </Block>
  );
}

function DiscussionsBlock({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.piazza;
  const items = [...card.items].sort((a, b) => {
    const ia = a.metadata?.is_instructor ? 0 : 1;
    const ib = b.metadata?.is_instructor ? 0 : 1;
    if (ia !== ib) return ia - ib;
    return (b.occurred_at ?? "").localeCompare(a.occurred_at ?? "");
  });
  return (
    <Block icon="💬" title="Discussions" status={card.status}>
      {items.length === 0 ? (
        <Empty>No discussions yet</Empty>
      ) : (
        <MoreList
          className="xitems"
          items={items}
          render={(r) => (
            <ExpandItem key={r.id} title={r.title} badge={r.metadata?.is_instructor ? "Instructor" : undefined}>
              <Facts rows={[["Course", courseShort(r)], ["Posted", fmtDay(r.occurred_at, tz)]]} />
              {r.body && <p className="small">{r.body}</p>}
              {r.source_url && (
                <a className="small" href={r.source_url} target="_blank" rel="noreferrer">
                  Open in Piazza ↗
                </a>
              )}
            </ExpandItem>
          )}
        />
      )}
    </Block>
  );
}

function DocumentsBlock({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.documents;
  return (
    <Block
      icon="📄"
      title="Documents"
      status={card.status}
    >
      {card.documents.length === 0 ? (
        <Empty>No documents yet</Empty>
      ) : (
        <MoreList
          className="xitems"
          items={card.documents}
          render={(d) => (
            <ExpandItem
              key={d.id}
              title={d.title || d.filename}
              badge={d.status === "failed" ? "failed" : d.kind === "graded_assessment" ? "graded" : undefined}
            >
              <Facts
                rows={[
                  ["Type", d.kind === "graded_assessment" ? "Graded work" : "Study material"],
                  ["Pages", String(d.page_count)],
                  ["Evidence", d.kind === "graded_assessment" ? `${d.observations_created} answers${d.pending_review ? `, ${d.pending_review} to review` : ""}` : null],
                  ["Added", fmtDay(d.uploaded_at, tz)],
                ]}
              />
              {d.error && <p className="error-text small">{d.error}</p>}
              <a className="small" href={d.file_url} target="_blank" rel="noreferrer">
                Open PDF ↗
              </a>
            </ExpandItem>
          )}
        />
      )}
    </Block>
  );
}
