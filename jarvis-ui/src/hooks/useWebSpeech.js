/**
 * useWebSpeech.js — Hook completo de voz via Web Speech API nativa do browser.
 *
 * Funcionalidades:
 *   - Speech-to-Text:  SpeechRecognition API (captura contínua ou única)
 *   - Text-to-Speech:  SpeechSynthesis API (fala a resposta do Jarvis)
 *   - Compatibilidade: detecção automática com mensagens de erro claras
 *   - Idioma:          pt-BR por padrão
 *   - Transcript:      texto parcial e final em tempo real
 *
 * Uso:
 *   const { listening, transcript, startListening, stopListening, speak, supported } = useWebSpeech();
 */

import { useState, useEffect, useRef, useCallback } from "react";

// ─── Detecção de Suporte ──────────────────────────────────────────────────────

const SpeechRecognitionAPI =
  window.SpeechRecognition ||
  window.webkitSpeechRecognition ||
  null;

const synthAPI = window.speechSynthesis || null;

export const SPEECH_SUPPORTED = {
  recognition: Boolean(SpeechRecognitionAPI),
  synthesis: Boolean(synthAPI),
};

// ─── Configurações ────────────────────────────────────────────────────────────

const STT_LANG    = "pt-BR";   // idioma de reconhecimento
const TTS_LANG    = "pt-BR";   // idioma de síntese
const TTS_RATE    = 1.05;      // velocidade da fala (1.0 = normal)
const TTS_PITCH   = 1.0;       // tom da voz
const TTS_VOLUME  = 1.0;       // volume

// ─── Hook Principal ───────────────────────────────────────────────────────────

export function useWebSpeech() {
  // Estado de reconhecimento
  const [listening, setListening]         = useState(false);
  const [transcript, setTranscript]       = useState("");       // texto parcial em tempo real
  const [finalText, setFinalText]         = useState("");       // texto confirmado
  const [sttError, setSttError]           = useState(null);

  // Estado de síntese
  const [speaking, setSpeaking]           = useState(false);
  const [ttsError, setTtsError]           = useState(null);

  // Referências internas (evitam re-renders desnecessários)
  const recognizerRef     = useRef(null);
  const onResultRef       = useRef(null);     // callback externo ao finalizar
  const silenceTimerRef   = useRef(null);     // timer de silêncio automático


  // ─── Limpeza ao desmontar ─────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      _stopRecognizer();
      _stopSpeaking();
    };
  }, []);


  // ─── Speech-to-Text ───────────────────────────────────────────────────────

  /**
   * Inicia a captura de voz.
   *
   * @param {Object} options
   * @param {Function} options.onResult - callback(finalText: string) chamado ao finalizar
   * @param {number}  options.silenceMs - ms de silêncio para encerrar automaticamente (default 2500)
   */
  const startListening = useCallback(({ onResult, silenceMs = 2500 } = {}) => {
    if (!SPEECH_SUPPORTED.recognition) {
      setSttError("Reconhecimento de voz não suportado neste navegador. Use Chrome ou Edge.");
      return;
    }
    if (listening) return;

    // Para a síntese de voz (não falar e ouvir ao mesmo tempo)
    _stopSpeaking();

    onResultRef.current = onResult || null;
    setSttError(null);
    setTranscript("");
    setFinalText("");

    const recognizer = new SpeechRecognitionAPI();
    recognizer.lang              = STT_LANG;
    recognizer.interimResults    = true;   // mostra texto parcial em tempo real
    recognizer.maxAlternatives   = 1;
    recognizer.continuous        = false;  // para automaticamente após pausa

    // Evento: resultado (parcial ou final)
    recognizer.onresult = (event) => {
      let interim = "";
      let confirmed = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          confirmed += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      // Atualiza o transcript em tempo real
      setTranscript(confirmed || interim);

      // Se teve resultado final, reinicia o timer de silêncio
      if (confirmed) {
        setFinalText((prev) => (prev + " " + confirmed).trim());
        _resetSilenceTimer(recognizer, silenceMs);
      }
    };

    // Evento: início da escuta
    recognizer.onstart = () => {
      setListening(true);
      _resetSilenceTimer(recognizer, silenceMs);
    };

    // Evento: encerramento (por silêncio, .stop() ou erro)
    recognizer.onend = () => {
      _clearSilenceTimer();
      setListening(false);

      // Usa o estado mais recente via ref funcional
      setFinalText((current) => {
        if (current && onResultRef.current) {
          onResultRef.current(current);
        }
        return current;
      });
    };

    // Evento: erro
    recognizer.onerror = (event) => {
      _clearSilenceTimer();
      setListening(false);

      const msgs = {
        "not-allowed":    "Permissão de microfone negada. Habilite nas configurações do navegador.",
        "no-speech":      "Nenhuma fala detectada. Tente novamente.",
        "audio-capture":  "Microfone não encontrado ou inacessível.",
        "network":        "Erro de rede no reconhecimento. Verifique sua conexão.",
        "aborted":        null,   // cancelamento intencional — sem mensagem
      };

      const msg = msgs[event.error] ?? `Erro de reconhecimento: ${event.error}`;
      if (msg) setSttError(msg);
    };

    recognizerRef.current = recognizer;
    recognizer.start();
  }, [listening]);


  /**
   * Para a captura de voz manualmente.
   */
  const stopListening = useCallback(() => {
    _stopRecognizer();
  }, []);


  // ─── Text-to-Speech ───────────────────────────────────────────────────────

  /**
   * Fala um texto usando a SpeechSynthesis API.
   *
   * @param {string} text - texto a ser falado
   * @param {Object} options - { lang, rate, pitch, volume, onEnd }
   */
  const speak = useCallback((text, options = {}) => {
    if (!SPEECH_SUPPORTED.synthesis) {
      setTtsError("Síntese de voz não suportada neste navegador.");
      return;
    }
    if (!text?.trim()) return;

    // Cancela qualquer fala em andamento
    synthAPI.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang   = options.lang   ?? TTS_LANG;
    utterance.rate   = options.rate   ?? TTS_RATE;
    utterance.pitch  = options.pitch  ?? TTS_PITCH;
    utterance.volume = options.volume ?? TTS_VOLUME;

    // Tenta usar uma voz em português
    utterance.voice = _getBestVoice(utterance.lang);

    utterance.onstart = () => setSpeaking(true);
    utterance.onend   = () => {
      setSpeaking(false);
      options.onEnd?.();
    };
    utterance.onerror = (e) => {
      setSpeaking(false);
      if (e.error !== "interrupted") {
        setTtsError(`Erro na síntese: ${e.error}`);
      }
    };

    setTtsError(null);
    synthAPI.speak(utterance);
  }, []);


  /**
   * Para a fala imediatamente.
   */
  const stopSpeaking = useCallback(() => {
    _stopSpeaking();
    setSpeaking(false);
  }, []);


  /**
   * Limpa os erros e o transcript.
   */
  const reset = useCallback(() => {
    setSttError(null);
    setTtsError(null);
    setTranscript("");
    setFinalText("");
  }, []);


  // ─── Funções Privadas ─────────────────────────────────────────────────────

  function _stopRecognizer() {
    _clearSilenceTimer();
    if (recognizerRef.current) {
      try { recognizerRef.current.stop(); } catch (_) {}
      recognizerRef.current = null;
    }
  }

  function _stopSpeaking() {
    if (synthAPI?.speaking) synthAPI.cancel();
  }

  function _resetSilenceTimer(recognizer, ms) {
    _clearSilenceTimer();
    silenceTimerRef.current = setTimeout(() => {
      try { recognizer.stop(); } catch (_) {}
    }, ms);
  }

  function _clearSilenceTimer() {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }

  function _getBestVoice(lang) {
    const voices = synthAPI?.getVoices() ?? [];
    // Prioridade: voz exata → mesma língua → qualquer
    return (
      voices.find((v) => v.lang === lang) ||
      voices.find((v) => v.lang.startsWith(lang.split("-")[0])) ||
      null
    );
  }


  // ─── Retorno do Hook ──────────────────────────────────────────────────────

  return {
    // Reconhecimento
    listening,
    transcript,     // texto parcial em tempo real (para mostrar na UI)
    finalText,      // texto final confirmado
    sttError,
    startListening,
    stopListening,

    // Síntese
    speaking,
    ttsError,
    speak,
    stopSpeaking,

    // Geral
    reset,
    supported: SPEECH_SUPPORTED,
  };
}
