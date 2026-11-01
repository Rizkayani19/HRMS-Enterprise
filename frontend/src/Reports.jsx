import React, { useEffect, useState } from "react";
import { api, download } from "./api.js";

export default function Reports() {
  const [list, setList] = useState([]);
  const [active, setActive] = useState(null);
  const [data, setData] = useState(null);
  useEffect(() => { api("reports/").then((l) => { setList(l); setActive(l[0]?.key); }); }, []);
  useEffect(() => { if (active) { setData(null); api(`reports/${active}/`).then(setData); } }, [active]);
  return (
    <>
      <div className="page-head"><div><h1>Reports</h1><p>{list.length} built-in reports — preview here, export to PDF, Excel or CSV.</p></div></div>
      <div className="grid" style={{ gridTemplateColumns: "260px minmax(0,1fr)" }}>
        <div className="card" style={{ padding: 8, alignSelf: "start" }}>
          {list.map((r) => (
            <button key={r.key} className={`nav-btn${active === r.key ? " active" : ""}`} style={{ width: "100%", color: active === r.key ? "#fff" : "var(--text)", background: active === r.key ? "var(--navy)" : "none", display: "block" }}
              onClick={() => setActive(r.key)}>
              {r.title}<div style={{ fontSize: 11, opacity: .75 }}>{r.description}</div>
            </button>
          ))}
        </div>
        <div className="card">
          {!data ? <p className="muted">Loading…</p> : <>
            <div className="page-head" style={{ marginBottom: 10 }}>
              <div><h2>{data.title}</h2><p>{data.subtitle}</p></div>
              <div className="btn-row">
                <button className="btn primary" onClick={() => download(`reports/${active}/pdf/`)}>PDF</button>
                <button className="btn" onClick={() => download(`reports/${active}/xlsx/`)}>Excel</button>
                <button className="btn" onClick={() => download(`reports/${active}/csv/`)}>CSV</button>
              </div>
            </div>
            <div className="table-wrap" style={{ maxHeight: "calc(100vh - 260px)" }}>
              <table>
                <thead><tr>{data.columns.map((c) => <th key={c} className="nowrap">{c}</th>)}</tr></thead>
                <tbody>{data.rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j} className="nowrap">{String(v)}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </>}
        </div>
      </div>
    </>
  );
}
