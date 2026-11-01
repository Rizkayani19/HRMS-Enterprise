import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { Bars } from "./components.jsx";
import { daysUntil, fmtDate } from "./util.js";

export default function Dashboard() {
  const [d, setD] = useState(null);
  useEffect(() => { api("dashboard/").then(setD); }, []);
  if (!d) return <p className="muted">Loading dashboard…</p>;
  const h = d.housing;
  return (
    <>
      <div className="page-head">
        <div><h1>Dashboard</h1><p>{d.org_name} — workforce at a glance</p></div>
      </div>
      <div className="grid kpis">
        <div className="card kpi"><h3>Headcount</h3><div className="v">{d.headcount}</div><div className="s">active employees</div></div>
        <div className="card kpi"><h3>On leave</h3><div className="v">{d.on_leave}</div><div className="s">{d.notice_period} serving notice</div></div>
        <div className="card kpi"><h3>Contracts due</h3><div className="v">{d.contracts_due.length}</div><div className="s">ending in 90 days</div></div>
        <div className="card kpi"><h3>Staff housing</h3><div className="v">{h.occupied}/{h.units}</div><div className="s">occupied · {h.waiting} waiting</div></div>
        <div className="card kpi"><h3>Exits this year</h3><div className="v">{d.exited_this_year}</div><div className="s">archived profiles</div></div>
      </div>
      <div className="grid two" style={{ marginTop: 14 }}>
        <div className="card"><h2 style={{ marginBottom: 12 }}>Strength by department</h2><Bars items={d.by_department} /></div>
        <div className="card">
          <h2 style={{ marginBottom: 12 }}>Employment type</h2><Bars items={d.by_type} />
          <h2 style={{ margin: "18px 0 12px" }}>Staff category</h2><Bars items={d.by_category} />
        </div>
        <div className="card">
          <h2 style={{ marginBottom: 10 }}>Contracts ending soon</h2>
          <table>
            <thead><tr><th>Employee</th><th>Department</th><th>Ends</th><th className="num">Days</th></tr></thead>
            <tbody>
              {d.contracts_due.map((e) => (
                <tr key={e.id}>
                  <td>{e.full_name}<div className="muted">{e.designation_title}</div></td>
                  <td>{e.department_name}</td><td>{fmtDate(e.contract_end)}</td>
                  <td className="num"><span className={`pill${daysUntil(e.contract_end) <= 30 ? " warn" : ""}`}>{daysUntil(e.contract_end)}</span></td>
                </tr>
              ))}
              {!d.contracts_due.length && <tr><td colSpan="4" className="muted">None in the next 90 days.</td></tr>}
            </tbody>
          </table>
          <h2 style={{ margin: "18px 0 10px" }}>Retiring in the next 12 months</h2>
          {d.retiring.length ? d.retiring.map((r) => (
            <div key={r.id} style={{ padding: "4px 0" }}>{r.full_name} <span className="muted">— {fmtDate(r.retirement_date)}</span></div>
          )) : <p className="muted">None.</p>}
        </div>
        <div className="card">
          <h2 style={{ marginBottom: 10 }}>Recent activity</h2>
          <ul className="timeline">
            {d.recent_activity.map((a, i) => (
              <li key={i}><b>{a.action.replaceAll("_", " ")}</b> — {a.detail}<div className="muted">{a.user} · {new Date(a.at).toLocaleString("en-GB")}</div></li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
