import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConnectorStatus, Provider } from "../api/types";
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
