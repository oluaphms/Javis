/**
 * TasksPanel.js — Painel de gerenciamento de tarefas.
 */

import React, { useState } from "react";
import { useTasks } from "../hooks/useTasks";
import "./TasksPanel.css";

const PRIORITY_COLORS = { baixa: "#4ade80", media: "#facc15", alta: "#f87171" };
const PRIORITY_LABELS = { baixa: "Baixa", media: "Média", alta: "Alta" };
const STATUS_LABELS = {
  pendente: "Pendente",
  em_progresso: "Em andamento",
  concluida: "Concluída",
};

function TaskCard({ task, onComplete, onDelete, onStatusChange }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`task-card task-card--${task.priority} ${task.status === "concluida" ? "task-card--done" : ""}`}>
      <div className="task-card__header" onClick={() => setExpanded(!expanded)}>
        <span
          className="task-card__priority"
          style={{ background: PRIORITY_COLORS[task.priority] }}
          title={PRIORITY_LABELS[task.priority]}
        />
        <p className="task-card__title">{task.title}</p>
        <span className="task-card__status">{STATUS_LABELS[task.status]}</span>
        <span className="task-card__chevron">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div className="task-card__body">
          {task.description && <p className="task-card__desc">{task.description}</p>}
          <p className="task-card__meta">
            Criada em {new Date(task.created_at).toLocaleDateString("pt-BR")}
          </p>

          <div className="task-card__actions">
            <select
              value={task.status}
              onChange={(e) => onStatusChange(task.id, e.target.value)}
              className="task-card__select"
            >
              <option value="pendente">Pendente</option>
              <option value="em_progresso">Em andamento</option>
              <option value="concluida">Concluída</option>
            </select>
            {task.status !== "concluida" && (
              <button className="btn-complete" onClick={() => onComplete(task.id)}>
                ✓ Concluir
              </button>
            )}
            <button className="btn-delete" onClick={() => onDelete(task.id)}>
              🗑
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function TasksPanel() {
  const { taskList, summary, loading, createTask, completeTask, deleteTask, updateTaskStatus } = useTasks();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", priority: "media" });
  const [filter, setFilter] = useState("all");

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    await createTask(form.title, form.description, form.priority);
    setForm({ title: "", description: "", priority: "media" });
    setShowForm(false);
  };

  const filtered = filter === "all" ? taskList : taskList.filter((t) => t.status === filter);

  return (
    <section className="tasks-panel">
      {/* Header */}
      <div className="tasks-panel__header">
        <h2 className="tasks-panel__title">📋 Tarefas</h2>
        <button
          id="new-task-btn"
          className="btn-new-task"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? "✕ Fechar" : "+ Nova"}
        </button>
      </div>

      {/* Summary */}
      <div className="tasks-summary">
        <div className="summary-item">
          <span className="summary-num">{summary.total}</span>
          <span>Total</span>
        </div>
        <div className="summary-item summary-item--yellow">
          <span className="summary-num">{summary.pendentes}</span>
          <span>Pendentes</span>
        </div>
        <div className="summary-item summary-item--blue">
          <span className="summary-num">{summary.em_progresso}</span>
          <span>Andamento</span>
        </div>
        <div className="summary-item summary-item--green">
          <span className="summary-num">{summary.concluidas}</span>
          <span>Concluídas</span>
        </div>
      </div>

      {/* Create Form */}
      {showForm && (
        <form className="task-form" onSubmit={handleCreate}>
          <input
            id="task-title-input"
            className="task-form__input"
            type="text"
            placeholder="Título da tarefa..."
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
            autoFocus
          />
          <textarea
            className="task-form__input task-form__textarea"
            placeholder="Descrição (opcional)..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={2}
          />
          <div className="task-form__row">
            <select
              className="task-form__select"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
            >
              <option value="baixa">Prioridade Baixa</option>
              <option value="media">Prioridade Média</option>
              <option value="alta">Prioridade Alta</option>
            </select>
            <button id="create-task-submit" type="submit" className="btn-create">
              Criar
            </button>
          </div>
        </form>
      )}

      {/* Filter */}
      <div className="tasks-filter">
        {["all", "pendente", "em_progresso", "concluida"].map((f) => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? "filter-btn--active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "Todas" : STATUS_LABELS[f]}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="tasks-list">
        {loading && <p className="tasks-empty">Carregando...</p>}
        {!loading && filtered.length === 0 && (
          <p className="tasks-empty">Nenhuma tarefa encontrada.</p>
        )}
        {filtered.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onComplete={completeTask}
            onDelete={deleteTask}
            onStatusChange={updateTaskStatus}
          />
        ))}
      </div>
    </section>
  );
}
