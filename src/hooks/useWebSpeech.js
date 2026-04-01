/**
 * useWebSpeech.js — Hook completo de voz via Web Speech API nativa do browser.
 *
 * Funcionalidades:
 *   - Speech-to-Text:  SpeechRecognition (captura contínua ou única)
 *   - Text-to-Speech:  SpeechSynthesis (fala a resposta do Jarvis)
 *
 * Nota: no Chrome/Edge o STT em pt-BR usa serviço em nuvem; erro "network"
 * indica falha de rede/firewall/VPN ao contatar esse serviço.
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

const STT_LANG = "pt-BR";

const FEMALE_NAME = /female|feminino|feminina|mulher|woman|maria|helena|zira|francisca|luciana|camila|juliana|vit[oó]ria|\bana\b/i;
const MALE_NAME = /male|masculino|masculina|homem|man|daniel|jorge|paulo|thiago|henrique|david|antonio|felipe|bruno|james/i;

function isPtVoice(v) {
  const L = (v.lang || "").toLowerCase();
  return L.startsWith("pt") || L === "pt-br";
}

function soundsFemale(v) {
  return v && FEMALE_NAME.test(v.name);
}

function soundsMale(v) {
  return v && MALE_NAME.test(v.name);
}

/** Escolhe SpeechSynthesisVoice conforme gênero (heurística por nome do sistema). */
function pickVoiceForGender(voices, gender) {
  if (!voices?.length) return null;
  const pt = voices.filter(isPtVoice);
  const pool = pt.length ? pt : voices;

  if (gender === "auto") {
    return (
      pool.find((v) => v.lang === "pt-BR" && (v.name.includes("Google") || v.name.includes("Natural"))) ||
      pool.find((v) => v.lang === "pt-BR") ||
      pool[0] ||
      voices[0]
    );
  }

  if (gender === "female") {
    const f = pool.find(soundsFemale);
    if (f) return f;
    return pool[0] || voices[0];
  }

  if (gender === "male") {
    const m = pool.find(soundsMale);
    if (m) return m;
    const notFemale = pool.find((v) => !soundsFemale(v));
    return notFemale || pool[0] || voices[0];
  }

  return pool[0] || voices[0];
}

/** Mensagens para SpeechRecognitionErrorEvent.error (códigos em inglês). */
function messageForSttError(code) {
  const messages = {
    network:
      "Voz indisponível: o navegador não alcançou o serviço de reconhecimento. Teste outra rede ou desative VPN/firewall para speech.google.com.",
    "not-allowed":
      "Permissão do microfone negada. Permita o acesso nas configurações do site.",
    "audio-capture":
      "Microfone não encontrado ou não acessível.",
    "no-speech":
      "Nenhuma fala detectada. Tente falar mais alto ou mais perto do microfone.",
    "service-not-allowed":
      "O navegador bloqueou o reconhecimento de voz neste contexto.",
    "bad-grammar": "Erro interno do reconhecimento de voz.",
    "language-not-supported":
      "Idioma não suportado pelo serviço de voz neste navegador.",
  };
  return messages[code] ?? `Erro de reconhecimento de voz (${code}).`;
}

export function useWebSpeech() {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [, setFinalText] = useState("");
  const [sttError, setSttError] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [ttsError, setTtsError] = useState(null);

  const recognizerRef = useRef(null);
  const onResultRef = useRef(null);
  const silenceTimerRef = useRef(null);
  /** Último texto reconhecido (onend não pode usar state — closure desatualizado). */
  const transcriptRef = useRef("");

  const _clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const _stopRecognizer = useCallback(() => {
    _clearSilenceTimer();
    if (recognizerRef.current) {
      try {
        recognizerRef.current.stop();
      } catch (_) {}
      recognizerRef.current = null;
    }
    setListening(false);
  }, [_clearSilenceTimer]);

  const _stopSpeaking = useCallback(() => {
    if (synthAPI?.speaking) synthAPI.cancel();
    setSpeaking(false);
  }, []);

  const _resetSilenceTimer = useCallback(
    (recognizer, ms) => {
      _clearSilenceTimer();
      silenceTimerRef.current = setTimeout(() => {
        try {
          recognizer.stop();
        } catch (_) {}
      }, ms);
    },
    [_clearSilenceTimer]
  );

  useEffect(() => {
    return () => {
      _stopRecognizer();
      _stopSpeaking();
    };
  }, [_stopRecognizer, _stopSpeaking]);

  const startListening = useCallback(
    ({ onResult, silenceMs = 2500 } = {}) => {
      if (!SPEECH_SUPPORTED.recognition || listening) return;

      _stopSpeaking();
      onResultRef.current = onResult || null;
      setSttError(null);
      setTranscript("");
      transcriptRef.current = "";

      const recognizer = new SpeechRecognitionAPI();
      recognizer.lang = STT_LANG;
      recognizer.interimResults = true;
      recognizer.maxAlternatives = 1;
      recognizer.continuous = false;

      recognizer.onresult = (event) => {
        let interim = "";
        let confirmed = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) confirmed += event.results[i][0].transcript;
          else interim += event.results[i][0].transcript;
        }
        const text = (confirmed || interim).trim();
        transcriptRef.current = text;
        setTranscript(confirmed || interim);
        if (confirmed) {
          setFinalText(confirmed);
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
        const final = transcriptRef.current?.trim();
        if (onResultRef.current && final) {
          onResultRef.current(final);
        }
        transcriptRef.current = "";
      };

      recognizer.onerror = (event) => {
        _clearSilenceTimer();
        setListening(false);
        if (event.error === "aborted") {
          setSttError(null);
          return;
        }
        setSttError(messageForSttError(event.error));
      };

      recognizerRef.current = recognizer;
      recognizer.start();
    },
    [listening, _stopSpeaking, _resetSilenceTimer, _clearSilenceTimer]
  );

  const stopListening = useCallback(() => {
    _stopRecognizer();
  }, [_stopRecognizer]);

  useEffect(() => {
    if (!synthAPI) return;
    const loadVoices = () => synthAPI.getVoices();
    loadVoices();
    synthAPI.onvoiceschanged = loadVoices;
    return () => {
      if (synthAPI) synthAPI.onvoiceschanged = null;
    };
  }, []);

  const speak = useCallback((text, options = {}) => {
    if (!synthAPI || !text?.trim()) return;

    synthAPI.cancel();
    const utterance = new SpeechSynthesisUtterance(text);

    utterance.lang = "pt-BR";
    utterance.rate = options.rate ?? 0.95;
    utterance.pitch = options.pitch ?? 1;
    utterance.volume = options.volume ?? 1.0;

    const voices = synthAPI.getVoices();
    const gender = options.voiceGender || "auto";
    const voz = pickVoiceForGender(voices, gender);
    if (voz) utterance.voice = voz;

    if (gender === "female" && !soundsFemale(voz)) {
      utterance.pitch = Math.min(1.15, (options.pitch ?? 1) * 1.08);
    } else if (gender === "male" && !soundsMale(voz)) {
      utterance.pitch = Math.max(0.82, (options.pitch ?? 1) * 0.92);
    }

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => {
      setSpeaking(false);
      options.onEnd?.();
    };
    utterance.onerror = (e) => {
      console.error("Erro TTS:", e);
      setSpeaking(false);
    };

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
