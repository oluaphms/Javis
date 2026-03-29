/**
 * VoiceButton.js — Botão de microfone com visualizador de áudio animado.
 *
 * Estados visuais:
 *   idle       → ícone de microfone, cor accent
 *   listening  → anéis pulsantes, ondas animadas, "ouvindo..."
 *   speaking   → ícone de alto-falante animado
 *   disabled   → opaco, cursor not-allowed
 *   unsupported → aviso de browser incompatível
 */

import React from "react";
import "./VoiceButton.css";

// ─── Ícones SVG ───────────────────────────────────────────────────────────────

const IconMic = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" width="22" height="22">
    <rect x="9" y="2" width="6" height="12" rx="3" />
    <path d="M5 10a7 7 0 0 0 14 0" />
    <line x1="12" y1="19" x2="12" y2="22" />
    <line x1="8"  y1="22" x2="16" y2="22" />
  </svg>
);

const IconStop = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <rect x="5" y="5" width="14" height="14" rx="2" />
  </svg>
);

const IconSpeaker = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" width="22" height="22">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
  </svg>
);

const IconMicSlash = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" width="22" height="22">
    <line x1="1" y1="1" x2="23" y2="23" stroke="#f87171" />
    <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
    <path d="M15 9.34V4a3 3 0 0 0-5.94-.6" />
    <path d="M17 16.95A7 7 0 0 1 5 10v-1" />
    <path d="M19 10a7 7 0 0 1-.11 1.23" />
    <line x1="12" y1="19" x2="12" y2="22" />
    <line x1="8"  y1="22" x2="16" y2="22" />
  </svg>
);


// ─── Visualizador de Ondas ────────────────────────────────────────────────────

function SoundWaves() {
  return (
    <div className="sound-waves" aria-hidden="true">
      {[...Array(5)].map((_, i) => (
        <span key={i} className="sound-wave" style={{ animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  );
}


// ─── Componente Principal ─────────────────────────────────────────────────────

export default function VoiceButton({
  listening = false,
  speaking = false,
  disabled = false,
  supported = true,
  transcript = "",
  onStart,
  onStop,
  className = "",
}) {
  const isUnsupported = !supported;
  const isActive      = listening || speaking;

  const handleClick = () => {
    if (isUnsupported || disabled) return;
    if (listening) {
      onStop?.();
    } else {
      onStart?.();
    }
  };

  // Estado visual
  const state = isUnsupported
    ? "unsupported"
    : listening
    ? "listening"
    : speaking
    ? "speaking"
    : "idle";

  const titles = {
    idle:        "Clique para falar com o Jarvis",
    listening:   "Clique para parar de ouvir",
    speaking:    "Jarvis está falando...",
    unsupported: "Reconhecimento de voz não suportado (use Chrome ou Edge)",
  };

  return (
    <div className={`voice-btn-wrapper ${className}`}>
      <button
        id="voice-button"
        className={`voice-btn voice-btn--${state}`}
        onClick={handleClick}
        disabled={disabled || isUnsupported}
        title={titles[state]}
        aria-label={titles[state]}
        aria-pressed={listening}
      >
        {/* Anéis de pulso — só quando ouvindo */}
        {listening && (
          <>
            <span className="pulse-ring pulse-ring--1" aria-hidden="true" />
            <span className="pulse-ring pulse-ring--2" aria-hidden="true" />
          </>
        )}

        {/* Ícone central */}
        <span className="voice-btn__icon">
          {isUnsupported ? <IconMicSlash />
           : listening   ? <IconStop />
           : speaking    ? <IconSpeaker />
           : <IconMic />}
        </span>
      </button>

      {/* Transcript em tempo real */}
      {listening && (
        <div className="voice-transcript" role="status" aria-live="polite">
          <SoundWaves />
          <span className="voice-transcript__text">
            {transcript || "Ouvindo..."}
          </span>
        </div>
      )}

      {/* Label de estado */}
      {speaking && !listening && (
        <div className="voice-speaking-label" aria-live="polite">
          <span className="speaking-dot" /> Jarvis falando
        </div>
      )}
    </div>
  );
}
