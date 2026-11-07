import { fmtDay, type ConceptView } from "./replay";

export function Timeline({
  concepts,
  courseFilter,
  tz,
  selectedId,
  onSelect,
}: {
  concepts: ConceptView[];
  courseFilter: string;
  tz: string;
  selectedId: string | null;
  onSelect: (conceptId: string) => void;
}) {
  const rows = concepts
    .filter((k) => courseFilter === "all" || k.courseId === courseFilter)
    .flatMap((k) => k.steps.map((s) => ({ k, s })))
    .sort((a, b) => (a.s.event.at < b.s.event.at ? 1 : a.s.event.at > b.s.event.at ? -1 : a.s.event.id < b.s.event.id ? 1 : -1));

  if (rows.length === 0) return <p className="empty">No graded work at this point in time.</p>;

  return (
    <ol className="sm-timeline">
      {rows.map(({ k, s }) => (
        <li key={s.event.id}>
          <button className={`sm-tl-row ${selectedId === k.id ? "is-selected" : ""}`} onClick={() => onSelect(k.id)}>
            <span className={s.event.correct ? "sm-ok" : "sm-bad"} aria-label={s.event.correct ? "right" : "wrong"}>
              {s.event.correct ? "✓" : "✗"}
            </span>
            <span className="sm-tl-main">
              <span>{k.label}</span>
              <span className="muted small">
                {s.event.source} · {fmtDay(s.event.at, tz)}
              </span>
            </span>
            <span className="sm-tl-delta">
              <span className="muted">{s.before.toFixed(2)} →</span> {s.after.toFixed(2)}
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}
