import { useMemo, type KeyboardEvent } from "react";
import type { GraphResponse } from "../../api/types";
import { band, courseShort, type ConceptView } from "./replay";

export type Selection = { kind: "concept" | "goal"; id: string } | null;

const NODE_R = 15;
const RING_R = 21;
const LABEL_DY = 35;
const SIDE = 70; // room for labels left/right of each cluster
const GOAL_W = 190;

interface Props {
  concepts: ConceptView[];
  courses: { id: string; label: string }[];
  graph: GraphResponse | null;
  selected: Selection;
  courseFilter: string; // "all" | course id
  /** Calm view: only these concepts get a place on the map, and relation lines appear only around the selection.
   *  null = everything (the "All topics" view). */
  focusIds: Set<string> | null;
  onSelect: (s: Selection) => void;
}

const stripPrefix = (id: string) => id.slice(id.indexOf(":") + 1);
const truncate = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

/** "After graduation I want to work at a robotics startup." -> "Work at a robotics startup" (full text stays in the tooltip). */
const LEAD_IN =
  /^(?:(?:after graduation|over the next (?:year|semester)|this (?:year|semester)|long[- ]term|eventually|ultimately)[,\s]+)?(?:i(?:'m| am)?\s+)?(?:really\s+|especially\s+|also\s+|very\s+)*(?:want to|plan to|would like to|'d like to|hope to|interested in|aim to|intend to)\s+/i;
export function goalShort(statement: string): string {
  const s = statement.trim().replace(LEAD_IN, "").replace(/[.!]+$/, "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function activate(fn: () => void) {
  return (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fn();
    }
  };
}

export function ConceptMap({ concepts, courses, graph, selected, courseFilter, focusIds, onSelect }: Props) {
  const layout = useMemo(() => {
    // Picking a course zooms the map to that course's cluster.
    const clusters = courses
      .filter((c) => courseFilter === "all" || c.id === courseFilter)
      // In the all-courses view a shared concept sits in its primary course's ring; filtered to one course, that
      // course's ring also includes the concepts it shares with other courses.
      .map((c) => ({
        ...c,
        items: concepts.filter(
          (k) =>
            (!focusIds || focusIds.has(k.id)) &&
            (k.courseId === c.id || (courseFilter !== "all" && k.alsoIn.includes(c.id))),
        ),
      }))
      .filter((c) => c.items.length > 0);
    const radius = (n: number) => Math.max(95, (n * 50) / (2 * Math.PI));
    const maxR = Math.max(95, ...clusters.map((c) => radius(c.items.length)));
    const cy = maxR + 45;
    const pos = new Map<string, { x: number; y: number }>();
    const hubs: { id: string; label: string; x: number; y: number }[] = [];
    let cursor = 0;
    for (const c of clusters) {
      const r = radius(c.items.length);
      const cx = cursor + SIDE + r;
      cursor = cx + r + SIDE;
      hubs.push({ id: c.id, label: courseShort(c.label), x: cx, y: cy });
      c.items.forEach((k, i) => {
        const a = ((-90 + (i * 360) / c.items.length) * Math.PI) / 180;
        pos.set(k.id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
      });
    }
    const goalLinks = (graph?.edges ?? [])
      .filter((e) => e.relation === "supports_goal")
      .map((e) => ({ concept: stripPrefix(e.source), goal: stripPrefix(e.target) }))
      .filter((l) => pos.has(l.concept));
    const linkedGoals = new Set(goalLinks.map((l) => l.goal));
    const goals = (graph?.nodes ?? []).filter(
      (n) => n.type === "goal" && (courseFilter === "all" || linkedGoals.has(stripPrefix(n.id))),
    );
    const relations = (graph?.edges ?? [])
      .filter((e) => (e.relation === "prerequisite_of" || e.relation === "related_to") && e.source.startsWith("concept:"))
      .map((e) => ({ a: stripPrefix(e.source), b: stripPrefix(e.target) }))
      .filter((l) => pos.has(l.a) && pos.has(l.b));
    const width = Math.max(cursor, goals.length * (GOAL_W + 20), 560);
    const goalY = cy + maxR + 85;
    const goalPos = new Map<string, { x: number; y: number }>();
    goals.forEach((g, i) => {
      const span = goals.length * (GOAL_W + 20);
      goalPos.set(stripPrefix(g.id), { x: (width - span) / 2 + i * (GOAL_W + 20) + GOAL_W / 2 + 10, y: goalY });
    });
    const height = goals.length ? goalY + 30 : cy + maxR + 55;
    return { pos, hubs, goals, goalLinks, goalPos, relations, width, height };
  }, [concepts, courses, graph, courseFilter, focusIds]);

  const dimmed = (courseId: string) => courseFilter !== "all" && courseId !== courseFilter;
  const hiddenK = (k: ConceptView) =>
    courseFilter !== "all" && k.courseId !== courseFilter && !k.alsoIn.includes(courseFilter);
  const byId = new Map(concepts.map((k) => [k.id, k]));
  const isSel = (kind: "concept" | "goal", id: string) => selected?.kind === kind && selected.id === id;
  const calm = focusIds !== null;

  return (
    <div className="sm-map-scroll">
      <svg
        className="sm-map"
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        width="100%"
        role="group"
        aria-label="Concept map: color is the mastery estimate, the blue ring is your confidence"
      >
        {concepts.flatMap((k) => {
          const p = layout.pos.get(k.id);
          if (!p || hiddenK(k)) return [];
          // One line per course that teaches the concept: shared concepts connect to every course hub.
          return [k.courseId, ...k.alsoIn].flatMap((cid) => {
            const hub = layout.hubs.find((h) => h.id === cid);
            if (!hub) return [];
            const shared = cid !== k.courseId;
            return [
              <line key={`h-${k.id}-${cid}`} className={`sm-edge-hub ${shared ? "is-shared" : ""}`} x1={hub.x} y1={hub.y} x2={p.x} y2={p.y} />,
            ];
          });
        })}
        {layout.relations.map((l, i) => {
          const a = layout.pos.get(l.a)!;
          const b = layout.pos.get(l.b)!;
          const ka = byId.get(l.a);
          const kb = byId.get(l.b);
          if ((ka && hiddenK(ka)) || (kb && hiddenK(kb))) return null;
          if (calm && !isSel("concept", l.a) && !isSel("concept", l.b)) return null; // calm: only around the selection
          return <line key={`r-${i}`} className="sm-edge-rel" x1={a.x} y1={a.y} x2={b.x} y2={b.y} />;
        })}
        {layout.goalLinks.map((l, i) => {
          const a = layout.pos.get(l.concept);
          const g = layout.goalPos.get(l.goal);
          const k = byId.get(l.concept);
          if (!a || !g || (k && hiddenK(k))) return null;
          const active = isSel("goal", l.goal) || isSel("concept", l.concept);
          if (calm && !active) return null; // calm: goal lines only for the selected goal or concept
          return <line key={`g-${i}`} className={`sm-edge-goal ${active ? "is-active" : ""}`} x1={a.x} y1={a.y} x2={g.x} y2={g.y - 14} />;
        })}

        {layout.hubs.map((h) => (
          <g key={h.id} className="sm-hub" opacity={dimmed(h.id) ? 0.25 : 1}>
            <rect x={h.x - 38} y={h.y - 14} width={76} height={28} rx={14} />
            <text x={h.x} y={h.y + 4} textAnchor="middle">
              {h.label}
            </text>
          </g>
        ))}

        {layout.goals.map((g) => {
          const id = stripPrefix(g.id);
          const p = layout.goalPos.get(id)!;
          const sel = isSel("goal", id);
          return (
            <g
              key={g.id}
              className={`sm-goal ${sel ? "is-selected" : ""}`}
              role="button"
              tabIndex={0}
              aria-label={`Goal: ${g.label}`}
              onClick={() => onSelect({ kind: "goal", id })}
              onKeyDown={activate(() => onSelect({ kind: "goal", id }))}
            >
              <title>{g.label}</title>
              <rect x={p.x - GOAL_W / 2} y={p.y - 14} width={GOAL_W} height={28} rx={14} />
              <text x={p.x} y={p.y + 4} textAnchor="middle">
                {truncate(goalShort(g.label), 30)}
              </text>
            </g>
          );
        })}

        {concepts.map((k) => {
          const p = layout.pos.get(k.id);
          if (!p) return null;
          const b = band(k.mastery);
          const sel = isSel("concept", k.id);
          const labeled = sel || k.blindSpot || b === "gap";
          const ring = 2 * Math.PI * RING_R;
          return (
            <g
              key={k.id}
              className={`sm-node band-${b} ${sel ? "is-selected" : ""} ${labeled ? "is-labeled" : ""}`}
              opacity={hiddenK(k) ? 0.15 : 1}
              role="button"
              tabIndex={0}
              aria-label={`${k.label}: ${k.mastery === null ? "no graded work" : `estimate ${k.mastery.toFixed(2)}`}${
                k.confidence !== null ? `, your confidence ${k.confidence.toFixed(2)}` : ""
              }${k.blindSpot ? ", check this" : ""}`}
              onClick={() => onSelect({ kind: "concept", id: k.id })}
              onKeyDown={activate(() => onSelect({ kind: "concept", id: k.id }))}
            >
              <circle className="sm-dot" cx={p.x} cy={p.y} r={NODE_R} />
              {k.confidence !== null && (
                <circle
                  className="sm-ring"
                  cx={p.x}
                  cy={p.y}
                  r={RING_R}
                  strokeDasharray={`${(ring * k.confidence).toFixed(1)} ${ring.toFixed(1)}`}
                  transform={`rotate(-90 ${p.x} ${p.y})`}
                />
              )}
              {k.blindSpot && <circle className="sm-flag" cx={p.x + NODE_R} cy={p.y - NODE_R} r={5} />}
              <text className="sm-lbl" x={p.x} y={p.y + LABEL_DY} textAnchor="middle">
                {truncate(k.label, 26)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** Calm view keeps only the five signals; "not graded yet" shows while replaying or with all topics, prerequisites with all topics. */
export function MapLegend({ allTopics, replaying }: { allTopics: boolean; replaying: boolean }) {
  return (
    <div className="sm-legend">
      <span><i className="sm-sw band-gap" /> gap</span>
      <span><i className="sm-sw band-building" /> building</span>
      <span><i className="sm-sw band-solid" /> solid</span>
      <span><i className="sm-sw sm-sw-ring" /> your confidence</span>
      <span><i className="sm-sw sm-sw-flag" /> check this</span>
      {(allTopics || replaying) && <span><i className="sm-sw band-none" /> not graded yet</span>}
      {allTopics && <span><i className="sm-sw-line" /> prerequisite</span>}
    </div>
  );
}
