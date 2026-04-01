/**
 * StatusBar.js — Barra de status do sistema Jarvis.
 */

import React, { useState, useEffect } from "react";
import { jarvis } from "../api";
import "./StatusBar.css";

export default function StatusBar() {
  const [status, setStatus] = useState(null);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    jarvis.status().then(setStatus).catch(() => setStatus({ status: "offline" }));
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="status-bar">
      <div className="status-bar__brand">
        <span className="status-bar__logo">⬡</span>
        <span className="status-bar__name">J.A.R.V.I.S</span>
        {status?.version && (
          <span className="status-bar__version">v{status.version}</span>
        )}
      </div>

      <div className="status-bar__indicators">
        <div className={`indicator ${status?.status === "online" ? "indicator--online" : "indicator--offline"}`}>
          <span className="indicator__dot" />
          {status?.status === "online" ? "Sistema Online" : "Conectando..."}
        </div>
        <div className="indicator">
          <span className="indicator__icon">🧠</span>
          {status?.ai_online ? "IA online" : "Modo local"}
        </div>
        <div className="indicator">
          <span className="indicator__icon">🎙️</span>
          {status?.voice_available ? "Voz OK" : "Voz N/A"}
        </div>
      </div>

      <div className="status-bar__time">
        {time.toLocaleTimeString("pt-BR")}
      </div>
    </div>
  );
}
