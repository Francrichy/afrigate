export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "afrigate_token";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }

  if (!res.ok) {
    const message = (data && (data.detail || data.error)) || `Request failed (${res.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return data;
}

export const api = {
  register: (body) => request("/api/auth/register", { method: "POST", body, auth: false }),
  login: (body) => request("/api/auth/login", { method: "POST", body, auth: false }),

  listModels: () => request("/api/models", { auth: false }),

  listKeys: () => request("/api/keys"),
  createKey: (label) => request("/api/keys", { method: "POST", body: { label } }),
  revokeKey: (id) => request(`/api/keys/${id}`, { method: "DELETE" }),

  getWallet: () => request("/api/wallet"),
  getUsage: () => request("/api/wallet/usage"),

  createDeposit: (body) => request("/api/billing/deposit", { method: "POST", body }),
  depositStatus: (reference) => request(`/api/billing/deposit/${reference}`),

  adminListModels: () => request("/api/admin/models"),
  adminUpsertModel: (body) => request("/api/admin/models", { method: "POST", body }),
  adminSetAlias: (body) => request("/api/admin/models/alias", { method: "POST", body }),
  adminToggleModel: (slug, enabled) =>
    request(`/api/admin/models/${encodeURIComponent(slug)}/toggle?enabled=${enabled}`, { method: "POST" }),
  adminDeprecateModel: (slug, sunsetInDays = 180) =>
    request(`/api/admin/models/${encodeURIComponent(slug)}/deprecate?sunset_in_days=${sunsetInDays}`, { method: "POST" }),

  // Daily model-discovery feed ("new AI detected, here's advice")
  adminListSuggestions: (status = "new") => request(`/api/admin/suggestions?status=${status}`),
  adminDismissSuggestion: (id) => request(`/api/admin/suggestions/${id}/dismiss`, { method: "POST" }),
  adminPromoteSuggestion: (id, body) => request(`/api/admin/suggestions/${id}/promote`, { method: "POST", body }),
  adminRunDiscoveryNow: () => request("/api/admin/suggestions/run-now", { method: "POST" }),

  // Platform-wide settings (adjustable top-up fee %)
  adminGetSettings: () => request("/api/admin/settings"),
  adminUpdateSettings: (body) => request("/api/admin/settings", { method: "PUT", body }),

  // Direct call to the public gateway itself - used by the Playground.
  chatCompletion: async (apiKey, body) => {
    const res = await fetch(`${API_BASE}/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed.");
    return data;
  },
};
