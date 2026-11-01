import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, resetCsrf } from "./api.js";
import Dashboard from "./Dashboard.jsx";
import Employees from "./Employees.jsx";
import Housing from "./Housing.jsx";
import Duties from "./Duties.jsx";
import Reports from "./Reports.jsx";
import AuditLog from "./AuditLog.jsx";

const AppCtx = createContext(null);
export const useApp = () => useContext(AppCtx);

const PAGES = [
  ["dashboard", "Dashboard", "▦"],
  ["employees", "Employees", "☰"],
  ["archive", "Archive", "⧉"],
  ["housing", "Staff Housing", "⌂"],
  ["duties", "Duty Roster", "◷"],
  ["reports", "Reports", "▤"],
  ["audit", "Audit Log", "✎"],
];

function Login({ onLogin }) {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    setErr(null);
    try {
      resetCsrf();
      onLogin(await api("auth/login/", { method: "POST", body: { username: u, password: p } }));
      resetCsrf();
    } catch (ex) {
      setErr(ex.message);
    }
  };
  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <div className="brand" style={{ color: "var(--navy)", padding: "0 0 16px" }}>
          <div className="brand-mark" style={{ background: "var(--navy)", color: "#fff" }}>HR</div>
          <div><strong>Enterprise HRMS</strong><small style={{ color: "var(--muted)" }}>Sign in to continue</small></div>
        </div>
        {err && <div className="error">{err}</div>}
        <div className="grid">
          <input placeholder="Username" value={u} onChange={(e) => setU(e.target.value)} autoFocus />
          <input placeholder="Password" type="password" value={p} onChange={(e) => setP(e.target.value)} />
          <button className="btn primary" type="submit">Sign in</button>
        </div>
        <div className="demo-users">
          Demo accounts: <b>admin</b> / admin123 · <b>hrofficer</b> / officer123 · <b>viewer</b> / viewer123
        </div>
      </form>
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState(undefined);
  const [page, setPage] = useState(() => location.hash.slice(1) || "dashboard");
  const [masters, setMasters] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => { api("auth/me/").then(setMe).catch(() => setMe(null)); }, []);
  useEffect(() => { location.hash = page; }, [page]);

  const loadMasters = useCallback(async () => {
    const [departments, designations, types, locations] = await Promise.all([
      api("departments/"), api("designations/"), api("employment-types/"), api("locations/"),
    ]);
    setMasters({ departments, designations, types, locations });
  }, []);
  useEffect(() => { if (me) loadMasters(); }, [me, loadMasters]);

  const notify = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3200);
  }, []);

  if (me === undefined) return null;
  if (!me) return <Login onLogin={setMe} />;
  if (!masters) return <div className="main">Loading…</div>;

  const logout = async () => {
    await api("auth/logout/", { method: "POST" });
    resetCsrf();
    setMe(null);
  };

  return (
    <AppCtx.Provider value={{ me, masters, notify, setPage }}>
      <div className="layout">
        <nav className="sidebar">
          <div className="brand">
            <div className="brand-mark">HR</div>
            <div><strong>Enterprise HRMS</strong><small>NexGen Holdings Ltd.</small></div>
          </div>
          {PAGES.map(([key, label, icon]) => (
            <button key={key} className={`nav-btn${page === key ? " active" : ""}`} onClick={() => setPage(key)}>
              <span aria-hidden>{icon}</span>{label}
            </button>
          ))}
          <div className="sidebar-foot">
            {me.full_name}<br />{me.role}
            <div><button className="btn small" onClick={logout}>Sign out</button></div>
          </div>
        </nav>
        <main className="main">
          {page === "dashboard" && <Dashboard />}
          {page === "employees" && <Employees key="active" />}
          {page === "archive" && <Employees key="archive" archived />}
          {page === "housing" && <Housing />}
          {page === "duties" && <Duties />}
          {page === "reports" && <Reports />}
          {page === "audit" && <AuditLog />}
        </main>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </AppCtx.Provider>
  );
}
