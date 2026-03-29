"""
voice.py — Módulo de síntese e reconhecimento de voz (Seguro para Nuvem).
Desativa sons nativos se estiver rodando em ambiente Serverless (Vercel).
"""

import logging
import os

logger = logging.getLogger(__name__)

# O backend na Vercel (Cloud) NÃO tem acesso ao microfone ou alto-falante do servidor.
# Toda a voz é processada no NAVEGADOR (Frontend).
# Estes métodos permanecem aqui como stubs para não quebrar os imports do router.

def synthesize(text: str) -> bool:
    """
    Sintetiza texto em voz.
    Nota: Em produção (Vercel), a fala é processada pelo SpeechSynthesis API do browser.
    """
    logger.info(f"Voz (Simulada no Server): {text[:30]}...")
    return True # Pretende que falou para não travar o fluxo

def listen(timeout: int = 5, phrase_limit: int = 10) -> dict:
    """
    Captura e reconhece a fala.
    Nota: Em produção, o microfone do servidor é desabilitado.
    """
    return {
        "success": False, 
        "text": "", 
        "error": "O microfone só é suportado no modo local ou via navegador."
    }

def is_voice_available() -> bool:
    """Verifica se o microfone está disponível (sempre falso na nuvem)."""
    return False if os.environ.get("VERCEL") else True
