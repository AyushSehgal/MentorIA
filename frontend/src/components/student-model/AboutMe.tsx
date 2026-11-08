import type { StudentModel } from "../../api/types";
import { ChatPanel } from "../ChatPanel";
import { goalShort, type Selection } from "./ConceptMap";
import { band } from "./replay";

const short = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

/**
 * Student Model side panel: what MentorIA currently believes (from graded work and what the student said), plus the
 * About me chat. Statements typed there are saved; questions are answered from the model and never saved.
 */
export function AboutMe({
  model,
  goalIds,
  tz,
  onSelect,
  onChanged,
}: {
  model: StudentModel;
  goalIds: Set<string>; // propositions that have a goal pill on the map
  tz: string;
  onSelect: (s: Selection) => void;
  onChanged: () => void;
}) {
  return (
    <div className="sm-about">
      <BeliefSummary model={model} goalIds={goalIds} onSelect={onSelect} />
      <ChatPanel tz={tz} onMemoryChanged={onChanged} modes={["tell"]} />
    </div>
  );
}

function BeliefSummary({ model, goalIds, onSelect }: { model: StudentModel; goalIds: Set<string>; onSelect: (s: Selection) => void }) {
  const active = model.propositions.filter((p) => p.status !== "disputed" && p.status !== "expired");
  const goals = active
    .filter((p) => p.category === "goal" || p.category === "interest")
    .sort((a, b) => b.evidence_ids.length - a.evidence_ids.length)
    .slice(0, 3);
  const prefs = active.filter((p) => p.category === "preference").slice(0, 2);
  const graded = model.concepts.filter((c) => c.mastery !== null);
  const gaps = graded.filter((c) => (c.mastery ?? 1) < 0.4).sort((a, b) => (a.mastery ?? 0) - (b.mastery ?? 0)).slice(0, 4);
  const solid = graded.filter((c) => (c.mastery ?? 0) >= 0.7).sort((a, b) => (b.mastery ?? 0) - (a.mastery ?? 0)).slice(0, 3);
  const check = model.concepts.filter((c) => c.blind_spot);
  const mood = model.global_beliefs.find((b) => b.key === "motivation.self_report" && b.status !== "expired" && b.value);

  const concept = (c: (typeof graded)[number]) => (
    <button key={c.concept_id} className={`sm-src sm-src-btn band-${band(c.mastery)}`} onClick={() => onSelect({ kind: "concept", id: c.concept_id })}>
      <i className="sm-sw" />
      {c.label}
    </button>
  );

  const rows: [string, JSX.Element[]][] = [
    [
      "Goals",
      goals.map((p) => {
        const ev = model.proposition_evidence?.[p.id] ?? [];
        const n = ev.length || p.evidence_ids.length;
        const sample = ev.length > 0 && ev.every((e) => e.is_fixture);
        const inner = (
          <>
            {short(goalShort(p.statement), 42)}
            {n > 1 && <span className="sm-count">{n} sources</span>}
            {sample && <span className="chip-sample">Sample</span>}
          </>
        );
        return goalIds.has(p.id) ? (
          <button key={p.id} className="sm-src sm-src-btn sm-goal-chip" title={p.statement} onClick={() => onSelect({ kind: "goal", id: p.id })}>
            {inner}
          </button>
        ) : (
          <span key={p.id} className="sm-src sm-goal-chip" title={p.statement}>
            {inner}
          </span>
        );
      }),
    ],
    ["Check this", check.map(concept)],
    ["Gaps", gaps.map(concept)],
    ["Solid", solid.map(concept)],
    [
      "Prefers",
      prefs.map((p) => (
        <span key={p.id} className="sm-belief-text" title={p.statement}>
          {short(p.statement, 70)}
        </span>
      )),
    ],
    [
      "Feeling",
      mood
        ? [
            <span key="mood" className="sm-belief-text" title="Short-lived: expires 24 hours after you said it">
              “{short(String(mood.value), 60)}”
            </span>,
          ]
        : [],
    ],
  ];
  const shown = rows.filter(([, items]) => items.length > 0);

  return (
    <section className="card sm-beliefs">
      <h2>What MentorIA believes about you</h2>
      <p className="muted small">From your graded work and what you've told it. Click anything to see it on the map.</p>
      {shown.length === 0 ? (
        <p className="empty">Nothing yet. Tell MentorIA about yourself below.</p>
      ) : (
        <dl className="sm-belief-rows">
          {shown.map(([label, items]) => (
            <div key={label} className={`sm-belief-row ${label === "Check this" ? "is-flag" : ""}`}>
              <dt>{label}</dt>
              <dd>{items}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
