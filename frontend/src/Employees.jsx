import React, { useCallback, useEffect, useState } from "react";
import { api, download } from "./api.js";
import { useApp } from "./App.jsx";
import { ErrorBox, Field, Modal, Select, Status } from "./components.jsx";
import EmployeeDrawer from "./EmployeeDrawer.jsx";
import { canWrite, fmtDate, todayISO } from "./util.js";

const STATUSES = ["Active", "On Leave", "Notice Period"];

export default function Employees({ archived = false }) {
  const { me, masters, notify } = useApp();
  const [rows, setRows] = useState([]);
  const [filters, setFilters] = useState({ q: "", department: "", employment_type: "", status: "" });
  const [selected, setSelected] = useState(new Set());
  const [openId, setOpenId] = useState(null);
  const [bulk, setBulk] = useState(null);
  const [loading, setLoading] = useState(false);

  const query = useCallback(() => {
    const p = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
    if (archived) p.set("archived", "1");
    return p.toString();
  }, [filters, archived]);

  const load = useCallback(async () => {
    setLoading(true);
    setRows(await api(`employees/?${query()}`));
    setLoading(false);
  }, [query]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  const set = (k) => (v) => setFilters((f) => ({ ...f, [k]: v }));
  const toggle = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));
  const writable = canWrite(me) && !archived;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{archived ? "Archive" : "Employees"}</h1>
          <p>{archived ? "Exited employees, with their full history preserved." : "Search, filter, select and act on staff records."}</p>
        </div>
        {writable && <button className="btn primary" onClick={() => setOpenId("new")}>+ Add employee</button>}
      </div>

      <div className="toolbar">
        <input type="search" placeholder="Search name, employee no, ID, mobile…" value={filters.q} onChange={(e) => set("q")(e.target.value)} />
        <Select value={filters.department} onChange={set("department")} placeholder="All departments"
          options={masters.departments.map((d) => ({ value: d.id, label: d.name }))} />
        <Select value={filters.employment_type} onChange={set("employment_type")} placeholder="All types"
          options={masters.types.map((t) => ({ value: t.id, label: t.name }))} />
        {!archived && <Select value={filters.status} onChange={set("status")} placeholder="Any status"
          options={STATUSES.map((s) => ({ value: s, label: s }))} />}
        <span className="muted">{loading ? "Loading…" : `${rows.length} records`}</span>
      </div>

      {selected.size > 0 && (
        <div className="notice btn-row">
          <b>{selected.size} selected</b>
          {writable && <button className="btn small" onClick={() => setBulk("status")}>Change status</button>}
          {writable && <button className="btn small" onClick={() => setBulk("transfer")}>Transfer department</button>}
          <button className="btn small" onClick={() => download(`employees/export-csv/?${query()}&ids=${[...selected].join(",")}`)}>Export selected (CSV)</button>
          <button className="btn small" onClick={() => setSelected(new Set())}>Clear</button>
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 30 }}>
                <input type="checkbox" checked={allSelected} aria-label="Select all"
                  onChange={() => setSelected(allSelected ? new Set() : new Set(rows.map((r) => r.id)))} />
              </th>
              <th>Emp No</th><th>Name</th><th>Designation</th><th className="num">Grade</th><th>Department</th>
              <th>Type</th><th>Joined</th><th>{archived ? "Status" : "Contract ends"}</th>{!archived && <th>Status</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className={`clickable${selected.has(r.id) ? " selected" : ""}`} onClick={() => setOpenId(r.id)}>
                <td onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} aria-label={`Select ${r.full_name}`} /></td>
                <td className="nowrap">{r.employee_no}</td>
                <td><b>{r.full_name}</b><div className="muted">{r.location_name}</div></td>
                <td>{r.designation_title}</td><td className="num">{r.grade}</td><td>{r.department_name}</td>
                <td>{r.employment_type_name}</td><td>{fmtDate(r.join_date)}</td>
                <td>{archived ? <Status value={r.status} /> : r.contract_end ? fmtDate(r.contract_end) : <span className="muted">—</span>}</td>
                {!archived && <td><Status value={r.status} /></td>}
              </tr>
            ))}
            {!rows.length && !loading && <tr><td colSpan="10" className="muted">No matching employees.</td></tr>}
          </tbody>
        </table>
      </div>

      {openId && (
        <EmployeeDrawer id={openId === "new" ? null : openId} onClose={() => setOpenId(null)}
          onChanged={() => load()} onCreated={(e) => { setOpenId(e.id); load(); }} />
      )}
      {bulk && (
        <BulkModal kind={bulk} ids={[...selected]} onClose={() => setBulk(null)}
          onDone={(n) => { setBulk(null); setSelected(new Set()); notify(`${n} employees updated`); load(); }} />
      )}
    </>
  );
}

function BulkModal({ kind, ids, onClose, onDone }) {
  const { masters } = useApp();
  const [status, setStatus] = useState("On Leave");
  const [dept, setDept] = useState("");
  const [date, setDate] = useState(todayISO());
  const [order, setOrder] = useState("");
  const [err, setErr] = useState(null);
  const submit = async () => {
    try {
      const body = kind === "status"
        ? { ids, action: "status", status }
        : { ids, action: "transfer", to_department: Number(dept), effective_date: date, order_ref: order };
      onDone((await api("employees/bulk/", { method: "POST", body })).updated);
    } catch (e) { setErr(e); }
  };
  return (
    <Modal title={kind === "status" ? `Change status of ${ids.length} employees` : `Transfer ${ids.length} employees`} onClose={onClose}>
      <ErrorBox error={err} />
      <div className="form">
        {kind === "status" ? (
          <Field label="New status" full><Select value={status} onChange={setStatus} options={STATUSES.map((s) => ({ value: s, label: s }))} /></Field>
        ) : (
          <>
            <Field label="To department" full><Select value={dept} onChange={setDept} placeholder="Choose…" options={masters.departments.map((d) => ({ value: d.id, label: d.name }))} /></Field>
            <Field label="Effective date"><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
            <Field label="Order reference"><input value={order} onChange={(e) => setOrder(e.target.value)} /></Field>
          </>
        )}
      </div>
      <div className="btn-row" style={{ marginTop: 16, justifyContent: "flex-end" }}>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn primary" onClick={submit}>Apply</button>
      </div>
    </Modal>
  );
}
