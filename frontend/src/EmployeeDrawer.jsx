import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { useApp } from "./App.jsx";
import { ErrorBox, Field, Modal, Select, Status } from "./components.jsx";
import { canWrite, fmtDate, fmtMoney, todayISO } from "./util.js";

const BLANK = {
  employee_no: "", full_name: "", father_name: "", national_id: "", gender: "Male", dob: "", blood_group: "",
  marital_status: "Single", mobile: "", email: "", office_ext: "", address: "", home_district: "", qualification: "",
  department: "", designation: "", employment_type: "", location: "", join_date: todayISO(), grade_seniority_date: "",
  contract_start: "", contract_end: "", basic_pay: "0", allowances: "0", remarks: "", family: [], previous_appointments: [],
};

const clean = (obj) => {
  const out = {};
  for (const [k, v] of Object.entries(obj)) out[k] = v === "" && /date|dob|contract_|location/.test(k) ? null : v;
  return out;
};

export default function EmployeeDrawer({ id, onClose, onChanged, onCreated }) {
  const { me } = useApp();
  const [emp, setEmp] = useState(id ? null : BLANK);
  const [tab, setTab] = useState(id ? "overview" : "edit");
  const [action, setAction] = useState(null);

  const load = () => id && api(`employees/${id}/`).then(setEmp);
  useEffect(() => { load(); }, [id]);
  useEffect(() => {
    const k = (e) => e.key === "Escape" && !action && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [action, onClose]);

  if (!emp) return <div className="overlay"><div className="drawer">Loading…</div></div>;
  const exited = emp.status === "Exited";
  const writable = canWrite(me) && !exited;
  const refreshed = (e) => { setEmp(e); onChanged(); };

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="drawer">
        <div className="page-head" style={{ marginBottom: 0 }}>
          <div>
            <h1>{id ? emp.full_name : "New employee"}</h1>
            {id && <p>{emp.employee_no} · {emp.designation_title} (G-{emp.grade}) · {emp.department_name} · <Status value={emp.status} /></p>}
          </div>
          <button className="btn" onClick={onClose}>Close</button>
        </div>
        {id && writable && (
          <div className="btn-row" style={{ marginTop: 12 }}>
            <button className="btn small" onClick={() => setAction("transfer")}>Transfer</button>
            <button className="btn small" onClick={() => setAction("promote")}>Promote</button>
            {emp.employment_type_name && emp.contract_end && <button className="btn small" onClick={() => setAction("extend")}>Extend contract</button>}
            <button className="btn small" onClick={() => setAction("type")}>Change employment type</button>
            <button className="btn small danger" onClick={() => setAction("exit")}>Exit / archive</button>
          </div>
        )}
        <div className="tabs">
          {id && <button className={`tab${tab === "overview" ? " active" : ""}`} onClick={() => setTab("overview")}>Overview</button>}
          {(writable || !id) && <button className={`tab${tab === "edit" ? " active" : ""}`} onClick={() => setTab("edit")}>{id ? "Edit profile" : "Profile"}</button>}
          {id && <button className={`tab${tab === "history" ? " active" : ""}`} onClick={() => setTab("history")}>Service history</button>}
        </div>
        {tab === "overview" && <Overview emp={emp} />}
        {tab === "edit" && <EditForm emp={emp} isNew={!id} onSaved={(e) => { if (!id) onCreated(e); else { refreshed(e); setTab("overview"); } }} />}
        {tab === "history" && <History emp={emp} />}
        {action && <ActionModal kind={action} emp={emp} onClose={() => setAction(null)} onDone={(e) => { setAction(null); refreshed(e); }} />}
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return <div><div className="muted" style={{ fontSize: 12 }}>{k}</div><div>{v || "—"}</div></div>;
}

function Overview({ emp }) {
  const h = emp.housing;
  return (
    <div className="grid">
      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Personal</h3>
        <div className="form">
          <Row k="Father's name" v={emp.father_name} /><Row k="National ID" v={emp.national_id} />
          <Row k="Date of birth" v={fmtDate(emp.dob)} /><Row k="Gender" v={emp.gender} />
          <Row k="Blood group" v={emp.blood_group} /><Row k="Marital status" v={emp.marital_status} />
          <Row k="Mobile" v={emp.mobile} /><Row k="Email" v={emp.email} />
          <Row k="Office extension" v={emp.office_ext} /><Row k="Home district" v={emp.home_district} />
          <Row k="Qualification" v={emp.qualification} /><Row k="Address" v={emp.address} />
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Employment</h3>
        <div className="form">
          <Row k="Employment type" v={emp.employment_type_name} /><Row k="Location" v={emp.location_name} />
          <Row k="Joined" v={fmtDate(emp.join_date)} /><Row k="Years of service" v={emp.years_of_service} />
          <Row k="Seniority in grade" v={fmtDate(emp.grade_seniority_date)} /><Row k="Retirement date" v={fmtDate(emp.retirement_date)} />
          <Row k="Contract" v={emp.contract_end ? `${fmtDate(emp.contract_start)} – ${fmtDate(emp.contract_end)}` : "—"} />
          <Row k="Basic / gross pay" v={`${fmtMoney(emp.basic_pay)} / ${fmtMoney(emp.gross_pay)}`} />
          <Row k="Staff housing" v={h ? (h.unit ? `${h.unit}, ${h.block} (since ${fmtDate(h.occupied_from)})` : `On waiting list (${h.category}) since ${fmtDate(h.waiting_since)}`) : "Not allotted"} />
        </div>
      </div>
      <div className="grid two">
        <div className="card">
          <h3 style={{ marginBottom: 10 }}>Family</h3>
          {emp.family.length ? emp.family.map((f) => <div key={f.id}>{f.relationship}: {f.name} {f.dob && <span className="muted">({fmtDate(f.dob)})</span>}</div>) : <p className="muted">None recorded.</p>}
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 10 }}>Earlier appointments</h3>
          {emp.previous_appointments.length ? emp.previous_appointments.map((a) => (
            <div key={a.id}>{a.title}, {a.organisation} <span className="muted">{fmtDate(a.from_date)} – {fmtDate(a.to_date)}</span></div>
          )) : <p className="muted">None recorded.</p>}
        </div>
      </div>
      {emp.exit_record && (
        <div className="card">
          <h3 style={{ marginBottom: 10 }}>Exit</h3>
          <div className="form">
            <Row k="Exit date" v={fmtDate(emp.exit_record.exit_date)} /><Row k="Category" v={emp.exit_record.category} />
            <Row k="Destination" v={emp.exit_record.destination} /><Row k="Reliever" v={emp.exit_record.reliever} />
            <Row k="Housing to vacate" v={emp.exit_record.housing_vacation_due ? "Yes — notice raised" : "No"} />
          </div>
        </div>
      )}
    </div>
  );
}

function History({ emp }) {
  const items = [
    ...emp.transfers.map((t) => ({ d: t.effective_date, t: `Transferred ${t.from_department} → ${t.to_department}`, s: [t.order_ref, t.reason] })),
    ...emp.promotions.map((p) => ({ d: p.effective_date, t: `Promoted ${p.from_designation} → ${p.to_designation}`, s: [p.order_ref] })),
    ...emp.contract_extensions.map((c) => ({ d: c.new_start, t: `Contract extended to ${fmtDate(c.new_end)}${c.pay_revised ? ` · pay ${fmtMoney(c.old_basic_pay)} → ${fmtMoney(c.new_basic_pay)}` : ""}`, s: [c.order_ref] })),
    ...emp.type_changes.map((c) => ({ d: c.effective_date, t: `Employment type ${c.from_type} → ${c.to_type}`, s: [c.order_ref] })),
    { d: emp.join_date, t: "Joined the organisation", s: [] },
  ].sort((a, b) => (a.d < b.d ? 1 : -1));
  return (
    <div className="card">
      <ul className="timeline">
        {items.map((i, n) => <li key={n}><b>{fmtDate(i.d)}</b> — {i.t}<div className="muted">{i.s.filter(Boolean).join(" · ")}</div></li>)}
      </ul>
    </div>
  );
}

function EditForm({ emp, isNew, onSaved }) {
  const { masters, notify } = useApp();
  const [f, setF] = useState(() => {
    const o = { ...BLANK };
    for (const k of Object.keys(BLANK)) if (emp[k] !== undefined && emp[k] !== null) o[k] = emp[k];
    return o;
  });
  const [err, setErr] = useState(null);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e?.target ? e.target.value : e }));
  const opts = (list, label) => list.map((x) => ({ value: x.id, label: label(x) }));
  const contractual = masters.types.find((t) => String(t.id) === String(f.employment_type))?.is_contractual;

  const save = async () => {
    setErr(null);
    try {
      const body = clean(f);
      body.family = f.family.map(({ id, ...r }) => clean(r));
      body.previous_appointments = f.previous_appointments.map(({ id, ...r }) => clean(r));
      const saved = isNew ? await api("employees/", { method: "POST", body }) : await api(`employees/${emp.id}/`, { method: "PUT", body });
      notify(isNew ? "Employee created" : "Profile saved");
      onSaved(saved);
    } catch (e) { setErr(e); }
  };

  const rows = (key, blank) => ({
    add: () => setF((x) => ({ ...x, [key]: [...x[key], blank] })),
    del: (i) => setF((x) => ({ ...x, [key]: x[key].filter((_, j) => j !== i) })),
    set: (i, k) => (e) => setF((x) => ({ ...x, [key]: x[key].map((r, j) => (j === i ? { ...r, [k]: e.target.value } : r)) })),
  });
  const fam = rows("family", { relationship: "Son", name: "", dob: "", is_dependent: true });
  const prev = rows("previous_appointments", { organisation: "", title: "", from_date: "", to_date: "" });

  return (
    <div className="grid">
      <ErrorBox error={err} />
      <div className="card form">
        <Field label="Employee no *"><input value={f.employee_no} onChange={set("employee_no")} /></Field>
        <Field label="Full name *"><input value={f.full_name} onChange={set("full_name")} /></Field>
        <Field label="Father's name"><input value={f.father_name} onChange={set("father_name")} /></Field>
        <Field label="National ID (13 digits, dashes removed automatically)"><input value={f.national_id} onChange={set("national_id")} placeholder="42101-1234567-1" /></Field>
        <Field label="Date of birth"><input type="date" value={f.dob || ""} onChange={set("dob")} /></Field>
        <Field label="Gender"><Select value={f.gender} onChange={set("gender")} options={["Male", "Female"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Marital status"><Select value={f.marital_status} onChange={set("marital_status")} options={["Single", "Married", "Widowed", "Divorced"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Blood group"><input value={f.blood_group} onChange={set("blood_group")} /></Field>
        <Field label="Mobile (03xxxxxxxxx)"><input value={f.mobile} onChange={set("mobile")} /></Field>
        <Field label="Email"><input value={f.email} onChange={set("email")} /></Field>
        <Field label="Office extension"><input value={f.office_ext} onChange={set("office_ext")} /></Field>
        <Field label="Home district"><input value={f.home_district} onChange={set("home_district")} /></Field>
        <Field label="Qualification"><input value={f.qualification} onChange={set("qualification")} /></Field>
        <Field label="Address" full><input value={f.address} onChange={set("address")} /></Field>
      </div>
      <div className="card form">
        <Field label="Department *"><Select value={f.department} onChange={set("department")} placeholder="Choose…" options={opts(masters.departments, (d) => d.name)} /></Field>
        <Field label="Designation *"><Select value={f.designation} onChange={set("designation")} placeholder="Choose…" options={opts(masters.designations, (d) => `${d.title} (G-${d.grade})`)} /></Field>
        <Field label="Employment type *"><Select value={f.employment_type} onChange={set("employment_type")} placeholder="Choose…" options={opts(masters.types, (t) => t.name)} /></Field>
        <Field label="Location"><Select value={f.location} onChange={set("location")} placeholder="—" options={opts(masters.locations, (l) => `${l.name}, ${l.city}`)} /></Field>
        <Field label="Join date *"><input type="date" value={f.join_date || ""} onChange={set("join_date")} /></Field>
        <Field label="Seniority in grade from"><input type="date" value={f.grade_seniority_date || ""} onChange={set("grade_seniority_date")} /></Field>
        {contractual && <Field label="Contract start"><input type="date" value={f.contract_start || ""} onChange={set("contract_start")} /></Field>}
        {contractual && <Field label="Contract end *"><input type="date" value={f.contract_end || ""} onChange={set("contract_end")} /></Field>}
        <Field label="Basic pay (Rs)"><input type="number" value={f.basic_pay} onChange={set("basic_pay")} /></Field>
        <Field label="Allowances (Rs)"><input type="number" value={f.allowances} onChange={set("allowances")} /></Field>
        <Field label="Remarks" full><textarea rows="2" value={f.remarks} onChange={set("remarks")} /></Field>
      </div>
      <div className="card">
        <div className="btn-row" style={{ justifyContent: "space-between", marginBottom: 8 }}><h3>Family</h3><button className="btn small" onClick={fam.add}>+ Add</button></div>
        <table><tbody>{f.family.map((r, i) => (
          <tr key={i}>
            <td><select value={r.relationship} onChange={fam.set(i, "relationship")}>{["Spouse", "Son", "Daughter", "Father", "Mother"].map((v) => <option key={v}>{v}</option>)}</select></td>
            <td><input value={r.name} onChange={fam.set(i, "name")} placeholder="Name" /></td>
            <td><input type="date" value={r.dob || ""} onChange={fam.set(i, "dob")} /></td>
            <td><button className="btn small danger" onClick={() => fam.del(i)}>Remove</button></td>
          </tr>))}</tbody></table>
      </div>
      <div className="card">
        <div className="btn-row" style={{ justifyContent: "space-between", marginBottom: 8 }}><h3>Earlier appointments</h3><button className="btn small" onClick={prev.add}>+ Add</button></div>
        <table><tbody>{f.previous_appointments.map((r, i) => (
          <tr key={i}>
            <td><input value={r.title} onChange={prev.set(i, "title")} placeholder="Title" /></td>
            <td><input value={r.organisation} onChange={prev.set(i, "organisation")} placeholder="Organisation" /></td>
            <td><input type="date" value={r.from_date || ""} onChange={prev.set(i, "from_date")} /></td>
            <td><input type="date" value={r.to_date || ""} onChange={prev.set(i, "to_date")} /></td>
            <td><button className="btn small danger" onClick={() => prev.del(i)}>Remove</button></td>
          </tr>))}</tbody></table>
      </div>
      <div className="btn-row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={save}>{isNew ? "Create employee" : "Save changes"}</button></div>
    </div>
  );
}

const ACTIONS = {
  transfer: { title: "Transfer to another department", path: "transfer" },
  promote: { title: "Promote", path: "promote" },
  extend: { title: "Extend contract", path: "extend-contract" },
  type: { title: "Change employment type", path: "change-type" },
  exit: { title: "Exit and archive", path: "exit" },
};

function ActionModal({ kind, emp, onClose, onDone }) {
  const { masters, notify } = useApp();
  const [f, setF] = useState({ effective_date: todayISO(), exit_date: todayISO(), category: "Resignation" });
  const [err, setErr] = useState(null);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e?.target ? e.target.value : e }));
  const submit = async () => {
    try {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));
      onDone(await api(`employees/${emp.id}/${ACTIONS[kind].path}/`, { method: "POST", body }));
      notify(`${ACTIONS[kind].title}: done`);
    } catch (e) { setErr(e); }
  };
  const date = <Field label="Effective date"><input type="date" value={f.effective_date} onChange={set("effective_date")} /></Field>;
  const order = <Field label="Order reference"><input value={f.order_ref || ""} onChange={set("order_ref")} /></Field>;
  return (
    <Modal title={`${ACTIONS[kind].title} — ${emp.full_name}`} onClose={onClose}>
      <ErrorBox error={err} />
      <div className="form">
        {kind === "transfer" && <>
          <Field label="To department" full><Select value={f.to_department} onChange={set("to_department")} placeholder="Choose…" options={masters.departments.filter((d) => d.id !== emp.department).map((d) => ({ value: d.id, label: d.name }))} /></Field>
          {date}{order}<Field label="Reason" full><input value={f.reason || ""} onChange={set("reason")} /></Field>
        </>}
        {kind === "promote" && <>
          <Field label="New designation" full><Select value={f.to_designation} onChange={set("to_designation")} placeholder="Choose…" options={masters.designations.filter((d) => d.grade > emp.grade).map((d) => ({ value: d.id, label: `${d.title} (G-${d.grade})` }))} /></Field>
          {date}{order}<Field label="New basic pay (optional)"><input type="number" value={f.new_basic_pay || ""} onChange={set("new_basic_pay")} /></Field>
        </>}
        {kind === "extend" && <>
          <p className="muted field full" style={{ margin: 0 }}>Current contract ends {fmtDate(emp.contract_end)}. Basic pay {fmtMoney(emp.basic_pay)}.</p>
          <Field label="New contract end"><input type="date" value={f.new_end || ""} onChange={set("new_end")} /></Field>
          <Field label="Revised basic pay (optional)"><input type="number" value={f.new_basic_pay || ""} onChange={set("new_basic_pay")} /></Field>
          {order}
        </>}
        {kind === "type" && <>
          <Field label="New employment type" full><Select value={f.to_type} onChange={set("to_type")} placeholder="Choose…" options={masters.types.filter((t) => t.id !== emp.employment_type).map((t) => ({ value: t.id, label: t.name }))} /></Field>
          {date}<Field label="Contract end (if contractual)"><input type="date" value={f.contract_end || ""} onChange={set("contract_end")} /></Field>{order}
        </>}
        {kind === "exit" && <>
          <Field label="Exit date"><input type="date" value={f.exit_date} onChange={set("exit_date")} /></Field>
          <Field label="Category"><Select value={f.category} onChange={set("category")} options={["Resignation", "Retirement", "Contract Ended", "Transfer to Group Company", "Termination"].map((v) => ({ value: v, label: v }))} /></Field>
          <Field label="Destination"><input value={f.destination || ""} onChange={set("destination")} /></Field>
          <Field label="Reliever"><input value={f.reliever || ""} onChange={set("reliever")} /></Field>
          <Field label="Handover notes" full><textarea rows="2" value={f.handover_notes || ""} onChange={set("handover_notes")} /></Field>
          {emp.housing?.unit && <div className="notice field full" style={{ margin: 0 }}>This employee holds housing unit {emp.housing.unit}. It will be marked vacated and a vacation notice flagged.</div>}
        </>}
      </div>
      <div className="btn-row" style={{ marginTop: 16, justifyContent: "flex-end" }}>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className={`btn ${kind === "exit" ? "danger" : "primary"}`} onClick={submit}>Confirm</button>
      </div>
    </Modal>
  );
}
