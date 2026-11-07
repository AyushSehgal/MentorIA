import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { DocumentSummary } from "../api/types";
import { Card, DemoLabel, Empty } from "../components/Common";
import { fmtDateTime } from "../lib/format";

export function Documents({ tz, onChanged }: { tz: string; onChanged?: () => void }) {
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [course, setCourse] = useState("");
  const [last, setLast] = useState<DocumentSummary | null>(null);

  const load = useCallback(() => {
    api
      .documents()
      .then((d) => {
        setDocs(d);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  async function run(p: Promise<DocumentSummary>) {
    setBusy(true);
    setError(null);
    try {
      const d = await p;
      setLast(d);
      load();
      onChanged?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    void run(api.uploadDocument(file, course || undefined));
  }

  return (
    <div className="page">
      <Card title="Upload academic documents">
        <p className="muted">
          Upload lecture notes, readings, or <strong>graded</strong> historical quizzes (PDF). NOVA extracts text with page
          references. Only questions with explicit grading marks and a recognizable topic become assessment evidence. Ungraded
          documents are indexed as study material and <strong>do not change knowledge estimates</strong>.
        </p>
        <form className="upload" onSubmit={onUpload}>
          <input type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <select value={course} onChange={(e) => setCourse(e.target.value)} aria-label="Course">
            <option value="">Course: auto-detect</option>
            <option value="systems">Computer Systems</option>
            <option value="robot_learning">Robot Learning</option>
          </select>
          <button className="btn primary" disabled={!file || busy} type="submit">
            Upload & extract
          </button>
        </form>
        <div className="demo-buttons">
          <button className="btn" disabled={busy} onClick={() => void run(api.loadDemoDocument("graded_quiz"))}>
            Load demo graded quiz
          </button>
          <button className="btn" disabled={busy} onClick={() => void run(api.loadDemoDocument("ungraded_sheet"))}>
            Load demo ungraded question sheet
          </button>
          <span className="muted small">Demo PDFs are fixtures and are labeled “Demo data”.</span>
        </div>
        {busy && <p className="muted">Processing…</p>}
        {error && <p className="error-text">{error}</p>}
        {last && (
          <p className="success-text">
            Processed “{last.title || last.filename}”: {last.kind === "graded_assessment" ? "graded assessment" : "study material"},{" "}
            {last.observations_created} observations created
            {last.pending_review > 0 && `, ${last.pending_review} pending review`}.
          </p>
        )}
      </Card>

      {docs === null && !error && <Empty>Loading…</Empty>}
      {docs && docs.length === 0 && <Empty>No documents uploaded yet.</Empty>}
      {docs?.map((d) => (
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
            {d.filename} · {d.page_count} pages · course {d.course_id ?? "unassigned"} ·{" "}
            {d.kind === "graded_assessment" ? "graded assessment" : "study material"} · status {d.status} · uploaded{" "}
            {fmtDateTime(d.uploaded_at, tz)}
          </p>
          {d.error && <p className="error-text">{d.error}</p>}
          {d.kind === "study_material" && (
            <p className="muted small">No grading evidence found — indexed for search only; knowledge estimates unchanged.</p>
          )}
          {d.questions.length > 0 && (
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
          )}
          {d.is_fixture && <DemoLabel />}
        </Card>
      ))}
    </div>
  );
}
