import { useEffect, useRef, useState } from "react";
import type { EvidenceRef, SemanticProposition } from "../../api/types";
import { EvidenceChips } from "../Common";
import { band, type ConceptView, type Step } from "./replay";

export function ConceptInspector({
  concept,
  courseLabel,
  isNow,
  savedConfidence,
  onDraft,
  onSave,
}: {
  concept: ConceptView;
  courseLabel: string;
  isNow: boolean;
  /** The persisted self-report (concept.confidence may be a live draft while dragging). */
  savedConfidence: number | null;
  onDraft: (value: number | null) => void;
  onSave: (value: number) => Promise<void>;
}) {
  const k = concept;
  const right = k.steps.filter((s) => s.event.correct).length;
  return (
    <section className="sm-inspector" aria-live="polite">
      <header className="sm-ins-head">
        <div>
          <h3>{k.label}</h3>
          <p className="muted small">
            {courseLabel} · {k.steps.length ? `${right} of ${k.steps.length} graded answers right` : "no graded work yet"}
            {k.stale && " · evidence is over 60 days old"}
          </p>
        </div>
        {k.blindSpot && <span className="sm-badge-flag">Check this</span>}
      </header>

      <Scale mastery={k.mastery} confidence={k.confidence} />
      {k.blindSpot && <p className="muted small sm-note">You feel confident, but graded work disagrees.</p>}

      {k.steps.length > 0 && (
        <>
          <Sparkline steps={k.steps} />
          <div className="sm-sources">
            {k.steps.map((s) => {
              const inner = (
                <>
                  <span className={s.event.correct ? "sm-ok" : "sm-bad"} aria-label={s.event.correct ? "right" : "wrong"}>
                    {s.event.correct ? "✓" : "✗"}
                  </span>
                  {s.event.source}
                  {s.event.isFixture && <span className="chip-sample">Sample</span>}
                </>
              );
              return s.event.url ? (
                <a key={s.event.id} className="sm-src" href={s.event.url} target="_blank" rel="noreferrer">
                  {inner}
                </a>
              ) : (
                <span key={s.event.id} className="sm-src">
                  {inner}
                </span>
              );
            })}
          </div>
        </>
      )}

      {isNow ? (
        <ConfidenceSlider key={k.id} value={savedConfidence} label={k.label} onDraft={onDraft} onSave={onSave} />
      ) : (
        <p className="muted small sm-note">Replaying history. Go back to now to change your confidence.</p>
      )}
    </section>
  );
}

function Scale({ mastery, confidence }: { mastery: number | null; confidence: number | null }) {
  return (
    <div className="sm-scale" aria-hidden="true">
      <div className="sm-scale-track" />
      {mastery !== null && (
        <>
          <span className="sm-scale-tag" style={{ left: `${mastery * 100}%` }}>
            model {mastery.toFixed(2)}
          </span>
          <span className={`sm-scale-model band-${band(mastery)}`} style={{ left: `${mastery * 100}%` }} />
        </>
      )}
      {confidence !== null && (
        <>
          <span className="sm-scale-tag sm-scale-tag-you" style={{ left: `${confidence * 100}%` }}>
            you {confidence.toFixed(2)}
          </span>
          <span className="sm-scale-you" style={{ left: `${confidence * 100}%` }} />
        </>
      )}
      {mastery === null && confidence === null && <span className="sm-scale-empty">No estimate or confidence yet</span>}
    </div>
  );
}

function Sparkline({ steps }: { steps: Step[] }) {
  const W = 600;
  const H = 70;
  const pad = 14;
  const dx = (W - 2 * pad) / steps.length;
  const y = (m: number) => H - 8 - m * (H - 18);
  const pts = [{ x: pad, y: y(steps[0].before) }, ...steps.map((s, i) => ({ x: pad + (i + 1) * dx, y: y(s.after) }))];
  return (
    <svg className="sm-spark" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Mastery estimate after each graded answer">
      <line className="sm-spark-mid" x1={pad} x2={W - pad} y1={y(0.5)} y2={y(0.5)} />
      <polyline className="sm-spark-line" points={pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")} />
      {steps.map((s, i) => (
        <circle key={s.event.id} className={s.event.correct ? "sm-spark-ok" : "sm-spark-bad"} cx={pts[i + 1].x} cy={pts[i + 1].y} r={5}>
          <title>
            {s.event.source}: {s.before.toFixed(2)} → {s.after.toFixed(2)}
          </title>
        </circle>
      ))}
    </svg>
  );
}

function ConfidenceSlider({
  value,
  label,
  onDraft,
  onSave,
}: {
  value: number | null;
  label: string;
  onDraft: (v: number | null) => void;
  onSave: (v: number) => Promise<void>;
}) {
  const [v, setV] = useState(value ?? 0.5);
  const [saving, setSaving] = useState(false);
  // Refs, not state: commits fire from pointer/key/blur events and must see the latest value immediately.
  const latest = useRef<number>(value ?? 0.5);
  const saved = useRef<number | null>(value);
  const inFlight = useRef(false);
  const touched = useRef(false); // only values the student actually moved are ever saved
  useEffect(() => {
    saved.current = value;
    if (!inFlight.current && !touched.current) {
      setV(value ?? 0.5);
      latest.current = value ?? 0.5;
    }
  }, [value]);

  /** Saves the latest value; if it changes while a save is in flight, saves again so the last value always wins. */
  async function commit() {
    if (inFlight.current || !touched.current || latest.current === saved.current) return;
    inFlight.current = true;
    setSaving(true);
    try {
      while (latest.current !== saved.current) {
        const target = latest.current;
        await onSave(target);
        saved.current = target;
      }
      touched.current = false;
    } finally {
      inFlight.current = false;
      setSaving(false);
      onDraft(null);
    }
  }

  return (
    <label className="sm-conf">
      <span>Your confidence</span>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={v}
        aria-busy={saving}
        aria-label={`Your confidence in ${label}`}
        onChange={(e) => {
          const nv = parseFloat(e.target.value);
          latest.current = nv;
          touched.current = true;
          setV(nv);
          onDraft(nv);
        }}
        onPointerUp={() => void commit()}
        onKeyUp={() => void commit()}
        onBlur={() => void commit()}
      />
      <span className="sm-conf-val">{value === null && !touched.current ? "—" : v.toFixed(2)}</span>
    </label>
  );
}

export function GoalInspector({
  proposition,
  evidence,
  linked,
  onSelectConcept,
  onSetStatus,
}: {
  proposition: SemanticProposition;
  evidence: EvidenceRef[];
  linked: ConceptView[];
  onSelectConcept: (id: string) => void;
  onSetStatus: (status: "confirmed" | "disputed") => void;
}) {
  const p = proposition;
  return (
    <section className="sm-inspector" aria-live="polite">
      <header className="sm-ins-head">
        <div>
          <h3>{p.statement}</h3>
          <p className="muted small">
            {p.category} · {p.status.replace("_", " ")}
            {evidence.length > 1 && ` · stated in ${evidence.length} sources`}
          </p>
        </div>
        <div className="sm-actions">
          <button className="btn small-btn" disabled={p.status === "confirmed"} onClick={() => onSetStatus("confirmed")}>
            Confirm
          </button>
          <button className="btn small-btn" disabled={p.status === "disputed"} onClick={() => onSetStatus("disputed")}>
            That’s wrong
          </button>
        </div>
      </header>
      {linked.length > 0 && (
        <div className="sm-sources">
          {linked.map((k) => (
            <button key={k.id} className={`sm-src sm-src-btn band-${band(k.mastery)}`} onClick={() => onSelectConcept(k.id)}>
              <i className="sm-sw" />
              {k.label}
            </button>
          ))}
        </div>
      )}
      <EvidenceChips evidence={evidence} />
    </section>
  );
}
