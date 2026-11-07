import { useState } from "react";
import { api, DEFAULT_STUDENT } from "../api/client";
import type { ApproveResponse, Recommendation } from "../api/types";
import { fmtDateTime } from "../lib/format";
import { Bar, EvidenceChips } from "./Common";

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
  const [showFactors, setShowFactors] = useState(false);

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
    <div className={`approval status-${current.status} ${compact ? "compact" : ""}`}>
      <div className="approval-row">
        <div className="approval-main">
          <div className="approval-title">{current.title}</div>
          <div className="item-meta">
            {typeLabel[current.type] ?? current.type} ·{" "}
            {current.suggested_start ? fmtDateTime(current.suggested_start, tz) : "no time"}
            {current.duration_minutes ? ` · ${current.duration_minutes} min` : ""}
            {current.is_fixture && !compact ? " · Demo" : ""}
          </div>
        </div>
        {pending ? (
          <div className="approval-actions">
            <button
              className="btn primary small-btn"
              disabled={busy}
              onClick={approve}
              title={hasCalendarAction ? "Add to calendar — nothing is written without your approval" : "Approve"}
            >
              Approve
            </button>
            <button className="btn small-btn" disabled={busy} onClick={reject}>
              Reject
            </button>
          </div>
        ) : (
          <span className={`rec-status rec-${current.status}`}>{current.status.replace("_", " ")}</span>
        )}
      </div>
      {simulated && <div className="simulated-banner">Simulated — Calendar not connected; nothing written</div>}
      {current.status === "rejected" && <div className="approval-result">Rejected — no external action taken.</div>}
      {error && <p className="error-text">{error}</p>}
      <button className="link-btn why-btn" onClick={() => setShowFactors((s) => !s)}>
        {showFactors ? "hide details" : "details"}
      </button>
      {showFactors && (
        <div className="approval-details">
          <p className="approval-reason">{current.reason}</p>
          {current.factors.length > 0 && (
            <ul className="factors">
              {current.factors.map((f) => (
                <li key={f.name} title={f.explanation}>
                  <span className="factor-name">{f.name.replace(/_/g, " ")}</span>
                  <Bar value={f.value} />
                  <span className="factor-val">{f.value.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          )}
          {(result?.result_detail || current.result_detail) && (
            <p className="approval-result">{result?.result_detail ?? current.result_detail}</p>
          )}
          <EvidenceChips evidence={current.evidence} />
        </div>
      )}
    </div>
  );
}
