import React, { useEffect, useState } from "react";
import { api, download } from "./api.js";
import { useApp } from "./App.jsx";
import { canWrite } from "./util.js";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Duties() {
  const { me, notify } = useApp();
  const now = new Date();
  const [ym, setYm] = useState({ y: now.getFullYear(), m: now.getMonth() + 1 });
  const [rows, setRows] = useState([]);
  const [types, setTypes] = useState([]);
  const load = async () => {
    const [r, t] = await Promise.all([api(`duties/?year=${ym.y}&month=${ym.m}`), api("duty-types/")]);
    setRows(r); setTypes(t);
  };
  useEffect(() => { load(); }, [ym]);
  const shift = (d) => setYm(({ y, m }) => { const x = new Date(y, m - 1 + d, 1); return { y: x.getFullYear(), m: x.getMonth() + 1 }; });
  const generate = async (replace) => {
    const r = await api("duties/generate/", { method: "POST", body: { year: ym.y, month: ym.m, replace } });
    notify(`${r.created} duties assigned`); load();
  };
  const days = new Date(ym.y, ym.m, 0).getDate();
  const lead = (new Date(ym.y, ym.m - 1, 1).getDay() + 6) % 7;
  const label = new Date(ym.y, ym.m - 1, 1).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
  const tIndex = Object.fromEntries(types.map((t, i) => [t.id, i]));

  return (
    <>
      <div className="page-head">
        <div><h1>Duty roster</h1><p>Fair rotation: fewest duties first, within each duty's grade band; no one gets two duties on one day.</p></div>
        <div className="btn-row">
          <button className="btn" onClick={() => shift(-1)}>‹</button><b style={{ minWidth: 130, textAlign: "center" }}>{label}</b><button className="btn" onClick={() => shift(1)}>›</button>
          {canWrite(me) && <button className="btn primary" onClick={() => generate(false)}>Fill gaps</button>}
          {canWrite(me) && <button className="btn" onClick={() => generate(true)}>Regenerate month</button>}
          <button className="btn" onClick={() => download(`reports/duty-roster/pdf/?year=${ym.y}&month=${ym.m}`)}>PDF</button>
        </div>
      </div>
      <div className="btn-row" style={{ marginBottom: 10 }}>
        {types.map((t, i) => <span key={t.id} className={`legend t${i}`}>{t.name} · G-{t.min_grade}–{t.max_grade}{t.weekends_only ? " · weekends" : ""}</span>)}
      </div>
      <div className="cal">
        {DOW.map((d) => <div className="dow" key={d}>{d}</div>)}
        {Array.from({ length: lead }).map((_, i) => <div key={`x${i}`} />)}
        {Array.from({ length: days }, (_, i) => i + 1).map((d) => {
          const iso = `${ym.y}-${String(ym.m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
          const wd = (lead + d - 1) % 7;
          return (
            <div key={d} className={`day${wd >= 5 ? " weekend" : ""}`}>
              <div className="d">{d}</div>
              {rows.filter((r) => r.date === iso).map((r) => (
                <div key={r.id} className={`duty t${tIndex[r.duty_type]}`} title={`${r.duty_name}: ${r.full_name}, ${r.designation}`}>{r.full_name}</div>
              ))}
            </div>
          );
        })}
      </div>
    </>
  );
}
