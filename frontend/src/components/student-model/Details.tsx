import type { StudentModel } from "../../api/types";
import { fmtDateTime } from "../../lib/format";
import { EvidenceChips, SampleTag } from "../Common";
import { courseShort, type ConceptView } from "./replay";

const f2 = (v: number | null) => (v === null ? "—" : v.toFixed(2));

/** Everything at once: the full table, all propositions and global state. The "settings" view. */
export function Details({
  model,
  concepts,
  courseFilter,
  tz,
  onSelectConcept,
  onSetPropStatus,
}: {
  model: StudentModel;
  concepts: ConceptView[];
  courseFilter: string;
  tz: string;
  onSelectConcept: (id: string) => void;
  onSetPropStatus: (id: string, status: "confirmed" | "disputed") => void;
}) {
  const courseLabel = (id: string) => courseShort(model.courses.find((c) => c.course_id === id)?.label ?? id);
  const rows = concepts.filter((k) => courseFilter === "all" || k.courseId === courseFilter || k.alsoIn.includes(courseFilter));
  const lastAt = new Map(model.concepts.map((c) => [c.concept_id, c.last_evidence_at]));

  return (
    <div className="sm-details">
      <div className="table-wrap">
        <table className="table sm-table">
          <thead>
            <tr>
              <th>Concept</th>
              <th>Course</th>
              <th>Model</th>
              <th>You</th>
              <th>Right / wrong</th>
              <th>Last graded</th>
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((k) => {
              const right = k.steps.filter((s) => s.event.correct).length;
              const last = lastAt.get(k.id);
              return (
                <tr key={k.id} onClick={() => onSelectConcept(k.id)} className="sm-row-link">
                  <td>{k.label}</td>
                  <td className="muted">
                    {[k.courseId, ...k.alsoIn].map(courseLabel).join(" · ")}
                    {k.alsoIn.length > 0 && <span className="pill pill-shared">shared</span>}
                    <SampleTag show={!!model.courses.find((c) => c.course_id === k.courseId)?.is_fixture} />
                  </td>
                  <td>{f2(k.mastery)}</td>
                  <td>{f2(k.confidence)}</td>
                  <td>
                    {right} / {k.steps.length - right}
                  </td>
                  <td className="muted">{last ? fmtDateTime(last, tz) : "—"}</td>
                  <td>
                    {k.blindSpot && <span className="pill pill-bad">check this</span>}
                    {k.stale && <span className="pill pill-warn">stale</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h3 className="section-label">Goals, interests and preferences</h3>
      {model.propositions.length === 0 ? (
        <p className="empty">None yet. Tell MentorIA about your goals in the About me tab.</p>
      ) : (
        <ul className="props">
          {model.propositions.map((p) => (
            <li key={p.id} className={`prop prop-${p.status}`}>
              <div>
                <span className="pill">{p.category}</span> {p.statement}
                {p.evidence_ids.length > 1 && <span className="pill pill-accent">stated in {p.evidence_ids.length} sources</span>}
                <EvidenceChips evidence={model.proposition_evidence?.[p.id] ?? []} />
              </div>
              <div className="prop-side">
                <span className={`pill status-${p.status}`}>{p.status.replace("_", " ")}</span>
                <button className="btn small-btn" disabled={p.status === "confirmed"} onClick={() => onSetPropStatus(p.id, "confirmed")}>
                  Confirm
                </button>
                <button className="btn small-btn" disabled={p.status === "disputed"} onClick={() => onSetPropStatus(p.id, "disputed")}>
                  That’s wrong
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {model.global_beliefs.length > 0 && (
        <>
          <h3 className="section-label">Global state</h3>
          <ul className="rows">
            {model.global_beliefs.map((b) => (
              <li key={b.id} className="row">
                <div className="row-main">
                  <span className="row-title">{b.key}</span>
                  <span className="muted small">
                    {b.status} · {b.evidence_strength}
                    {b.expires_at && ` · expires ${fmtDateTime(b.expires_at, tz)}`}
                  </span>
                </div>
                <div className="row-side">{typeof b.value === "number" ? b.value.toFixed(2) : String(b.value)}</div>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3 className="section-label">About these numbers</h3>
      <p className="muted small">
        The model value is a Bayesian Knowledge Tracing estimate from graded work, with illustrative, uncalibrated
        parameters. "You" is your own confidence, stored separately and never mixed into the estimate. "Check this" marks a
        gap of 0.3 or more between the two, with at least two graded answers: a signal, not a diagnosis.
{" "}
        Concepts marked "shared" are taught in more than one course: one estimate, evidence from all of them. State version {model.state_version}.
      </p>
    </div>
  );
}
