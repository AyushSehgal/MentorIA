import { useEffect, useRef, useState } from "react";
import type { DashboardResponse, Insight, KnowledgeCounts, SourceRecord } from "../api/types";
import { ApprovalCard } from "../components/ApprovalCard";
import { ChatPanel } from "../components/ChatPanel";
import { WeekCalendar } from "../components/WeekCalendar";
import { Bar, Block, Empty, EvidenceChips, ExpandItem, Facts, MoreList } from "../components/Common";
import { fmtDay, fmtShort, pct } from "../lib/format";

const anyFixture = (items: { is_fixture: boolean }[]) => items.some((i) => i.is_fixture);

const insightIcon: Record<Insight["kind"], string> = {
  focus_area: "🎯",
  blind_spot: "⚠️",
  deadline: "⏰",
  stale_evidence: "🕰️",
  opportunity: "✨",
  missing_evidence: "❔",
  goal: "🧭",
};

const KSTATS: { key: keyof KnowledgeCounts; label: string }[] = [
  { key: "courses", label: "Courses" },
  { key: "concepts", label: "Concepts" },
  { key: "documents", label: "Docs" },
  { key: "graded_answers", label: "Graded" },
  { key: "goals", label: "Goals" },
  { key: "source_items", label: "Items" },
];

function isEmpty(k: KnowledgeCounts | undefined) {
  return !k || Object.values(k).every((v) => !v);
}

function KnowledgeBar({ k }: { k: KnowledgeCounts }) {
  const prev = useRef<KnowledgeCounts | null>(null);
  const [grew, setGrew] = useState<Set<string>>(new Set());
  useEffect(() => {
    const p = prev.current;
    prev.current = k;
    if (!p) return;
    setGrew(new Set(KSTATS.filter((s) => (k[s.key] ?? 0) > (p[s.key] ?? 0)).map((s) => s.key as string)));
    const t = setTimeout(() => setGrew(new Set()), 2500);
    return () => clearTimeout(t);
  }, [k]);
  return (
    <div className="knowledge-bar" aria-label="What MentorIA knows">
      {KSTATS.map((s) => {
        const v = k[s.key] ?? 0;
        const tip = s.key === "goals" && k.goal_sources ? `${k.goal_sources} sources back these goals` : undefined;
        return (
          <div key={s.key} className={`kstat ${v ? "" : "zero"} ${grew.has(s.key) ? "grew" : ""}`} title={tip}>
            <div className="kval">{v}</div>
            <div className="klabel">{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}

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
  const empty = data ? isEmpty(data.knowledge) : false;
  return (
    <div className="dash">
      <div className="dash-main">
        {!data && loading && <div className="card"><p className="empty">Loading…</p></div>}
        {!data && error && <div className="card"><p className="error-text">Dashboard unavailable: {error}</p></div>}
        {data && (
          <>
            {data.knowledge && <KnowledgeBar k={data.knowledge} />}
            {empty ? (
              <div className="card empty-hero">
                <h2>MentorIA is empty</h2>
                <button className="btn primary" onClick={() => navigate("/documents")}>
                  Add data
                </button>
              </div>
            ) : (
              <>
                <InsightsBlock data={data} />
                <ApprovalsBlock data={data} tz={tz} onRefresh={onRefresh} />
                <CalendarBlock data={data} tz={tz} onRefresh={onRefresh} />
                <div className="grid-2">
                  <AssignmentsBlock data={data} tz={tz} />
                  <OpportunitiesBlock data={data} tz={tz} />
                  <DiscussionsBlock data={data} tz={tz} />
                </div>
                <DocumentsBlock data={data} tz={tz} navigate={navigate} />
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

function InsightsBlock({ data }: { data: DashboardResponse }) {
  return (
    <Block icon="💡" title="Insights">
      {data.insights.length === 0 ? (
        <Empty>No insights yet</Empty>
      ) : (
        <MoreList
          className="xitems"
          items={data.insights}
          limit={5}
          render={(ins) => {
            const sources = ins.kind === "goal" ? ins.evidence.length : 0;
            return (
              <ExpandItem
                key={ins.id}
                icon={insightIcon[ins.kind] ?? "•"}
                title={ins.kind === "goal" ? ins.detail : ins.title.replace(/^Focus #\d+: /, "Focus: ")}
                badge={sources > 1 ? `${sources} sources` : undefined}
              >
                {ins.kind !== "goal" && <p>{ins.detail}</p>}
                {ins.confidence_note && <p className="muted small">{ins.confidence_note}</p>}
                <EvidenceChips evidence={ins.evidence} />
              </ExpandItem>
            );
          }}
        />
      )}
    </Block>
  );
}

function ApprovalsBlock({ data, tz, onRefresh }: { data: DashboardResponse; tz: string; onRefresh: () => void }) {
  if (data.recommendations.length === 0) return null;
  return (
    <Block icon="✅" title="Needs approval" demo={anyFixture(data.recommendations)}>
      <MoreList
        className="xitems"
        items={data.recommendations}
        limit={3}
        render={(r) => (
          <ExpandItem
            key={r.id}
            icon={r.type === "attend_event" ? "🎤" : "📖"}
            title={r.title.replace(/^Study: /, "").replace(/^Attend: /, "")}
            badge={r.suggested_start ? fmtDay(r.suggested_start, tz) : undefined}
          >
            <ApprovalCard rec={r} tz={tz} onChanged={onRefresh} compact />
          </ExpandItem>
        )}
      />
    </Block>
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
    <Block icon="📚" title="Assignments" status={card.status} demo={anyFixture(items)}>
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
      demo={anyFixture(card.items)}
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
    <Block icon="✉️" title="Opportunities" status={card.status} demo={anyFixture(card.items)}>
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
    <Block icon="💬" title="Discussions" status={card.status} demo={anyFixture(items)}>
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

function DocumentsBlock({ data, tz, navigate }: { data: DashboardResponse; tz: string; navigate: (p: string) => void }) {
  const card = data.cards.documents;
  return (
    <Block
      icon="📄"
      title="Documents"
      status={card.status}
      demo={anyFixture(card.documents)}
      actions={
        <button className="btn small-btn" onClick={() => navigate("/documents")}>
          Add data
        </button>
      }
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
