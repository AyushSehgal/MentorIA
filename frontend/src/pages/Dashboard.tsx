import type { DashboardResponse, Insight, SourceRecord } from "../api/types";
import { ApprovalCard } from "../components/ApprovalCard";
import { ChatPanel } from "../components/ChatPanel";
import { Bar, Card, EvidenceChips, Empty } from "../components/Common";
import { dayKey, fmtDateTime, fmtTime, pct, relative } from "../lib/format";

const anyFixture = (items: { is_fixture: boolean }[]) => items.some((i) => i.is_fixture);

const insightIcon: Record<Insight["kind"], string> = {
  focus_area: "🎯",
  blind_spot: "⚠️",
  deadline: "⏰",
  stale_evidence: "🕰️",
  opportunity: "✨",
  missing_evidence: "❔",
};

export function Dashboard({
  data,
  error,
  loading,
  onRefresh,
  navigate,
}: {
  data: DashboardResponse | null;
  error: string | null;
  loading: boolean;
  onRefresh: () => void;
  navigate: (p: string) => void;
}) {
  const tz = data?.student.timezone ?? "America/New_York";
  return (
    <div className="dash">
      <div className="dash-main">
        {!data && loading && <div className="card"><p className="empty">Loading dashboard…</p></div>}
        {!data && error && (
          <div className="card">
            <p className="error-text">Dashboard unavailable: {error}</p>
            <p className="muted">The chat panel and other pages may still work once the backend is up.</p>
          </div>
        )}
        {data && (
          <>
            <InsightsCard data={data} tz={tz} onRefresh={onRefresh} />
            <div className="grid-2">
              <CanvasCard data={data} tz={tz} />
              <CalendarCard data={data} tz={tz} />
              <GmailCard data={data} tz={tz} />
              <PiazzaCard data={data} tz={tz} />
            </div>
            <DocumentsCard data={data} tz={tz} navigate={navigate} />
          </>
        )}
      </div>
      <aside className="dash-side">
        <ChatPanel tz={tz} onMemoryChanged={onRefresh} />
      </aside>
    </div>
  );
}

function InsightsCard({ data, tz, onRefresh }: { data: DashboardResponse; tz: string; onRefresh: () => void }) {
  return (
    <Card title="NOVA Insights & Priorities" className="insights">
      {data.insights.length === 0 && data.recommendations.length === 0 && (
        <Empty>No insights yet — sync sources or upload a graded quiz to build your student model.</Empty>
      )}
      {data.insights.length > 0 && (
        <ul className="insight-list">
          {data.insights.map((ins) => (
            <li key={ins.id} className={`insight insight-${ins.kind}`}>
              <div className="insight-title">
                <span aria-hidden>{insightIcon[ins.kind] ?? "•"}</span> {ins.title}
              </div>
              <div className="insight-detail">{ins.detail}</div>
              {ins.confidence_note && <div className="muted small">{ins.confidence_note}</div>}
              <EvidenceChips evidence={ins.evidence} />
            </li>
          ))}
        </ul>
      )}
      {data.recommendations.length > 0 && (
        <div className="rec-list">
          <h3 className="section-label">Awaiting your approval</h3>
          {data.recommendations.map((r) => (
            <ApprovalCard key={r.id} rec={r} tz={tz} onChanged={onRefresh} />
          ))}
        </div>
      )}
    </Card>
  );
}

function SourceLink({ r }: { r: SourceRecord }) {
  if (!r.source_url) return null;
  return (
    <a className="src-link" href={r.source_url} target="_blank" rel="noreferrer">
      open ↗
    </a>
  );
}

function CanvasCard({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.canvas;
  const items = [...card.items].sort((a, b) => {
    const ca = a.metadata?.completed ? 1 : 0;
    const cb = b.metadata?.completed ? 1 : 0;
    if (ca !== cb) return ca - cb;
    const ta = a.occurred_at ? new Date(a.occurred_at).getTime() : Infinity;
    const tb = b.occurred_at ? new Date(b.occurred_at).getTime() : Infinity;
    return ta - tb;
  });
  return (
    <Card title="Canvas — Due Soon" status={card.status} demo={card.status.state === "demo_data" || anyFixture(items)}>
      {items.length === 0 ? (
        <Empty>No assignments.</Empty>
      ) : (
        <ul className="rows">
          {items.map((r) => {
            const done = !!r.metadata?.completed;
            const dueMs = r.occurred_at ? new Date(r.occurred_at).getTime() - Date.now() : null;
            const urgent = !done && dueMs !== null && dueMs >= 0 && dueMs < 3 * 864e5;
            const overdue = !done && dueMs !== null && dueMs < 0;
            return (
              <li key={r.id} className={`row ${done ? "done" : ""}`}>
                <div className="row-main">
                  <span className="row-title">
                    {done ? "✓ " : ""}
                    {r.title}
                  </span>
                  <span className="muted small">{String(r.metadata?.course_name ?? r.course_id ?? "")}</span>
                </div>
                <div className="row-side">
                  <span className={`pill ${overdue ? "pill-bad" : urgent ? "pill-warn" : ""}`}>
                    {done ? "completed" : r.occurred_at ? `due ${relative(r.occurred_at)}` : "no due date"}
                  </span>
                  <span className="muted small">{fmtDateTime(r.occurred_at, tz)}</span>
                  <SourceLink r={r} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function CalendarCard({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.google_calendar;
  const groups = new Map<string, SourceRecord[]>();
  [...card.items]
    .sort((a, b) => (a.occurred_at ?? "").localeCompare(b.occurred_at ?? ""))
    .forEach((r) => {
      const k = dayKey(r.occurred_at, tz);
      groups.set(k, [...(groups.get(k) ?? []), r]);
    });
  return (
    <Card
      title="Google Calendar — This Week"
      status={card.status}
      demo={card.status.state === "demo_data" || anyFixture(card.items)}
    >
      {card.items.length === 0 ? (
        <Empty>No events this week.</Empty>
      ) : (
        <div className="cal">
          {[...groups.entries()].map(([day, evs]) => (
            <div key={day} className="cal-day">
              <div className="cal-day-label">{day}</div>
              <ul>
                {evs.map((e) => (
                  <li key={e.id}>
                    <span className="cal-time">
                      {fmtTime(e.occurred_at, tz)}
                      {typeof e.metadata?.end === "string" ? `–${fmtTime(e.metadata.end as string, tz)}` : ""}
                    </span>{" "}
                    {e.title}
                    {e.metadata?.created_by_nova ? <span className="pill pill-good">NOVA</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
      <h3 className="section-label">Free windows (candidate study blocks)</h3>
      {card.free_windows.length === 0 ? (
        <Empty>No free windows computed.</Empty>
      ) : (
        <ul className="windows">
          {card.free_windows.slice(0, 8).map((w, i) => (
            <li key={i}>
              <span className="window-bar" style={{ width: `${Math.min(100, (w.minutes / 240) * 100)}%` }} />
              <span>
                {fmtDateTime(w.start, tz)} – {fmtTime(w.end, tz)} · {w.minutes} min
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function GmailCard({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.gmail;
  const opps = [...card.opportunities].sort((a, b) => b.relevance_score - a.relevance_score);
  const recIds = new Set(data.recommendations.map((r) => r.id));
  return (
    <Card
      title="Gmail — Academic Opportunities"
      status={card.status}
      demo={card.status.state === "demo_data" || anyFixture(card.items)}
    >
      {opps.length === 0 ? (
        <Empty>No relevant academic announcements found.</Empty>
      ) : (
        <ul className="opps">
          {opps.map((o) => (
            <li key={o.record.id} className="opp">
              <div className="opp-head">
                <span className="row-title">{o.record.title}</span>
                <SourceLink r={o.record} />
              </div>
              <div className="opp-score">
                <Bar value={o.relevance_score} />
                <span className="small">relevance {pct(o.relevance_score)}</span>
              </div>
              <div className={`opp-timing ${o.event_start ? "" : "undated"}`}>
                {o.event_start ? `📅 ${o.timing_label}` : `🔎 ${o.timing_label}`}
              </div>
              <div className="muted small">
                {o.speaker && <>Speaker: {o.speaker} · </>}
                {o.venue && <>Venue: {o.venue} · </>}
                {o.url && (
                  <a href={o.url} target="_blank" rel="noreferrer">
                    link
                  </a>
                )}
                {o.record.occurred_at && <> · received {fmtDateTime(o.record.occurred_at, tz)}</>}
              </div>
              {o.relevance_reasons.length > 0 && (
                <ul className="reasons">
                  {o.relevance_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
              {o.recommendation_id && (
                <div className="small">
                  {recIds.has(o.recommendation_id)
                    ? "→ Calendar proposal awaiting approval in Insights"
                    : "→ Proposal already handled"}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function PiazzaCard({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.piazza;
  const items = [...card.items].sort((a, b) => {
    const ia = a.metadata?.is_instructor ? 0 : 1;
    const ib = b.metadata?.is_instructor ? 0 : 1;
    if (ia !== ib) return ia - ib;
    return (b.occurred_at ?? "").localeCompare(a.occurred_at ?? "");
  });
  return (
    <Card title="Piazza — Course Discussions" status={card.status} demo={card.status.state === "demo_data" || anyFixture(items)}>
      {items.length === 0 ? (
        <Empty>{card.status.state === "not_available" ? "Piazza is not connected." : "No discussions."}</Empty>
      ) : (
        <ul className="rows">
          {items.map((r) => (
            <li key={r.id} className="row">
              <div className="row-main">
                <span className="row-title">
                  {r.metadata?.is_instructor ? <span className="pill pill-accent">Instructor</span> : null} {r.title}
                </span>
                <span className="muted small clamp">{r.body}</span>
              </div>
              <div className="row-side">
                <span className="muted small">{String(r.metadata?.course_name ?? r.course_id ?? "")}</span>
                <span className="muted small">{fmtDateTime(r.occurred_at, tz)}</span>
                <SourceLink r={r} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DocumentsCard({ data, tz, navigate }: { data: DashboardResponse; tz: string; navigate: (p: string) => void }) {
  const card = data.cards.documents;
  return (
    <Card
      title="Documents — Academic Sources"
      status={card.status}
      demo={anyFixture(card.documents)}
      actions={
        <button className="btn small-btn" onClick={() => navigate("/documents")}>
          Upload
        </button>
      }
    >
      {card.documents.length === 0 ? (
        <Empty>No documents yet. Upload a graded quiz or load the demo quiz from the Documents page.</Empty>
      ) : (
        <ul className="rows">
          {card.documents.map((d) => (
            <li key={d.id} className="row">
              <div className="row-main">
                <span className="row-title">{d.title || d.filename}</span>
                <span className="muted small">
                  {d.kind === "graded_assessment" ? "Graded assessment" : "Study material"} · {d.page_count} pages ·{" "}
                  {d.course_id ?? "no course"} · {d.observations_created} observations
                  {d.pending_review > 0 && ` · ${d.pending_review} pending review`}
                </span>
              </div>
              <div className="row-side">
                <span className={`pill ${d.status === "failed" ? "pill-bad" : "pill-good"}`}>{d.status}</span>
                <span className="muted small">{fmtDateTime(d.uploaded_at, tz)}</span>
                <a className="src-link" href={d.file_url} target="_blank" rel="noreferrer">
                  PDF ↗
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
