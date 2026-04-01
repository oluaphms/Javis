/**
 * Painel: gênero da voz (TTS), prompt do sistema e skills/contexto.
 */

import React from "react";
import { useJarvisSettings } from "../context/JarvisSettingsContext";
import "./JarvisSettingsPanel.css";

export default function JarvisSettingsPanel() {
  const { systemPrompt, setSystemPrompt, skills, setSkills, voiceGender, setVoiceGender } =
    useJarvisSettings();

  return (
    <aside className="jarvis-settings" aria-label="Configurações do Jarvis">
      <h3 className="jarvis-settings__title">Personalização</h3>

      <div className="jarvis-settings__field">
        <label className="jarvis-settings__label" htmlFor="voice-gender">
          Voz (fala do assistente)
        </label>
        <select
          id="voice-gender"
          className="jarvis-settings__select"
          value={voiceGender}
          onChange={(e) => setVoiceGender(e.target.value)}
        >
          <option value="auto">Automática (padrão do sistema)</option>
          <option value="female">Feminina</option>
          <option value="male">Masculina</option>
        </select>
        <p className="jarvis-settings__hint">
          Depende das vozes instaladas no Windows/navegador; se não houver correspondência, usa tom
          ajustado por pitch.
        </p>
      </div>

      <div className="jarvis-settings__field">
        <label className="jarvis-settings__label" htmlFor="system-prompt">
          Prompt do sistema
        </label>
        <textarea
          id="system-prompt"
          className="jarvis-settings__textarea"
          rows={5}
          placeholder="Ex.: Você é um assistente técnico. Responda sempre com passos numerados. Não invente APIs."
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
        />
      </div>

      <div className="jarvis-settings__field">
        <label className="jarvis-settings__label" htmlFor="skills-context">
          Skills / contexto
        </label>
        <textarea
          id="skills-context"
          className="jarvis-settings__textarea"
          rows={6}
          placeholder="Ex.: Projeto: JAVIS. Stack: React + Node. Regras: priorizar segurança; citar arquivos quando falar de código."
          value={skills}
          onChange={(e) => setSkills(e.target.value)}
        />
        <p className="jarvis-settings__hint">
          Enviado junto com cada mensagem para a IA (Gemini/backend). Salvo automaticamente neste
          navegador.
        </p>
      </div>
    </aside>
  );
}
