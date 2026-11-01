import React, { useEffect, useState } from "react";
import { api } from "./api.js";

export default function AuditLog() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("audit-log/").then(setRows); }, []);
  return (
    <>
      <div className="page-head"><div><h1>Audit log</h1><p>Every lifecycle, housing, roster and bulk action, with who did it.</p></div></div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>When</th><th>User</th><th>Action</th><th>Detail</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id}><td>{new Date(r.created_at).toLocaleString("en-GB")}</td><td>{r.user}</td><td>{r.action.replaceAll("_", " ")}</td><td>{r.detail}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </>
  );
}
