import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConceptState, GraphResponse, HistoryResponse, StudentModel } from "../api/types";
import { Bar, Card, DemoLabel, EvidenceChips, Empty } from "../components/Common";
import { KnowledgeGraph } from "../components/KnowledgeGraph";
import { fmtDateTime, masteryColor } from "../lib/format";

export function Knowledge({ tz }: { tz: string }) {
  const [model, setModel] = useState<StudentModel | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const errs: Record<string, string> = {};
    await Promise.all([
      api.model().then(setModel).catch((e) => (errs.model = e.message)),
      api.graph().then(setGraph).catch((e) => (errs.graph = e.message)),
      api.history().then(setHistory).catch((e) => (errs.history = e.message)),
    ]);
    setErrors(errs);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const byCourse = new Map<string, ConceptState[]>();
  model?.concepts.forEach((c) => byCourse.set(c.course_id, [...(byCourse.get(c.course_id) ?? []), c]));
  const courseLabel = (id: string) => model?.courses.find((c) => c.course_id === id)?.label ?? id;

  return (
    <div className="page">
      <Card title="My Student Model" actions={<button className="btn small-btn" onClick={() => void load()}>Refresh</button>}>
        {errors.model && <p className="error-text">{errors.model}</p>}
        {!model && !errors.model && <Empty>Loading…</Empty>}
        {model && (
          <>
            <p className="narrative">{model.narrative}</p>
            {model.courses.length === 0 && <Empty>No courses yet.</Empty>}
            <p className="muted small" title="BKT parameters are illustrative, not calibrated. Blind spots are candidate signals, not diagnoses.">
              Mastery = estimate from graded work · Confidence = your own rating.
            </p>
            {[...byCourse.entries()].map(([course, concepts]) => (
              <div key={course} className="course-block">
                <h3>
                  {courseLabel(course)}{" "}
                  {model.courses.find((c) => c.course_id === course)?.is_fixture && <DemoLabel />}
                  <span className="muted small">
                    {" "}
                    · {model.courses.find((c) => c.course_id === course)?.upcoming_due ?? 0} due in next 7 days
                  </span>
                </h3>
                <div className="table-wrap">
                  <table className="table concepts">
                    <thead>
                      <tr>
                        <th>Concept</th>
                        <th>BKT mastery</th>
                        <th>Evidence</th>
                        <th>✓ / ✗</th>
                        <th>Self-confidence</th>
                        <th>Flags</th>
                        <th>Sources</th>
                      </tr>
                    </thead>
                    <tbody>
                      {concepts.map((c) => (
                        <ConceptRow key={c.concept_id} c={c} tz={tz} onChanged={load} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </>
        )}
      </Card>

      <Card title="Goals, interests & preferences">
        {!model ? (
          <Empty>—</Empty>
        ) : model.propositions.length === 0 ? (
          <Empty>No goals yet. Tell MentorIA your goals in chat, or add something you wrote on the Add data page.</Empty>
        ) : (
          <ul className="props">
            {model.propositions.map((p) => {
              const sources = model.proposition_evidence?.[p.id] ?? [];
              return (
              <li key={p.id} className={`prop prop-${p.status}`}>
                <div>
                  <span className="pill">{p.category}</span> {p.statement}
                  {sources.length >= 2 && <span className="prop-sources">stated in {sources.length} sources</span>}
                  <EvidenceChips evidence={sources} />
                </div>
                <div className="prop-side">
                  <span className={`pill status-${p.status}`}>{p.status.replace("_", " ")}</span>
                  <span className="muted small">{fmtDateTime(p.updated_at, tz)}</span>
                  <button
                    className="btn small-btn"
                    disabled={p.status === "confirmed"}
                    onClick={() => api.setPropositionStatus(p.id, "confirmed").then(load).catch(() => undefined)}
                  >
                    Confirm
                  </button>
                  <button
                    className="btn small-btn"
                    disabled={p.status === "disputed"}
                    onClick={() => api.setPropositionStatus(p.id, "disputed").then(load).catch(() => undefined)}
                  >
                    That’s wrong
                  </button>
                </div>
              </li>
              );
            })}
          </ul>
        )}
        {model && model.global_beliefs.length > 0 && (
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
                  <div className="row-side">{String(b.value)}</div>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>

      <Card title="Knowledge graph">
        {errors.graph && <p className="error-text">{errors.graph}</p>}
        {graph ? <KnowledgeGraph graph={graph} /> : !errors.graph && <Empty>Loading…</Empty>}
      </Card>

      <Card title="Recent updates & evidence">
        {errors.history && <p className="error-text">{errors.history}</p>}
        {history && (
          <div className="grid-2">
            <div>
              <h3 className="section-label">Belief updates</h3>
              {history.belief_updates.length === 0 ? (
                <Empty>No belief updates yet.</Empty>
              ) : (
                <ul className="rows">
                  {[...history.belief_updates].reverse().slice(0, 40).map((u, i) => (
                    <li key={i} className="row">
                      <div className="row-main">
                        <span className="row-title">
                          {u.key} · {u.scope.concept_id ?? u.scope.course_id ?? u.scope.level}
                        </span>
                        <span className="muted small">
                          v{u.version} · {fmtDateTime(u.at, tz)} · evidence: {u.evidence_ids.slice(-3).join(", ") || "—"}
                        </span>
                      </div>
                      <div className="row-side">
                        {fmtVal(u.old_value)} → <strong>{fmtVal(u.new_value)}</strong>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="section-label">Observations (episodic memory)</h3>
              {history.observations.length === 0 ? (
                <Empty>No observations yet.</Empty>
              ) : (
                <ul className="rows">
                  {[...history.observations].reverse().slice(0, 40).map((o) => (
                    <li key={o.event_id} className="row">
                      <div className="row-main">
                        <span className="row-title">
                          {o.event_type} {o.concept_id && `· ${o.concept_id}`}
                        </span>
                        <span className="muted small">
                          {o.source} · {fmtDateTime(o.occurred_at, tz)} ·{" "}
                          {String(o.payload?.evidence_text ?? o.payload?.statement ?? "")}
                        </span>
                      </div>
                      <div className="row-side">
                        <span className={`pill status-${o.status}`}>{o.status.replace("_", " ")}</span>
                        {o.is_fixture && <DemoLabel />}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

function fmtVal(v: number | string | null) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return v;
}

function ConceptRow({ c, tz, onChanged }: { c: ConceptState; tz: string; onChanged: () => void }) {
  const [conf, setConf] = useState<number>(c.self_confidence ?? 0.5);
  const [saving, setSaving] = useState(false);
  useEffect(() => setConf(c.self_confidence ?? 0.5), [c.self_confidence]);

  async function save(v: number) {
    setSaving(true);
    try {
      await api.setSelfConfidence(c.concept_id, v);
      onChanged();
    } catch {
      /* surfaced by refresh */
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr>
      <td>
        <strong>{c.label}</strong>
        {c.last_evidence_at && <div className="muted small">last evidence {fmtDateTime(c.last_evidence_at, tz)}</div>}
      </td>
      <td className="mastery-cell">
        {c.mastery === null ? (
          <span className="muted small">No assessment evidence</span>
        ) : (
          <>
            <Bar value={c.mastery} color={masteryColor(c.mastery)} /> {c.mastery.toFixed(2)}
          </>
        )}
      </td>
      <td>{c.evidence_strength}</td>
      <td>
        {c.correct} / {c.incorrect}
      </td>
      <td className="conf-cell">
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={conf}
          disabled={saving}
          onChange={(e) => setConf(parseFloat(e.target.value))}
          onMouseUp={() => void save(conf)}
          onTouchEnd={() => void save(conf)}
          onKeyUp={() => void save(conf)}
          aria-label={`Self-confidence for ${c.label}`}
        />
        <span className="small">{c.self_confidence === null ? "not reported" : c.self_confidence.toFixed(2)}</span>
      </td>
      <td>
        {c.blind_spot && <span className="pill pill-bad">blind-spot candidate</span>}
        {c.stale && <span className="pill pill-warn">stale</span>}
      </td>
      <td>
        <EvidenceChips evidence={c.evidence} />
      </td>
    </tr>
  );
}
