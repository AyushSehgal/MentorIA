import { useMemo, useState } from "react";
import type { GraphEdge, GraphNode, GraphResponse } from "../api/types";
import { masteryColor } from "../lib/format";

const COL_X: Record<GraphNode["type"], number> = { course: 110, concept: 400, goal: 700, evidence: 700 };
const relColor: Record<GraphEdge["relation"], string> = {
  contains: "#94a3b8",
  prerequisite_of: "#7c3aed",
  assessed_by: "#0ea5e9",
  supports_goal: "#16a34a",
  related_to: "#f59e0b",
};

export function KnowledgeGraph({ graph }: { graph: GraphResponse }) {
  const [hover, setHover] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(true);

  const layout = useMemo(() => {
    const nodes = graph.nodes.filter((n) => showEvidence || n.type !== "evidence");
    const ids = new Set(nodes.map((n) => n.id));
    const edges = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    const cols: Record<string, GraphNode[]> = { course: [], concept: [], right: [] };
    // order concepts by course to reduce crossings
    const courseOf = new Map<string, string>();
    edges.forEach((e) => {
      if (e.relation === "contains") courseOf.set(e.target, e.source);
    });
    nodes.forEach((n) => {
      if (n.type === "course") cols.course.push(n);
      else if (n.type === "concept") cols.concept.push(n);
      else cols.right.push(n);
    });
    cols.concept.sort((a, b) => (courseOf.get(a.id) ?? "").localeCompare(courseOf.get(b.id) ?? ""));
    cols.right.sort((a, b) => a.type.localeCompare(b.type));
    const rowH = 46;
    const maxRows = Math.max(cols.course.length, cols.concept.length, cols.right.length, 1);
    const height = maxRows * rowH + 40;
    const pos = new Map<string, { x: number; y: number }>();
    const place = (list: GraphNode[], xFor: (n: GraphNode) => number) => {
      const offset = (height - list.length * rowH) / 2;
      list.forEach((n, i) => pos.set(n.id, { x: xFor(n), y: offset + i * rowH + rowH / 2 }));
    };
    place(cols.course, () => COL_X.course);
    place(cols.concept, () => COL_X.concept);
    place(cols.right, (n) => COL_X[n.type]);
    return { nodes, edges, pos, height };
  }, [graph, showEvidence]);

  const related = (id: string) =>
    hover === null || hover === id || layout.edges.some((e) => (e.source === hover && e.target === id) || (e.target === hover && e.source === id));

  if (graph.nodes.length === 0) return <p className="empty">Graph is empty.</p>;

  return (
    <div className="kg">
      <div className="kg-controls">
        <label className="small">
          <input type="checkbox" checked={showEvidence} onChange={(e) => setShowEvidence(e.target.checked)} /> show evidence
          nodes
        </label>
        <span className="kg-legend">
          {Object.entries(relColor).map(([r, c]) => (
            <span key={r}>
              <i style={{ background: c }} /> {r.replace(/_/g, " ")}
            </span>
          ))}
          <span>
            <i className="dashed" /> fixture provenance
          </span>
        </span>
      </div>
      <div className="kg-scroll">
        <svg viewBox={`0 0 820 ${layout.height}`} width="100%" style={{ minWidth: 620 }} role="img" aria-label="Knowledge graph">
          {layout.edges.map((e, i) => {
            const a = layout.pos.get(e.source);
            const b = layout.pos.get(e.target);
            if (!a || !b) return null;
            const active = hover === null || hover === e.source || hover === e.target;
            const sameCol = Math.abs(a.x - b.x) < 5;
            const d = sameCol
              ? `M${a.x + 70},${a.y} C${a.x + 130},${a.y} ${b.x + 130},${b.y} ${b.x + 70},${b.y}`
              : `M${a.x + (b.x > a.x ? 70 : -70)},${a.y} C${(a.x + b.x) / 2},${a.y} ${(a.x + b.x) / 2},${b.y} ${b.x + (b.x > a.x ? -70 : 70)},${b.y}`;
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={relColor[e.relation] ?? "#999"}
                strokeWidth={active ? 1.8 : 0.8}
                strokeOpacity={active ? 0.9 : 0.2}
                strokeDasharray={e.provenance === "fixture" ? "5 4" : undefined}
              >
                <title>
                  {e.source} —{e.relation}→ {e.target} ({e.provenance})
                </title>
              </path>
            );
          })}
          {layout.nodes.map((n) => {
            const p = layout.pos.get(n.id)!;
            const mastery = typeof n.data?.mastery === "number" ? (n.data.mastery as number) : null;
            const fill =
              n.type === "course"
                ? "#e0e7ff"
                : n.type === "concept"
                  ? masteryColor(mastery)
                  : n.type === "goal"
                    ? "#dcfce7"
                    : "#e0f2fe";
            const dim = !related(n.id);
            const label = n.label.length > 22 ? n.label.slice(0, 21) + "…" : n.label;
            return (
              <g
                key={n.id}
                transform={`translate(${p.x - 70},${p.y - 16})`}
                opacity={dim ? 0.3 : 1}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "default" }}
              >
                <rect width={140} height={32} rx={8} fill={fill} stroke={n.data?.blind_spot ? "#dc2626" : "#cbd5e1"} strokeWidth={n.data?.blind_spot ? 2 : 1} />
                <text x={70} y={20} textAnchor="middle" fontSize={11} fill={n.type === "concept" && mastery !== null ? "#fff" : "#1e293b"}>
                  {label}
                </text>
                <title>
                  {n.type}: {n.label}
                  {n.type === "concept" &&
                    `\nmastery: ${mastery === null ? "no assessment evidence" : mastery.toFixed(2)}\nself-confidence: ${
                      typeof n.data?.self_confidence === "number" ? (n.data.self_confidence as number).toFixed(2) : "—"
                    }\nevidence: ${n.data?.evidence_count ?? 0}`}
                </title>
              </g>
            );
          })}
        </svg>
      </div>
      <details className="kg-table">
        <summary>Relations table ({graph.edges.length})</summary>
        <table className="table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Relation</th>
              <th>Target</th>
              <th>Provenance</th>
            </tr>
          </thead>
          <tbody>
            {graph.edges.map((e, i) => (
              <tr key={i}>
                <td>{labelOf(graph, e.source)}</td>
                <td>{e.relation}</td>
                <td>{labelOf(graph, e.target)}</td>
                <td>{e.provenance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

function labelOf(g: GraphResponse, id: string) {
  return g.nodes.find((n) => n.id === id)?.label ?? id;
}
