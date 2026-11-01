export const fmtDate = (v) =>
  v ? new Date(v + (v.length === 10 ? "T00:00:00" : "")).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";
export const fmtMoney = (v) => (v == null ? "—" : `Rs ${Number(v).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`);
export const todayISO = () => new Date().toISOString().slice(0, 10);
export const daysUntil = (v) => Math.round((new Date(v + "T00:00:00") - new Date(todayISO() + "T00:00:00")) / 86400000);
export const canWrite = (me) => me && (me.role === "HR Admin" || me.role === "HR Officer");
