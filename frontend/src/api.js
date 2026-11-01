// Small fetch wrapper: session cookie + CSRF token for Django REST Framework.
let csrfToken = null;

async function ensureCsrf() {
  if (!csrfToken) {
    const r = await fetch("/api/auth/csrf/", { credentials: "same-origin" });
    csrfToken = (await r.json()).csrfToken;
  }
  return csrfToken;
}

export class ApiError extends Error {
  constructor(status, data) {
    super(formatError(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

function formatError(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([k, v]) => `${k.replaceAll("_", " ")}: ${Array.isArray(v) ? v.join(" ") : typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" · ");
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = await ensureCsrf();
  }
  const r = await fetch(`/api/${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await r.text();
  const data = text ? JSON.parse(text) : null;
  if (!r.ok) throw new ApiError(r.status, data);
  return data;
}

export const resetCsrf = () => (csrfToken = null);
export const download = (path) => window.open(`/api/${path}`, "_blank");
