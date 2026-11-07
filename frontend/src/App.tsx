import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type { DashboardResponse } from "./api/types";
import { FALLBACK_TZ } from "./lib/format";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Documents";
import { Knowledge } from "./pages/Knowledge";
import { Sources } from "./pages/Sources";

const ROUTES = [
  { path: "/", label: "Dashboard" },
  { path: "/knowledge", label: "Student Model" },
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
  const route = ROUTES.find((r) => r.path === path) ? path : "/";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={() => navigate("/")}>
          <span className="logo">✦</span> MentorIA
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
          <ThemeToggle />
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


type Theme = "light" | "dark";

/** Light/dark switch. Starts from the theme index.html applied (saved choice, else the OS setting) and remembers changes. */
function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light",
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      className="btn small-btn theme-toggle"
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      onClick={() => {
        setTheme(next);
        try {
          localStorage.setItem("mentoria-theme", next);
        } catch {
          /* storage unavailable: the choice lasts for this visit */
        }
      }}
    >
      {theme === "dark" ? "☀︎" : "☾"}
    </button>
  );
}
