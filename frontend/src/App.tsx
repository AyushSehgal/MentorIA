import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type { ConnectorStatus, DashboardResponse } from "./api/types";
import { StatusDot } from "./components/Common";
import { FALLBACK_TZ, providerLabel } from "./lib/format";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Documents";
import { Knowledge } from "./pages/Knowledge";
import { Sources } from "./pages/Sources";

const ROUTES = [
  { path: "/", label: "Dashboard" },
  { path: "/knowledge", label: "Student Model" },
  { path: "/documents", label: "Add data" },
  { path: "/sources", label: "Sources" },
];

function usePath(): [string, (p: string) => void] {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const navigate = useCallback((p: string) => {
    if (p !== window.location.pathname) window.history.pushState({}, "", p);
    setPath(p);
    window.scrollTo(0, 0);
  }, []);
  return [path, navigate];
}

export default function App() {
  const [path, navigate] = usePath();
  const [dash, setDash] = useState<DashboardResponse | null>(null);
  const [dashError, setDashError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [backendDown, setBackendDown] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.dashboard();
      setDash(d);
      setDashError(null);
      setBackendDown(false);
    } catch (e) {
      const err = e as Error & { status?: number };
      setDashError(err.message);
      if (err.status === 0) setBackendDown(true);
    } finally {
      setLoading(false);
    }
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function syncAll() {
    setSyncing(true);
    try {
      await api.syncAll();
    } catch {
      /* per-card status will show failures */
    } finally {
      setSyncing(false);
      void refresh();
    }
  }

  const tz = dash?.student.timezone ?? FALLBACK_TZ;
  const connectors: ConnectorStatus[] = dash?.connectors ?? [];
  const route = ROUTES.find((r) => r.path === path) ? path : "/";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={() => navigate("/")}>
          <span className="logo">✦</span> NOVA
          <span className="tagline">academic intelligence</span>
        </div>
        <nav className="nav">
          {ROUTES.map((r) => (
            <a
              key={r.path}
              href={r.path}
              className={route === r.path ? "active" : ""}
              onClick={(e) => {
                e.preventDefault();
                navigate(r.path);
              }}
            >
              {r.label}
            </a>
          ))}
        </nav>
        <div className="topbar-right">
          <div className="conn-dots" onClick={() => navigate("/sources")} title="Connector status">
            {connectors.map((c) => (
              <span key={c.provider} className="conn-dot">
                <StatusDot status={c} />
                <span className="conn-name">{providerLabel(c.provider)}</span>
              </span>
            ))}
          </div>
          {dash?.demo_mode && <span className="demo-label">Demo mode</span>}
          <span className="student">{dash?.student.name ?? "—"}</span>
          <button className="btn small-btn" onClick={() => void syncAll()} disabled={syncing}>
            {syncing ? "Syncing…" : "↻ Sync all"}
          </button>
        </div>
      </header>
      {backendDown && (
        <div className="banner">Backend unreachable at /api — start the API on port 8000. Showing what is available.</div>
      )}
      <main className="content">
        {route === "/" && (
          <Dashboard data={dash} error={dashError} loading={loading} onRefresh={() => void refresh()} navigate={navigate} />
        )}
        {route === "/knowledge" && <Knowledge key={refreshKey} tz={tz} />}
        {route === "/documents" && <Documents tz={tz} onChanged={() => void refresh()} />}
        {route === "/sources" && <Sources tz={tz} onChanged={() => void refresh()} />}
      </main>
    </div>
  );
}
