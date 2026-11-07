import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { GraphResponse, HistoryResponse, StudentModel } from "../api/types";
import { Empty } from "../components/Common";
import { ConceptMap, MapLegend, type Selection } from "../components/student-model/ConceptMap";
import { Details } from "../components/student-model/Details";
import { ConceptInspector, GoalInspector } from "../components/student-model/Inspector";
import {
  answerEvents,
  BLIND_SPOT_GAP,
  BLIND_SPOT_MIN_EVIDENCE,
  courseShort,
  fmtDay,
  replay,
  type ConceptView,
} from "../components/student-model/replay";
import { Timeline } from "../components/student-model/Timeline";
import "./knowledge.css";

type Tab = "map" | "timeline" | "details";
const PLAY_MS = 550;

const INFO =
  "Color is a Bayesian Knowledge Tracing estimate from graded work (illustrative, uncalibrated parameters). " +
  "The blue ring is your own confidence, stored separately. A red dot means your confidence is well above the estimate: " +
  "a signal to check, not a diagnosis.";

function defaultSelection(views: ConceptView[]): Selection {
  const pick =
    views.find((k) => k.blindSpot) ??
    [...views].filter((k) => k.mastery !== null).sort((a, b) => (a.mastery ?? 0) - (b.mastery ?? 0))[0] ??
    views[0];
  return pick ? { kind: "concept", id: pick.id } : null;
}

export function Knowledge({ tz }: { tz: string }) {
  const [model, setModel] = useState<StudentModel | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<Tab>("map");
  const [course, setCourse] = useState("all");
  const [sel, setSel] = useState<Selection>(null);
  const [idx, setIdx] = useState<number | null>(null); // null = now
  const [playing, setPlaying] = useState(false);
  const [draft, setDraft] = useState<{ id: string; value: number } | null>(null);

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

  const observations = useMemo(() => history?.observations ?? [], [history]);
  const events = useMemo(() => answerEvents(observations), [observations]);
  const total = events.length;
  const upTo = idx === null ? total : Math.min(idx, total);
  const isNow = idx === null;

  const views = useMemo(() => {
    const base = model ? replay(model.concepts, events, observations, upTo) : [];
    if (!draft) return base;
    return base.map((k) => {
      if (k.id !== draft.id) return k;
      const confidence = draft.value;
      const blindSpot =
        k.mastery !== null && k.steps.length >= BLIND_SPOT_MIN_EVIDENCE && confidence - k.mastery >= BLIND_SPOT_GAP;
      return { ...k, confidence, blindSpot };
    });
  }, [model, events, observations, upTo, draft]);

  const courses = useMemo(() => (model?.courses ?? []).map((c) => ({ id: c.course_id, label: c.label })), [model]);

  // Keep a valid selection: the current one if it still exists, otherwise the most telling concept.
  useEffect(() => {
    if (!model) return;
    const exists =
      sel &&
      (sel.kind === "concept"
        ? model.concepts.some((c) => c.concept_id === sel.id)
        : model.propositions.some((p) => p.id === sel.id));
    if (!exists) setSel(defaultSelection(views));
  }, [model, views, sel]);

  // Replay playback.
  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setIdx((i) => (i === null || i + 1 >= total ? null : i + 1)), PLAY_MS);
    return () => clearInterval(t);
  }, [playing, total]);
  useEffect(() => {
    if (playing && idx === null) setPlaying(false); // reached "now"
  }, [playing, idx]);

  function togglePlay() {
    if (playing) return setPlaying(false);
    if (idx === null) setIdx(0);
    setPlaying(true);
  }

  async function saveConfidence(id: string, value: number) {
    try {
      await api.setSelfConfidence(id, value);
    } finally {
      await load();
    }
  }

  async function setPropStatus(id: string, status: "confirmed" | "disputed") {
    try {
      await api.setPropositionStatus(id, status);
    } finally {
      await load();
    }
  }

  const selectConcept = (id: string) => setSel({ kind: "concept", id });
  const courseLabel = (id: string) => courses.find((c) => c.id === id)?.label ?? id;
  const selConcept = sel?.kind === "concept" ? views.find((k) => k.id === sel.id) : undefined;
  const selGoal = sel?.kind === "goal" ? model?.propositions.find((p) => p.id === sel.id) : undefined;
  const goalLinked = selGoal
    ? (graph?.edges ?? [])
        .filter((e) => e.relation === "supports_goal" && e.target === `goal:${selGoal.id}`)
        .map((e) => views.find((k) => `concept:${k.id}` === e.source))
        .filter((k): k is ConceptView => !!k)
    : [];
  const when = isNow ? "Now" : upTo === 0 ? "Start" : fmtDay(events[upTo - 1].at, tz);

  const inspector =
    selConcept ? (
      <ConceptInspector
        concept={selConcept}
        courseLabel={courseLabel(selConcept.courseId)}
        isNow={isNow}
        savedConfidence={model?.concepts.find((c) => c.concept_id === selConcept.id)?.self_confidence ?? null}
        onDraft={(v) => setDraft(v === null ? null : { id: selConcept.id, value: v })}
        onSave={(v) => saveConfidence(selConcept.id, v)}
      />
    ) : selGoal ? (
      <GoalInspector
        proposition={selGoal}
        evidence={model?.proposition_evidence?.[selGoal.id] ?? []}
        linked={goalLinked}
        onSelectConcept={selectConcept}
        onSetStatus={(s) => void setPropStatus(selGoal.id, s)}
      />
    ) : null;

  return (
    <div className="page">
      <section className="card sm-card">
        <div className="sm-toolbar">
          <div className="sm-tabs" role="tablist" aria-label="Student model views">
            {(
              [
                ["map", "Map"],
                ["timeline", "Timeline"],
                ["details", "⚙ Details"],
              ] as [Tab, string][]
            ).map(([t, label]) => (
              <button key={t} role="tab" aria-selected={tab === t} className={`sm-tab ${tab === t ? "is-on" : ""}`} onClick={() => setTab(t)}>
                {label}
              </button>
            ))}
          </div>
          <div className="sm-toolbar-right">
            {courses.length > 1 &&
              [{ id: "all", label: "All" }, ...courses].map((c) => (
                <button
                  key={c.id}
                  className={`sm-chip ${course === c.id ? "is-on" : ""}`}
                  onClick={() => setCourse(c.id)}
                  title={c.id === "all" ? "All courses" : c.label}
                >
                  {c.id === "all" ? "All" : courseShort(c.label)}
                </button>
              ))}
            <span className="sm-info" title={INFO} aria-label={INFO} tabIndex={0}>
              ⓘ
            </span>
            <button className="sm-icon-btn" onClick={() => void load()} aria-label="Refresh" title="Refresh">
              ↻
            </button>
          </div>
        </div>

        {errors.model && <p className="error-text">{errors.model}</p>}
        {!model && !errors.model && <Empty>Loading…</Empty>}
        {model && model.concepts.length === 0 && (
          <Empty>No courses yet. Add a course overview on the Add data page and its concepts will appear here.</Empty>
        )}

        {model && model.concepts.length > 0 && (
          <>
            {total > 0 && (
              <div className="sm-replay">
                <button
                  className="sm-icon-btn"
                  onClick={togglePlay}
                  aria-label={playing ? "Pause replay" : "Replay history"}
                  title={playing ? "Pause" : "Replay how the model changed"}
                >
                  {playing ? "❚❚" : "▶"}
                </button>
                <input
                  type="range"
                  min={0}
                  max={total}
                  step={1}
                  value={upTo}
                  aria-label="Point in time"
                  onChange={(e) => {
                    const v = parseInt(e.target.value, 10);
                    setPlaying(false);
                    setDraft(null);
                    setIdx(v >= total ? null : v);
                  }}
                />
                <span className={`sm-when ${isNow ? "" : "is-past"}`}>{when}</span>
              </div>
            )}

            {tab === "map" && (
              <>
                {errors.graph && <p className="error-text">{errors.graph}</p>}
                <ConceptMap
                  concepts={views}
                  courses={courses}
                  graph={graph}
                  selected={sel}
                  courseFilter={course}
                  onSelect={setSel}
                />
                <MapLegend />
              </>
            )}
            {tab === "timeline" &&
              (errors.history ? (
                <p className="error-text">{errors.history}</p>
              ) : (
                <Timeline concepts={views} courseFilter={course} tz={tz} selectedId={selConcept?.id ?? null} onSelect={selectConcept} />
              ))}
            {tab === "details" && (
              <Details
                model={model}
                concepts={views}
                courseFilter={course}
                tz={tz}
                onSelectConcept={(id) => {
                  selectConcept(id);
                  setTab("map");
                }}
                onSetPropStatus={(id, s) => void setPropStatus(id, s)}
              />
            )}
          </>
        )}
      </section>

      {model && tab !== "details" && inspector}
    </div>
  );
}
