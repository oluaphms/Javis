/**
 * ChatPanel.js — Painel de conversa com o Jarvis.
 * Integra voz via Web Speech API (useJarvis → useWebSpeech).
 */

import React, { useState, useRef, useEffect } from "react";
import { useJarvis } from "../hooks/useJarvis";
import VoiceButton from "./VoiceButton";
import "./ChatPanel.css";

// ─── Labels por papel ─────────────────────────────────────────────────────────

const ROLE_LABELS = {
  user:      "Você",
  assistant: "Jarvis",
  system:    "Sistema",
};

// ─── Bolha de mensagem ────────────────────────────────────────────────────────

function MessageBubble({ message, onSpeak }) {
  const isAssistant = message.role === "assistant";
  const isVoice     = message.source === "voice";

  return (
    <div className={`message message--${message.role}`}>
      <div className="message__header">
        <span className="message__role">
          {ROLE_LABELS[message.role]}
          {isVoice && " 🎙️"}
        </span>
        {/* Botão de re-escutar — só para respostas do assistente */}
        {isAssistant && onSpeak && (
          <button
            className="message__speak-btn"
            onClick={() => onSpeak(message.text)}
            title="Ouvir novamente"
            aria-label="Ouvir resposta"
          >
            🔊
          </button>
        )}
      </div>
      <p className="message__text">{message.text}</p>
      <span className="message__time">
        {new Date(message.timestamp).toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </span>
    </div>
  );
}

// ─── Componente Principal ─────────────────────────────────────────────────────

export default function ChatPanel() {
  const {
    messages,
    loading,
    sendQuery,
    clearMessages,

    // Voz — entrada
    listening,
    transcript,
    sttError,
    startVoiceInput,
    stopVoiceInput,

    // Voz — saída
    speaking,
    speakReplies,
    toggleSpeakReplies,
    speak,
    stopSpeaking,

    // Suporte
    voiceSupported,
  } = useJarvis();

  const [input, setInput]   = useState("");
  const bottomRef           = useRef(null);
  const inputRef            = useRef(null);

  // Auto-scroll ao receber nova mensagem
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Quando parar de ouvir, foca o input de texto
  useEffect(() => {
    if (!listening) inputRef.current?.focus();
  }, [listening]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    sendQuery(text, "text");
    setInput("");
  };

  const handleKeyDown = (e) => {
    // Ctrl+M → aciona microfone
    if (e.ctrlKey && e.key === "m") {
      e.preventDefault();
      if (listening) stopVoiceInput();
      else startVoiceInput();
    }
  };

  const isBlocked = loading || listening;

  return (
    <section className="chat-panel" onKeyDown={handleKeyDown}>

      {/* ── Header ── */}
      <div className="chat-panel__header">
        <div className="chat-panel__avatar">
          <div className={`avatar-ring ${(loading || listening || speaking) ? "avatar-ring--active" : ""}`}>
            <svg viewBox="0 0 100 100" className="avatar-svg">
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--accent)"
                strokeWidth="1" strokeDasharray="4 4" />
              <circle cx="50" cy="50" r="30" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
              <circle cx="50" cy="50" r="15" fill="var(--accent)" fillOpacity="0.15" />
              <text x="50" y="56" textAnchor="middle" fill="var(--accent)"
                fontSize="14" fontFamily="monospace">AI</text>
            </svg>
          </div>
        </div>

        <div className="chat-panel__header-info">
          <h2 className="chat-panel__title">J.A.R.V.I.S</h2>
          <p className="chat-panel__subtitle" aria-live="polite">
            {listening  ? "🎙️ Ouvindo..." :
             speaking   ? "🔊 Falando..."  :
             loading    ? "⏳ Processando..." :
             "Online"}
          </p>
        </div>

        <div className="chat-panel__header-actions">
          {/* Toggle de voz nas respostas */}
          <button
            className={`btn-icon ${speakReplies ? "btn-icon--active" : ""}`}
            onClick={toggleSpeakReplies}
            title={speakReplies ? "Desativar fala das respostas" : "Ativar fala das respostas"}
            aria-label="Toggle de voz"
            disabled={!voiceSupported.synthesis}
          >
            {speakReplies ? "🔊" : "🔇"}
          </button>

          {/* Parar fala */}
          {speaking && (
            <button
              className="btn-icon btn-icon--danger"
              onClick={stopSpeaking}
              title="Parar fala"
              aria-label="Parar fala do Jarvis"
            >
              ⏹
            </button>
          )}

          {/* Limpar histórico */}
          <button
            className="btn-icon"
            onClick={clearMessages}
            title="Limpar histórico"
            aria-label="Limpar histórico"
          >
            🗑️
          </button>
        </div>
      </div>

      {/* ── Avisos de erro de voz ── */}
      {sttError && (
        <div className="voice-error-banner" role="alert">
          ⚠️ {sttError}
        </div>
      )}

      {/* ── Mensagens ── */}
      <div className="chat-panel__messages" role="log" aria-label="Conversa com Jarvis">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onSpeak={msg.role === "assistant" ? speak : null}
          />
        ))}

        {/* Indicador de processamento */}
        {loading && (
          <div className="message message--assistant typing" aria-label="Jarvis digitando">
            <span /><span /><span />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Área de Input ── */}
      <div className="chat-panel__input-area">

        {/* Linha principal: botão de voz + campo de texto + enviar */}
        <form className="chat-panel__form" onSubmit={handleSubmit}>

          {/* Botão de Microfone */}
          <VoiceButton
            listening={listening}
            speaking={speaking}
            disabled={loading}
            supported={voiceSupported.recognition}
            transcript={transcript}
            onStart={startVoiceInput}
            onStop={stopVoiceInput}
          />

          {/* Campo de texto */}
          <input
            id="chat-input"
            ref={inputRef}
            className={`chat-panel__input ${listening ? "chat-panel__input--listening" : ""}`}
            type="text"
            placeholder={listening ? transcript || "Falando..." : "Digite ou pressione o microfone... (Ctrl+M)"}
            value={listening ? transcript : input}
            onChange={(e) => !listening && setInput(e.target.value)}
            disabled={isBlocked}
            autoComplete="off"
            aria-label="Mensagem para o Jarvis"
          />

          {/* Botão Enviar */}
          <button
            id="send-button"
            type="submit"
            className="btn-send"
            disabled={isBlocked || !input.trim()}
            aria-label="Enviar mensagem"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </form>

        {/* Dica de atalho */}
        <div className="chat-panel__hint">
          {voiceSupported.recognition
            ? "Ctrl+M para ativar microfone"
            : "⚠️ Reconhecimento de voz não disponível — use Chrome ou Edge"}
        </div>
      </div>
    </section>
  );
}
