/**
 * api.js — Cliente HTTP centralizado para comunicação com o backend Jarvis.
 * Todos os acessos à API passam por aqui.
 */

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

async function request(method, path, body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Jarvis Core ──────────────────────────────────────────────────────────────

export const jarvis = {
  status: () => request("GET", "/jarvis/status"),
  query: (text, speak = false) => request("POST", "/jarvis/query", { text, speak }),
  listenVoice: () => request("GET", "/jarvis/voice/listen"),
  history: (limit = 50) => request("GET", `/jarvis/history?limit=${limit}`),
  clearHistory: () => request("POST", "/jarvis/clear-history"),
  commands: () => request("GET", "/jarvis/commands"),
};

// ─── Tarefas ──────────────────────────────────────────────────────────────────

export const tasks = {
  list: (status = null) => request("GET", `/tasks/${status ? `?status=${status}` : ""}`),
  summary: () => request("GET", "/tasks/summary"),
  create: (title, description = "", priority = "media") =>
    request("POST", "/tasks/", { title, description, priority }),
  update: (id, fields) => request("PATCH", `/tasks/${id}`, fields),
  complete: (id) => request("PATCH", `/tasks/${id}/complete`),
  delete: (id) => request("DELETE", `/tasks/${id}`),
};
