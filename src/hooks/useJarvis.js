/**
 * useJarvis.js — Hook central do assistente Jarvis.
 *
 * Integra:
 *   - Comunicação com o backend (api.js)
 *   - Voz no browser (useWebSpeech.js)
 *   - Gerenciamento de mensagens do chat
 *
 * Fluxo de voz:
 *   startListening → usuário fala → transcript atualiza em tempo real
 *   → silêncio → finalText → sendQuery(finalText) → resposta da IA
 *   → speak(resposta) → Jarvis fala a resposta
 */

import { useState, useCallback, useRef } from "react";
import { jarvis as jarvisApi } from "../api";
import { useWebSpeech } from "./useWebSpeech";
import { useJarvisSettings } from "../context/JarvisSettingsContext";

export function useJarvis() {
  const { systemPrompt, skills, voiceGender } = useJarvisSettings();
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: "assistant",
      text: "Olá! Sou o Jarvis. Como posso ajudar você hoje?",
      timestamp: new Date().toISOString(),
      source: "text",
    },
  ]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [speakReplies, setSpeakReplies] = useState(true); // toggle de voz nas respostas

  const speech = useWebSpeech();
  const loadingRef = useRef(false); // evita chamadas duplicadas

  const speakWithVoice = useCallback(
    (text, extra = {}) => speech.speak(text, { ...extra, voiceGender }),
    [speech, voiceGender]
  );

  // ─── Mensagens ─────────────────────────────────────────────────────────────

  const addMessage = useCallback((role, text, source = "text") => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        role,
        text,
        timestamp: new Date().toISOString(),
        source,   // "text" | "voice"
      },
    ]);
  }, []);

  // ─── Envio de Query ao Backend ─────────────────────────────────────────────

  const sendQuery = useCallback(
    async (text, source = "text") => {
      const cleaned = text?.trim();
      if (!cleaned || loadingRef.current) return;

      loadingRef.current = true;
      addMessage("user", cleaned, source);
      setLoading(true);
      setError(null);

      // Para a fala caso esteja falando
      speech.stopSpeaking();

      try {
        const data = await jarvisApi.query(cleaned, false, {
          systemPrompt,
          skills,
        });
        const reply = data.reply || "Não entendi. Pode repetir?";

        addMessage("assistant", reply, "text");

        // Exibe alerta se comando perigoso precisar de confirmação
        if (data.requires_confirm) {
          addMessage("system", "⚠️ Essa ação requer confirmação manual.");
        }

        // Jarvis fala a resposta se o modo de voz estiver ativo
        if (speakReplies && speech.supported.synthesis) {
          speakWithVoice(reply);
        }
      } catch (e) {
        const errMsg = `❌ Erro de conexão: ${e.message}. Verifique se o backend está rodando.`;
        setError(errMsg);
        addMessage("system", errMsg);
      } finally {
        setLoading(false);
        loadingRef.current = false;
      }
    },
    [addMessage, speech, speakReplies, systemPrompt, skills, speakWithVoice]
  );

  // ─── Voz: Iniciar Escuta ───────────────────────────────────────────────────

  const startVoiceInput = useCallback(() => {
    if (!speech.supported.recognition) {
      addMessage("system", "⚠️ Reconhecimento de voz não suportado. Use Chrome ou Edge.");
      return;
    }

    speech.startListening({
      onResult: (text) => {
        // Chamado automaticamente após silêncio ou stopListening()
        if (text?.trim()) {
          sendQuery(text, "voice");
        }
      },
      silenceMs: 2500,
    });
  }, [speech, sendQuery, addMessage]);

  // ─── Voz: Parar Escuta ─────────────────────────────────────────────────────

  const stopVoiceInput = useCallback(() => {
    speech.stopListening();
  }, [speech]);

  // ─── Toggle: Jarvis fala respostas ─────────────────────────────────────────

  const toggleSpeakReplies = useCallback(() => {
    setSpeakReplies((prev) => {
      if (prev) speech.stopSpeaking(); // para imediatamente se desligando
      return !prev;
    });
  }, [speech]);

  // ─── Limpar Histórico ──────────────────────────────────────────────────────

  const clearMessages = useCallback(() => {
    speech.stopSpeaking();
    speech.reset();
    setMessages([
      {
        id: Date.now(),
        role: "assistant",
        text: "Histórico limpo. Como posso ajudar?",
        timestamp: new Date().toISOString(),
        source: "text",
      },
    ]);
  }, [speech]);

  // ─── Retorno ───────────────────────────────────────────────────────────────

  return {
    // Chat
    messages,
    loading,
    error,
    sendQuery,
    clearMessages,

    // Voz — entrada
    listening: speech.listening,
    transcript: speech.transcript,       // texto parcial em tempo real
    sttError: speech.sttError,
    startVoiceInput,
    stopVoiceInput,

    // Voz — saída
    speaking: speech.speaking,
    speakReplies,
    toggleSpeakReplies,
    speak: speakWithVoice,
    stopSpeaking: speech.stopSpeaking,
    ttsError: speech.ttsError,

    // Suporte
    voiceSupported: speech.supported,
  };
}
