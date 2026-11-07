import { useEffect, useRef, useState } from "react";
import type { DashboardResponse, Insight, KnowledgeCounts, SourceRecord } from "../api/types";
import { ApprovalCard } from "../components/ApprovalCard";
import { ChatPanel } from "../components/ChatPanel";
import { WeekCalendar } from "../components/WeekCalendar";
import { Bar, Block, Empty, Item, MoreList, Why } from "../components/Common";
import { fmtDay, fmtShort, fmtTime, pct } from "../lib/format";

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
          className="insight-tiles"
          items={data.insights}
          limit={6}
          render={(ins) => {
            const sources = ins.kind === "goal" ? ins.evidence.length : 0;
            const tip = [ins.detail, ins.confidence_note, ...ins.evidence.map((e) => `• ${e.label}`)].filter(Boolean).join("\n");
            return (
              <li key={ins.id} className={`tile insight-${ins.kind}`} title={tip}>
                <div className="tile-title">
                  <span aria-hidden>{insightIcon[ins.kind] ?? "•"}</span> {ins.kind === "goal" ? "Your goal" : ins.title}
                  {sources > 1 && <span className="pill pill-accent">{sources} sources</span>}
                </div>
                <div className="tile-detail">{ins.detail}</div>
              </li>
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
        className="approvals"
        items={data.recommendations}
        limit={3}
        render={(r) => (
          <li key={r.id}>
            <ApprovalCard rec={r} tz={tz} onChanged={onRefresh} compact />
          </li>
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
          items={items}
          render={(r) => {
            const done = !!r.metadata?.completed;
            const dueMs = r.occurred_at ? new Date(r.occurred_at).getTime() - Date.now() : null;
            const urgent = !done && dueMs !== null && dueMs >= 0 && dueMs < 3 * 864e5;
            return (
              <Item
                key={r.id}
                done={done}
                tip={r.body || undefined}
                title={r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer">{r.title}</a> : r.title}
                meta={`${courseShort(r)} · ${done ? "done" : `due ${fmtShort(r.occurred_at, tz)}`}`}
                side={urgent ? <span className="pill pill-warn">soon</span> : done ? <span className="pill pill-good">✓</span> : null}
              />
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
  return (
    <Block icon="📅" title="Calendar" status={card.status} demo={anyFixture(card.items)} className="block-wide">
      {card.items.length === 0 && deadlines.length === 0 ? (
        <Empty>No events yet</Empty>
      ) : (
        <WeekCalendar events={card.items} deadlines={deadlines} freeWindows={card.free_windows} tz={tz} onChanged={onRefresh} />
      )}
    </Block>
  );
}

function OpportunitiesBlock({ data, tz }: { data: DashboardResponse; tz: string }) {
  const card = data.cards.gmail;
  const opps = [...card.opportunities].sort((a, b) => b.relevance_score - a.relevance_score);
  return (
    <Block icon="✉️" title="Opportunities" status={card.status} demo={anyFixture(card.items)}>
      {opps.length === 0 ? (
        <Empty>No emails yet</Empty>
      ) : (
        <MoreList
          items={opps}
          render={(o) => (
            <Item
              key={o.record.id}
              title={o.record.title}
              tip={[o.timing_label, o.speaker, o.venue].filter(Boolean).join(" · ")}
              meta={
                <>
                  {o.event_start ? fmtDay(o.event_start, tz) + " " + fmtTime(o.event_start, tz) : "no date"} ·{" "}
                  <Bar value={o.relevance_score} /> {pct(o.relevance_score)}{" "}
                  <Why reasons={o.relevance_reasons} />
                </>
              }
            />
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
          items={items}
          render={(r) => (
            <Item
              key={r.id}
              tip={r.body}
              title={r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer">{r.title}</a> : r.title}
              meta={`${courseShort(r)} · ${fmtDay(r.occurred_at, tz)}`}
              side={r.metadata?.is_instructor ? <span className="pill pill-accent">Instructor</span> : null}
            />
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
          items={card.documents}
          render={(d) => (
            <Item
              key={d.id}
              title={
                <a href={d.file_url} target="_blank" rel="noreferrer">
                  {d.title || d.filename}
                </a>
              }
              tip={d.error ?? undefined}
              meta={`${d.kind === "graded_assessment" ? "Graded" : "Material"} · ${d.page_count} p · ${fmtDay(d.uploaded_at, tz)}`}
              side={
                d.status === "failed" ? (
                  <span className="pill pill-bad">failed</span>
                ) : d.kind === "graded_assessment" ? (
                  <span className="pill pill-good">{d.observations_created} answers</span>
                ) : null
              }
            />
          )}
        />
      )}
    </Block>
  );
}
