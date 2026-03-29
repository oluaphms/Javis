"""
voice.py — Módulo de síntese e reconhecimento de voz.
Usa pyttsx3 para síntese (offline) e SpeechRecognition para captura.
"""

import logging
import threading
from config import VOICE_LANGUAGE, VOICE_RATE, VOICE_VOLUME

logger = logging.getLogger(__name__)

# ─── Síntese de Voz (Text-to-Speech) ─────────────────────────────────────────

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    """Retorna o motor de síntese (singleton com thread-safety)."""
    global _engine
    if _engine is None:
        try:
            import pyttsx3
            _engine = pyttsx3.init()
            _engine.setProperty("rate", VOICE_RATE)
            _engine.setProperty("volume", VOICE_VOLUME)
            # Tenta configurar voz em português
            voices = _engine.getProperty("voices")
            for voice in voices:
                if "brazil" in voice.name.lower() or "portugal" in voice.name.lower():
                    _engine.setProperty("voice", voice.id)
                    break
        except Exception as e:
            logger.warning(f"Motor de voz indisponível: {e}")
            _engine = None
    return _engine


def synthesize(text: str) -> bool:
    """
    Sintetiza texto em voz.
    Retorna True se bem-sucedido, False caso contrário.
    """
    with _engine_lock:
        engine = _get_engine()
        if engine is None:
            logger.warning("Text-to-speech indisponível.")
            return False
        try:
            engine.say(text)
            engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Erro na síntese de voz: {e}")
            return False


# ─── Reconhecimento de Voz (Speech-to-Text) ──────────────────────────────────

def listen(timeout: int = 5, phrase_limit: int = 10) -> dict:
    """
    Captura e reconhece a fala do microfone.

    Args:
        timeout: segundos para esperar o início da fala
        phrase_limit: segundos máximos de captura

    Returns:
        {"success": bool, "text": str, "error": str | None}
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 3000
        recognizer.dynamic_energy_threshold = True

        with sr.Microphone() as source:
            logger.info("Ajustando ruído ambiente...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("Ouvindo...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

        text = recognizer.recognize_google(audio, language=VOICE_LANGUAGE)
        logger.info(f"Reconhecido: '{text}'")
        return {"success": True, "text": text, "error": None}

    except Exception as e:
        err_class = type(e).__name__
        if "WaitTimeoutError" in err_class:
            msg = "Nenhuma fala detectada. Tente novamente."
        elif "UnknownValueError" in err_class:
            msg = "Não consegui entender. Fale mais claramente."
        elif "RequestError" in err_class:
            msg = "Serviço de reconhecimento de voz indisponível."
        else:
            msg = f"Erro: {str(e)}"
        logger.warning(f"Reconhecimento falhou: {msg}")
        return {"success": False, "text": "", "error": msg}


def is_voice_available() -> bool:
    """Verifica se o microfone está disponível."""
    try:
        import speech_recognition as sr
        with sr.Microphone():
            return True
    except Exception:
        return False
