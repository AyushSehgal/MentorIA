import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { DemoAsset, DocumentSummary, ImportKind, ImportResult, StudentModel } from "../api/types";

type CourseSummary = StudentModel["courses"][number];
import { Card, DemoLabel, Empty } from "../components/Common";
import { fmtDateTime } from "../lib/format";

const KIND_LABEL: Record<ImportKind, string> = {
  course_overview: "Course overview",
  graded_assessment: "Graded work",
  study_material: "Study material",
  personal_document: "My writing",
  email: "Email",
  calendar: "Calendar",
  source_pack: "Canvas / Piazza export",
};

function KindBadge({ kind }: { kind: ImportKind }) {
  return <span className="kind-badge">{KIND_LABEL[kind] ?? kind}</span>;
}

function ImportResultView({ r }: { r: ImportResult }) {
  return (
    <div className={`import-result ${r.warnings.length ? "warn" : ""}`}>
      <strong>{r.summary}</strong>
      {r.changes.length > 0 && (
        <ul>
          {r.changes.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
      {r.warnings.length > 0 && (
        <ul>
          {r.warnings.map((w, i) => (
            <li key={i}>⚠️ {w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Documents({ tz, onChanged }: { tz: string; onChanged?: () => void }) {
  const [assets, setAssets] = useState<DemoAsset[] | null>(null);
  const [history, setHistory] = useState<ImportResult[] | null>(null);
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [results, setResults] = useState<Record<string, ImportResult>>({});
  const [assetErrors, setAssetErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [mine, setMine] = useState(false);
  const [course, setCourse] = useState("");
  const [uploadResult, setUploadResult] = useState<ImportResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.demoAssets().then(setAssets).catch((e) => setError((e as Error).message));
    api.imports().then(setHistory).catch(() => setHistory([]));
    api.documents().then(setDocs).catch(() => setDocs([]));
    api
      .model()
      .then((m) => setCourses(m.courses))
      .catch(() => setCourses([]));
  }, []);
  useEffect(load, [load]);

  async function addAsset(name: string): Promise<boolean> {
    setBusy(name);
    setAssetErrors((e) => ({ ...e, [name]: "" }));
    try {
      const r = await api.addDemoAsset(name);
      setResults((m) => ({ ...m, [name]: r }));
      return true;
    } catch (e) {
      setAssetErrors((m) => ({ ...m, [name]: (e as Error).message }));
      return false;
    } finally {
      setBusy(null);
      load();
      onChanged?.();
    }
  }

  async function addAllRemaining() {
    if (!assets) return;
    const remaining = [...assets].filter((a) => !a.added).sort((a, b) => a.step - b.step);
    for (const a of remaining) {
      const ok = await addAsset(a.name);
      if (!ok) break;
    }
  }

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy("upload");
    setUploadError(null);
    setUploadResult(null);
    try {
      const r = await api.importFile(file, { authoredByMe: mine, courseId: course || undefined });
      setUploadResult(r);
    } catch (err) {
      setUploadError((err as Error).message);
    } finally {
      setBusy(null);
      load();
      onChanged?.();
    }
  }

  const sortedAssets = assets ? [...assets].sort((a, b) => a.step - b.step) : null;
  const remaining = sortedAssets?.filter((a) => !a.added).length ?? 0;
  const graded = docs?.filter((d) => d.questions.length > 0) ?? [];

  return (
    <div className="page">
      <Card
        title="Demo assets"
        actions={
          <button className="btn small-btn" disabled={busy !== null || remaining === 0} onClick={() => void addAllRemaining()}>
            Add all remaining
          </button>
        }
      >
        <p className="muted small">
          NOVA starts empty. Add these prepared files one at a time and watch the dashboard, student model and chat change.
          They are sample files (labeled “Demo data”), not your real accounts.
        </p>
        {error && <p className="error-text">{error}</p>}
        {sortedAssets === null && !error && <Empty>Loading…</Empty>}
        {sortedAssets && sortedAssets.length === 0 && <Empty>No demo assets found on the server.</Empty>}
        {sortedAssets && sortedAssets.length > 0 && (
          <ol className="asset-list">
            {sortedAssets.map((a) => (
              <li key={a.name} className={`asset ${a.added ? "added" : ""}`}>
                <div className="asset-head">
                  <span className="asset-step">{a.added ? "✓" : a.step}</span>
                  <span className="asset-title">{a.title}</span>
                  <KindBadge kind={a.kind} />
                  {a.added && <span className="pill pill-good">✓ Added</span>}
                  <button
                    className={`btn small-btn ${a.added ? "" : "primary"}`}
                    disabled={busy !== null}
                    onClick={() => void addAsset(a.name)}
                  >
                    {busy === a.name ? "Adding…" : a.added ? "Add again" : "Add"}
                  </button>
                </div>
                <div className="muted small">
                  {a.description} <span className="muted">({a.name})</span>
                </div>
                {a.what_to_notice && (
                  <div className="asset-notice">
                    <strong>What to notice:</strong> {a.what_to_notice}
                  </div>
                )}
                {assetErrors[a.name] && <p className="error-text">{assetErrors[a.name]}</p>}
                {results[a.name] && <ImportResultView r={results[a.name]} />}
              </li>
            ))}
          </ol>
        )}
      </Card>

      <Card title="Upload your own file">
        <p className="muted small">
          Accepts PDFs (course overviews, graded quizzes/homework, notes, your own writing), emails (.eml), calendars (.ics)
          and Canvas/Piazza export packs (.md). Only graded questions with explicit marks change knowledge estimates; goals
          and preferences are learned only from files you wrote.
        </p>
        <form className="upload" onSubmit={onUpload}>
          <input
            type="file"
            accept=".pdf,.eml,.ics,.md,application/pdf,message/rfc822,text/calendar,text/markdown"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <div className="upload-opts">
            <label>
              <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> I wrote this (use it to
              learn my goals and preferences)
            </label>
            <select value={course} onChange={(e) => setCourse(e.target.value)} aria-label="Course">
              <option value="">Course: auto-detect</option>
              {courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <button className="btn primary" disabled={!file || busy !== null} type="submit">
            {busy === "upload" ? "Importing…" : "Import file"}
          </button>
        </form>
        {uploadError && <p className="error-text">{uploadError}</p>}
        {uploadResult && <ImportResultView r={uploadResult} />}
      </Card>

      <Card title="Import history">
        {history === null && <Empty>Loading…</Empty>}
        {history && history.length === 0 && <Empty>Nothing added yet.</Empty>}
        {history && history.length > 0 && (
          <ul className="rows">
            {history.map((h) => (
              <li key={h.id} className="row">
                <div className="row-main">
                  <span className="row-title">
                    {h.title || h.filename} <KindBadge kind={h.kind} />
                  </span>
                  <span className="muted small">{h.summary}</span>
                </div>
                <div className="row-side">
                  {h.is_fixture && <DemoLabel />}
                  <span className="muted small">{fmtDateTime(h.imported_at, tz)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {graded.map((d) => (
        <Card
          key={d.id}
          title={d.title || d.filename}
          demo={d.is_fixture}
          actions={
            <a className="btn small-btn" href={d.file_url} target="_blank" rel="noreferrer">
              Open PDF
            </a>
          }
        >
          <p className="muted small">
            {d.filename} · {d.page_count} pages · course {d.course_id ?? "unassigned"} · graded work · {d.observations_created}{" "}
            answers counted{d.pending_review > 0 && ` · ${d.pending_review} pending review`} · added {fmtDateTime(d.uploaded_at, tz)}
          </p>
          {d.error && <p className="error-text">{d.error}</p>}
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Q</th>
                  <th>Page</th>
                  <th>Concept</th>
                  <th>Result</th>
                  <th>Status</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {d.questions.map((qq) => (
                  <tr key={`${qq.question_id}-${qq.page}`}>
                    <td>{qq.question_id}</td>
                    <td>
                      <a href={`${d.file_url}#page=${qq.page}`} target="_blank" rel="noreferrer">
                        p. {qq.page}
                      </a>
                    </td>
                    <td>{qq.concept_id ?? <span className="muted">{qq.topic_text ?? "unmapped"}</span>}</td>
                    <td className={qq.correct === true ? "ok" : qq.correct === false ? "bad" : ""}>
                      {qq.correct === true ? "✓" : qq.correct === false ? "✗" : "—"}
                    </td>
                    <td>
                      <span className={`pill status-${qq.status}`}>{qq.status.replace("_", " ")}</span>
                    </td>
                    <td className="small">{qq.evidence_text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  );
}
