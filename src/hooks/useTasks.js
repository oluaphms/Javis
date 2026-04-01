/**
 * useTasks.js — Hook customizado para gerenciamento de tarefas.
 */

import { useState, useCallback, useEffect } from "react";
import { tasks as tasksApi } from "../api";

export function useTasks() {
  const [taskList, setTaskList] = useState([]);
  const [summary, setSummary] = useState({ total: 0, pendentes: 0, em_progresso: 0, concluidas: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const [list, sum] = await Promise.all([tasksApi.list(), tasksApi.summary()]);
      setTaskList(list);
      setSummary(sum);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const createTask = useCallback(async (title, description = "", priority = "media") => {
    try {
      await tasksApi.create(title, description, priority);
      await fetchTasks();
    } catch (e) {
      setError(e.message);
    }
  }, [fetchTasks]);

  const completeTask = useCallback(async (id) => {
    try {
      await tasksApi.complete(id);
      await fetchTasks();
    } catch (e) {
      setError(e.message);
    }
  }, [fetchTasks]);

  const deleteTask = useCallback(async (id) => {
    try {
      await tasksApi.delete(id);
      await fetchTasks();
    } catch (e) {
      setError(e.message);
    }
  }, [fetchTasks]);

  const updateTaskStatus = useCallback(async (id, status) => {
    try {
      await tasksApi.update(id, { status });
      await fetchTasks();
    } catch (e) {
      setError(e.message);
    }
  }, [fetchTasks]);

  return {
    taskList,
    summary,
    loading,
    error,
    fetchTasks,
    createTask,
    completeTask,
    deleteTask,
    updateTaskStatus,
  };
}
