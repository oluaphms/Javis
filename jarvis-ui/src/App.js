/**
 * App.js — Componente raiz da aplicação Jarvis.
 * Monta o layout principal com StatusBar, ChatPanel e TasksPanel.
 */

import React from "react";
import "./App.css";
import StatusBar from "./components/StatusBar";
import ChatPanel from "./components/ChatPanel";
import TasksPanel from "./components/TasksPanel";

export default function App() {
  return (
    <div className="app">
      <StatusBar />
      <main className="app__main">
        <ChatPanel />
        <TasksPanel />
      </main>
    </div>
  );
}
