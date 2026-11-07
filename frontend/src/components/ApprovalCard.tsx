import { useState } from "react";
import { api, DEFAULT_STUDENT } from "../api/client";
import type { ApproveResponse, Recommendation } from "../api/types";
import { fmtDateTime } from "../lib/format";
import { Bar, DemoLabel, EvidenceChips } from "./Common";

const typeLabel: Record<Recommendation["type"], string> = {
  study_session: "Study session",
  attend_event: "Attend event",
  review_opportunity: "Review opportunity",
};

export function ApprovalCard({
  rec,
  tz,
  onChanged,
  compact,
}: {
  rec: Recommendation;
  tz: string;
  onChanged?: () => void;
  compact?: boolean;
}) {
  const [current, setCurrent] = useState<Recommendation>(rec);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ApproveResponse | null>(null);
  const [showFactors, setShowFactors] = useState(!compact);

  const pending = current.status === "pending";
  const hasCalendarAction = current.proposed_action?.provider === "google_calendar";

  async function approve() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.approve(current.id, {
        student_id: DEFAULT_STUDENT,
        confirm: {
          title: current.title,
          suggested_start: current.suggested_start,
          duration_minutes: current.duration_minutes,
        },
      });
      setResult(res);
      setCurrent(res.recommendation);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.reject(current.id);
      setCurrent(res.recommendation);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const simulated = result?.simulated || current.status === "executed_simulated";

  return (
    <div className={`approval status-${current.status}`}>
      <div className="approval-head">
        <span className="approval-type">{typeLabel[current.type] ?? current.type}</span>
        <span className={`rec-status rec-${current.status}`}>{current.status.replace("_", " ")}</span>
        <DemoLabel show={current.is_fixture} />
      </div>
      <h3 className="approval-title">{current.title}</h3>
      <dl className="approval-meta">
        <div>
          <dt>Start</dt>
          <dd>{current.suggested_start ? fmtDateTime(current.suggested_start, tz) : "No time proposed"}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{current.duration_minutes ? `${current.duration_minutes} min` : "—"}</dd>
        </div>
        {current.proposed_action && (
          <div>
            <dt>Action</dt>
            <dd>
              {current.proposed_action.provider} · {current.proposed_action.operation}
            </dd>
          </div>
        )}
      </dl>
      <p className="approval-reason">{current.reason}</p>
      {current.factors.length > 0 && (
        <div className="factors">
          <button className="link-btn" onClick={() => setShowFactors((s) => !s)}>
            {showFactors ? "Hide" : "Show"} prioritization factors ({current.factors.length})
          </button>
          {showFactors && (
            <ul>
              {current.factors.map((f) => (
                <li key={f.name}>
                  <span className="factor-name">{f.name.replace(/_/g, " ")}</span>
                  <Bar value={f.value} />
                  <span className="factor-val">{f.value.toFixed(2)}</span>
                  <span className="factor-exp">{f.explanation}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <EvidenceChips evidence={current.evidence} />
      {pending && (
        <div className="approval-actions">
          {current.proposed_action ? (
            <button className="btn primary" disabled={busy} onClick={approve}>
              {hasCalendarAction ? "Approve & add to calendar" : "Approve"}
            </button>
          ) : (
            <button className="btn primary" disabled={busy} onClick={approve}>
              Mark approved
            </button>
          )}
          <button className="btn" disabled={busy} onClick={reject}>
            Reject
          </button>
          <span className="approval-note">Nothing is written externally without your approval.</span>
        </div>
      )}
      {simulated && (
        <div className="simulated-banner">Simulated — Calendar not connected; nothing written</div>
      )}
      {(result?.result_detail || current.result_detail) && (
        <p className="approval-result">{result?.result_detail ?? current.result_detail}</p>
      )}
      {current.status === "rejected" && <p className="approval-result">Rejected — no external action taken.</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
