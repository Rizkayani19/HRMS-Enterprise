import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { useApp } from "./App.jsx";
import { ErrorBox, Field, Modal, Select } from "./components.jsx";
import { canWrite, fmtDate, todayISO } from "./util.js";

export default function Housing() {
  const { me, notify } = useApp();
  const [units, setUnits] = useState([]);
  const [waiting, setWaiting] = useState([]);
  const [modal, setModal] = useState(null);
  const load = async () => {
    const [u, w] = await Promise.all([api("housing/units/"), api("housing/waiting-list/")]);
    setUnits(u); setWaiting(w);
  };
  useEffect(() => { load(); }, []);
  const blocks = [...new Set(units.map((u) => u.block))];
  const writable = canWrite(me);
  const occupied = units.filter((u) => u.occupant).length;

  return (
    <>
      <div className="page-head">
        <div><h1>Staff housing</h1><p>{occupied} of {units.length} units occupied · {waiting.length} on the waiting list</p></div>
      </div>
      <div className="grid two" style={{ gridTemplateColumns: "minmax(0,2fr) minmax(300px,1fr)" }}>
        <div className="grid">
          {blocks.map((b) => (
            <div className="card" key={b}>
              <h2 style={{ marginBottom: 10 }}>{b}</h2>
              <div className="units">
                {units.filter((u) => u.block === b).map((u) => (
                  <div key={u.id} className={`unit${u.occupant ? "" : " vacant"}${u.is_serviceable ? "" : " bad"}`}>
                    <div className="code">{u.code}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{u.category} · G-{u.min_grade}+</div>
                    <div style={{ margin: "6px 0", minHeight: 36 }}>
                      {!u.is_serviceable ? <span className="pill warn">Unserviceable</span>
                        : u.occupant ? <>{u.occupant.full_name}<div className="muted" style={{ fontSize: 12 }}>since {fmtDate(u.occupant.occupied_from)}</div></>
                        : <span className="muted">Vacant</span>}
                    </div>
                    {writable && u.is_serviceable && (u.occupant
                      ? <button className="btn small" onClick={() => setModal({ kind: "vacate", unit: u })}>Vacate</button>
                      : <button className="btn small primary" onClick={() => setModal({ kind: "allot", unit: u })}>Allot</button>)}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="card">
          <h2 style={{ marginBottom: 4 }}>Waiting list</h2>
          <p className="muted" style={{ marginTop: 0 }}>In seniority order of registration.</p>
          <table>
            <thead><tr><th>#</th><th>Employee</th><th>For</th><th>Since</th></tr></thead>
            <tbody>{waiting.map((w, i) => (
              <tr key={w.id}><td>{i + 1}</td><td>{w.full_name}<div className="muted">{w.designation} · G-{w.grade}</div></td><td>{w.category}</td><td>{fmtDate(w.registered_on)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </div>
      {modal && <HousingModal {...modal} waiting={waiting} onClose={() => setModal(null)}
        onDone={(msg) => { setModal(null); notify(msg); load(); }} />}
    </>
  );
}

function HousingModal({ kind, unit, waiting, onClose, onDone }) {
  const [emps, setEmps] = useState([]);
  const [emp, setEmp] = useState("");
  const [date, setDate] = useState(todayISO());
  const [err, setErr] = useState(null);
  useEffect(() => { if (kind === "allot") api("employees/").then(setEmps); }, [kind]);
  const eligible = emps.filter((e) => e.grade >= unit.min_grade);
  const top = waiting.find((w) => w.category === unit.category && w.grade >= unit.min_grade);
  const submit = async () => {
    try {
      if (kind === "allot") await api(`housing/units/${unit.id}/allot/`, { method: "POST", body: { employee: Number(emp), occupied_from: date } });
      else await api(`housing/units/${unit.id}/vacate/`, { method: "POST", body: { vacated_on: date } });
      onDone(kind === "allot" ? `${unit.code} allotted` : `${unit.code} vacated`);
    } catch (e) { setErr(e); }
  };
  return (
    <Modal title={`${kind === "allot" ? "Allot" : "Vacate"} ${unit.code}`} onClose={onClose}>
      <ErrorBox error={err} />
      {kind === "allot" && top && <div className="notice">Next eligible on the waiting list: <b>{top.full_name}</b> (since {fmtDate(top.registered_on)}). <button className="btn small" onClick={() => setEmp(String(top.employee))}>Select</button></div>}
      <div className="form">
        {kind === "allot" && <Field label={`Employee (grade ${unit.min_grade}+)`} full>
          <Select value={emp} onChange={setEmp} placeholder="Choose…" options={eligible.map((e) => ({ value: e.id, label: `${e.full_name} — ${e.designation_title}` }))} />
        </Field>}
        <Field label={kind === "allot" ? "Occupied from" : "Vacated on"}><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
      </div>
      <div className="btn-row" style={{ marginTop: 16, justifyContent: "flex-end" }}>
        <button className="btn" onClick={onClose}>Cancel</button><button className="btn primary" onClick={submit}>Confirm</button>
      </div>
    </Modal>
  );
}
