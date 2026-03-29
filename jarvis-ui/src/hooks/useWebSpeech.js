/**
 * useWebSpeech.js — Hook completo de voz via Web Speech API nativa do browser.
 *
 * Funcionalidades:
 *   - Speech-to-Text:  SpeechRecognition (captura contínua ou única)
 *   - Text-to-Speech:  SpeechSynthesis (fala a resposta do Jarvis)
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

const STT_LANG    = "pt-BR";
const TTS_LANG    = "pt-BR";
const TTS_RATE    = 1.05;
const TTS_PITCH   = 1.0;
const TTS_VOLUME  = 1.0;

export function useWebSpeech() {
  const [listening, setListening]         = useState(false);
  const [transcript, setTranscript]       = useState("");
  const [, setFinalText]                  = useState(""); // finalText simplificado pois é via refluxo
  const [sttError, setSttError]           = useState(null);
  const [speaking, setSpeaking]           = useState(false);
  const [ttsError, setTtsError]           = useState(null);

  const recognizerRef     = useRef(null);
  const onResultRef       = useRef(null);
  const silenceTimerRef   = useRef(null);

  // ─── Funções Utilitárias Estabilizadas ──────────────────────────────────────

  const _clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const _stopRecognizer = useCallback(() => {
    _clearSilenceTimer();
    if (recognizerRef.current) {
      try { recognizerRef.current.stop(); } catch (_) {}
      recognizerRef.current = null;
    }
    setListening(false);
  }, [_clearSilenceTimer]);

  const _stopSpeaking = useCallback(() => {
    if (synthAPI?.speaking) synthAPI.cancel();
    setSpeaking(false);
  }, []);

  const _resetSilenceTimer = useCallback((recognizer, ms) => {
    _clearSilenceTimer();
    silenceTimerRef.current = setTimeout(() => {
      try { recognizer.stop(); } catch (_) {}
    }, ms);
  }, [_clearSilenceTimer]);


  // ─── Efeitos de Vida ────────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      _stopRecognizer();
      _stopSpeaking();
    };
  }, [_stopRecognizer, _stopSpeaking]);


  // ─── Speech-to-Text ───────────────────────────────────────────────────────

  const startListening = useCallback(({ onResult, silenceMs = 2500 } = {}) => {
    if (!SPEECH_SUPPORTED.recognition || listening) return;

    _stopSpeaking();
    onResultRef.current = onResult || null;
    setSttError(null);
    setTranscript("");

    const recognizer = new SpeechRecognitionAPI();
    recognizer.lang              = STT_LANG;
    recognizer.interimResults    = true;
    recognizer.maxAlternatives   = 1;
    recognizer.continuous        = false;

    recognizer.onresult = (event) => {
      let interim = "";
      let confirmed = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) confirmed += event.results[i][0].transcript;
        else interim += event.results[i][0].transcript;
      }
      setTranscript(confirmed || interim);
      if (confirmed) {
        setFinalText(confirmed); // Trigger local apenas
        _resetSilenceTimer(recognizer, silenceMs);
      }
    };

    recognizer.onstart = () => {
      setListening(true);
      _resetSilenceTimer(recognizer, silenceMs);
    };

    recognizer.onend = () => {
      _clearSilenceTimer();
      setListening(false);
      if (onResultRef.current && transcript) {
         onResultRef.current(transcript);
      }
    };

    recognizer.onerror = (event) => {
      _clearSilenceTimer();
      setListening(false);
      setSttError(`Erro STT: ${event.error}`);
    };

    recognizerRef.current = recognizer;
    recognizer.start();
  }, [listening, _stopSpeaking, _resetSilenceTimer, _clearSilenceTimer, transcript]);

  const stopListening = useCallback(() => {
    _stopRecognizer();
  }, [_stopRecognizer]);


  // ─── Text-to-Speech ───────────────────────────────────────────────────────

  const speak = useCallback((text, options = {}) => {
    if (!SPEECH_SUPPORTED.synthesis || !text?.trim()) return;

    synthAPI.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang   = options.lang   ?? TTS_LANG;
    utterance.rate   = options.rate   ?? TTS_RATE;
    utterance.pitch  = options.pitch  ?? TTS_PITCH;
    utterance.volume = options.volume ?? TTS_VOLUME;

    // Obtém vozes disponíveis
    const voices = synthAPI.getVoices();
    utterance.voice = voices.find(v => v.lang === utterance.lang) || voices[0];

    utterance.onstart = () => setSpeaking(true);
    utterance.onend   = () => {
      setSpeaking(false);
      options.onEnd?.();
    };
    utterance.onerror = () => setSpeaking(false);

    setTtsError(null);
    synthAPI.speak(utterance);
  }, []);

  const stopSpeaking = useCallback(() => {
    _stopSpeaking();
  }, [_stopSpeaking]);

  const reset = useCallback(() => {
    setSttError(null);
    setTtsError(null);
    setTranscript("");
  }, []);

  return {
    listening,
    transcript,
    sttError,
    startListening,
    stopListening,
    speaking,
    ttsError,
    speak,
    stopSpeaking,
    reset,
    supported: SPEECH_SUPPORTED,
  };
}
