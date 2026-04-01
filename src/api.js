/**
 * api.js — Cliente HTTP centralizado para comunicação com o backend Jarvis.
 * Todos os acessos à API passam por aqui.
 *
 * Compatível com o backend Node (jarvis-ui/backend-node) e FastAPI (backend/).
 */

const BASE_URL = "/api";

async function request(method, path, body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
    const detail = err.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || d).join(", ")
          : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return res.json();
}

/** FastAPI devolve { message, tasks }; Node devolve array direto. */
function normalizeTaskList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.tasks)) return data.tasks;
  return [];
}

/** FastAPI devolve { message, data }; Node stub devolve { pending, completed }. */
function normalizeTaskSummary(data) {
  if (data && data.data && typeof data.data === "object") {
    const d = data.data;
    return {
      total: d.total ?? 0,
      pendentes: d.pendentes ?? 0,
      em_progresso: d.em_progresso ?? 0,
      concluidas: d.concluidas ?? 0,
    };
  }
  if (data && (typeof data.pending === "number" || typeof data.completed === "number")) {
    const p = data.pending ?? 0;
    const c = data.completed ?? 0;
    return {
      total: p + c,
      pendentes: p,
      em_progresso: 0,
      concluidas: c,
    };
  }
  return {
    total: data?.total ?? 0,
    pendentes: data?.pendentes ?? 0,
    em_progresso: data?.em_progresso ?? 0,
    concluidas: data?.concluidas ?? 0,
  };
}

/** FastAPI QueryResponse usa vários campos; garante reply para o chat. */
function normalizeQueryResponse(data) {
  if (!data || typeof data !== "object") return { reply: "" };
  return {
    reply: data.reply ?? "",
    requires_confirm: data.requires_confirm ?? false,
    ...data,
  };
}

// ─── Jarvis Core ──────────────────────────────────────────────────────────────

export const jarvis = {
  status: () => request("GET", "/jarvis/status"),
  /** opts: { systemPrompt, skills } — enviados ao backend como system_prompt e skills */
  query: (text, speak = false, opts = {}) =>
    request("POST", "/jarvis/query", {
      text,
      speak,
      system_prompt: opts.systemPrompt ?? "",
      skills: opts.skills ?? "",
    }).then(normalizeQueryResponse),
  listenVoice: () => request("GET", "/jarvis/voice/listen"),
  history: (limit = 50) => request("GET", `/jarvis/history?limit=${limit}`),
  clearHistory: () => request("POST", "/jarvis/clear-history"),
  commands: () => request("GET", "/jarvis/commands"),
};

// ─── Tarefas ──────────────────────────────────────────────────────────────────

export const tasks = {
  list: (status = null) => {
    const path = status
      ? `/tasks/?status=${encodeURIComponent(status)}`
      : `/tasks/`;
    return request("GET", path).then(normalizeTaskList);
  },
  summary: () => request("GET", "/tasks/summary").then(normalizeTaskSummary),
  create: (title, description = "", priority = "media") =>
    request("POST", "/tasks/", { title, description, priority }),
  update: (id, fields) => request("PATCH", `/tasks/${id}`, fields),
  complete: (id) => request("PATCH", `/tasks/${id}/complete`),
  delete: (id) => request("DELETE", `/tasks/${id}`),
};
