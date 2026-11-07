import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConnectorStatus, LLMMode, PrivacySettings, Provider } from "../api/types";
import { Card, StatusBadge } from "../components/Common";
import { fmtDateTime, providerLabel } from "../lib/format";

export function Sources({ tz, onChanged }: { tz: string; onChanged?: () => void }) {
  const [statuses, setStatuses] = useState<ConnectorStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .connectors()
      .then((s) => {
        setStatuses(s);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function sync(p: Provider) {
    setBusy(p);
    setMsg(null);
    try {
      const r = await api.syncProvider(p);
      setMsg(
        `${providerLabel(p)}: ${r.status.state} (${r.status.mode}) — ${r.records_added} added, ${r.records_total} total${
          r.errors.length ? ` · errors: ${r.errors.join("; ")}` : ""
        }`,
      );
      load();
      onChanged?.();
    } catch (e) {
      setMsg(`${providerLabel(p)} sync failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  async function reset() {
    if (!window.confirm("Reset the demo? This clears local NOVA state and re-seeds labeled fixtures.")) return;
    setBusy("reset");
    try {
      await api.resetDemo();
      setMsg("Demo reset — fixtures re-seeded (no quiz ingested).");
      load();
      onChanged?.();
    } catch (e) {
      setMsg(`Reset failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <PrivacyCard />
      <Card
        title="Connected sources"
        actions={
          <button className="btn danger small-btn" disabled={busy !== null} onClick={() => void reset()}>
            Reset demo
          </button>
        }
      >
        <p className="muted small">
          “verified” means a live API call succeeded in this server process. Demo data is fixture content, never a claim about
          your real accounts.
        </p>
        {error && <p className="error-text">{error}</p>}
        {msg && <p className="info-text">{msg}</p>}
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>State</th>
                <th>Verified live</th>
                <th>Detail</th>
                <th>Last sync</th>
                <th>Records</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {statuses?.map((s) => (
                <tr key={s.provider}>
                  <td>
                    <strong>{providerLabel(s.provider)}</strong>
                  </td>
                  <td>
                    <StatusBadge status={s} />
                  </td>
                  <td>{s.verified_live ? "yes" : "no"}</td>
                  <td className="small">{s.detail}</td>
                  <td className="small">{fmtDateTime(s.last_synced_at, tz)}</td>
                  <td>{s.record_count}</td>
                  <td>
                    {s.provider !== "documents" && (
                      <button className="btn small-btn" disabled={busy !== null} onClick={() => void sync(s.provider)}>
                        {busy === s.provider ? "Syncing…" : "Sync"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

const MODES: { mode: LLMMode; title: string; blurb: string }[] = [
  { mode: "off", title: "Off — most private", blurb: "No language model. Answers are assembled directly from your stored evidence." },
  { mode: "local", title: "Local model", blurb: "A model running on this computer (e.g. Ollama) rewords answers. Nothing leaves your device." },
  { mode: "cloud", title: "Cloud model", blurb: "A hosted model (OpenRouter) rewords answers. Your question and NOVA's draft answer are sent to that provider." },
];

function PrivacyCard() {
  const [p, setP] = useState<PrivacySettings | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.privacy().then(setP).catch((e) => setErr((e as Error).message));
  }, []);

  async function choose(mode: LLMMode) {
    if (mode === "cloud" && !window.confirm("Cloud mode sends your questions and NOVA's drafted answers (which can include concept names, estimates, deadlines and email/assignment titles) to OpenRouter and the model provider it routes to. Continue?")) return;
    setBusy(true);
    try {
      setP(await api.setPrivacy(mode));
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const available = (m: LLMMode) => m === "off" || (m === "local" ? p?.local_available : p?.cloud_available);
  const detail = (m: LLMMode) => (m === "local" ? p?.local_detail : m === "cloud" ? p?.cloud_detail : "Always available");

  return (
    <Card title="Privacy & AI">
      <p className="muted small">
        Every answer is first built from your stored evidence with citations. A language model, if you enable one, may only
        reword that draft; rewrites that add numbers or drop citations are discarded automatically.
      </p>
      {err && <p className="error-text">{err}</p>}
      <div className="privacy-modes" role="radiogroup" aria-label="Language model mode">
        {MODES.map((m) => (
          <label key={m.mode} className={`privacy-mode${p?.mode === m.mode ? " selected" : ""}${available(m.mode) ? "" : " unavailable"}`}>
            <input
              type="radio"
              name="llm-mode"
              checked={p?.mode === m.mode}
              disabled={busy || !p || !available(m.mode)}
              onChange={() => void choose(m.mode)}
            />
            <span>
              <strong>{m.title}</strong>
              <span className="small">{m.blurb}</span>
              <span className="small muted">{available(m.mode) ? "✓ " : "Not available: "}{detail(m.mode)}</span>
            </span>
          </label>
        ))}
      </div>
      {p && (
        <p className="small">
          {p.data_leaves_device ? "⚠️ Data leaves this device in the current mode. " : "🔒 Nothing leaves this device in the current mode. "}
          <span className="muted">What an LLM receives: {p.sent_to_llm}</span>
        </p>
      )}
    </Card>
  );
}
