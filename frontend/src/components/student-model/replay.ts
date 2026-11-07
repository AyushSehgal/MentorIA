import type { ConceptState, Observation } from "../../api/types";

/** Mirrors backend/app/memory/bkt.py. Illustrative, uncalibrated parameters. */
export const BKT = { prior: 0.3, slip: 0.1, guess: 0.2, learn: 0.1 };
/** Mirrors ADR-007 (backend/app/memory/context.py). */
export const BLIND_SPOT_GAP = 0.3;
export const BLIND_SPOT_MIN_EVIDENCE = 2;

export function bktUpdate(p: number, correct: boolean): number {
  const { slip, guess, learn } = BKT;
  const num = correct ? p * (1 - slip) : p * slip;
  const den = correct ? num + (1 - p) * guess : num + (1 - p) * (1 - guess);
  const post = num / den;
  return post + (1 - post) * learn;
}

export interface AnswerEvent {
  id: string;
  conceptId: string;
  correct: boolean;
  at: string;
  /** Short source label, e.g. "Quiz 2 · p. 1 · Q3" */
  source: string;
  url: string | null;
  isFixture: boolean;
}

export interface Step {
  event: AnswerEvent;
  before: number;
  after: number;
}

/** Everything the views need about one concept at a point in the replay. */
export interface ConceptView {
  id: string;
  courseId: string; // primary course
  alsoIn: string[]; // other courses teaching the same concept (one estimate, shared evidence)
  label: string;
  mastery: number | null;
  confidence: number | null;
  blindSpot: boolean;
  stale: boolean;
  steps: Step[];
}

const byStr = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/** Accepted graded answers in the backend's replay order: (occurred_at, event_id), as plain string comparison (ADR-005). */
export function answerEvents(observations: Observation[]): AnswerEvent[] {
  return observations
    .filter(
      (o) =>
        o.event_type === "assessment_answer" &&
        o.status === "accepted" &&
        !!o.concept_id &&
        typeof o.payload?.correct === "boolean",
    )
    .sort((a, b) => byStr(a.occurred_at, b.occurred_at) || byStr(a.event_id, b.event_id))
    .map((o) => {
      const p = o.payload as Record<string, unknown>;
      const doc = String(p.document_title ?? "Assessment");
      const page = p.page != null ? `p. ${p.page}` : null;
      const q = p.question_id ? String(p.question_id) : null;
      return {
        id: o.event_id,
        conceptId: o.concept_id as string,
        correct: p.correct as boolean,
        at: o.occurred_at,
        source: [doc, page, q].filter(Boolean).join(" · "),
        url: p.document_id ? `/api/documents/${p.document_id}/file${p.page != null ? `#page=${p.page}` : ""}` : null,
        isFixture: o.is_fixture,
      };
    });
}

/** Last self-reported confidence per concept at or before `cutoff` (ms). */
function confidenceAt(observations: Observation[], cutoff: number): Record<string, number> {
  const out: Record<string, number> = {};
  observations
    .filter((o) => o.event_type === "self_confidence" && o.concept_id && typeof o.payload?.value === "number")
    .map((o) => ({ o, t: Date.parse(o.occurred_at) }))
    .filter(({ t }) => !isNaN(t) && t <= cutoff)
    .sort((a, b) => a.t - b.t)
    .forEach(({ o }) => (out[o.concept_id as string] = o.payload.value as number));
  return out;
}

/**
 * The student model replayed through the first `upTo` graded answers.
 * At upTo === events.length ("now") self-confidence comes from the live model; earlier, it is
 * whatever the student had reported by the time of the last included answer.
 */
export function replay(
  concepts: ConceptState[],
  events: AnswerEvent[],
  observations: Observation[],
  upTo: number,
): ConceptView[] {
  const steps: Record<string, Step[]> = {};
  const p: Record<string, number> = {};
  for (const e of events.slice(0, upTo)) {
    const before = p[e.conceptId] ?? BKT.prior;
    const after = bktUpdate(before, e.correct);
    p[e.conceptId] = after;
    (steps[e.conceptId] ??= []).push({ event: e, before, after });
  }
  const isNow = upTo >= events.length;
  const pastConf = isNow ? {} : upTo === 0 ? {} : confidenceAt(observations, Date.parse(events[upTo - 1].at));
  return concepts.map((c) => {
    const s = steps[c.concept_id] ?? [];
    const mastery = s.length ? s[s.length - 1].after : null;
    const confidence = isNow ? c.self_confidence : (pastConf[c.concept_id] ?? null);
    const blindSpot =
      mastery !== null && confidence !== null && s.length >= BLIND_SPOT_MIN_EVIDENCE && confidence - mastery >= BLIND_SPOT_GAP;
    return {
      id: c.concept_id,
      courseId: c.course_id,
      alsoIn: c.also_in ?? [],
      label: c.label,
      mastery,
      confidence,
      blindSpot,
      stale: isNow && c.stale,
      steps: s,
    };
  });
}

export type MasteryBand = "none" | "gap" | "building" | "solid";

export function band(m: number | null): MasteryBand {
  if (m === null) return "none";
  return m < 0.4 ? "gap" : m < 0.7 ? "building" : "solid";
}

/** "Introduction to Machine Learning (10-601)" -> "10-601" */
export function courseShort(label: string): string {
  const m = label.match(/\b\d{2}-\d{3}\b/);
  if (m) return m[0];
  return label.length > 14 ? label.slice(0, 13) + "…" : label;
}

export function fmtDay(iso: string, tz: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: tz, month: "short", day: "numeric" }).format(d);
  } catch {
    return d.toDateString();
  }
}
