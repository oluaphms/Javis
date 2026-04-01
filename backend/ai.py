"""
ai.py — Motor de Inteligência Artificial do Jarvis.
Resiliente, multi-provedor e offline-first.
"""

import re
import random
import logging
import config
from typing import Optional

# Logger
logger = logging.getLogger(__name__)


def compose_prompt_for_llm(user_text: str, system_prompt: str = "", skills: str = "") -> str:
    """Junta skills, prompt do sistema e pedido atual para o modelo."""
    user_text = (user_text or "").strip()
    blocks = []
    if skills and skills.strip():
        blocks.append(f"Contexto e skills indicados pelo usuário:\n{skills.strip()}")
    if system_prompt and system_prompt.strip():
        blocks.append(f"Instruções permanentes (persona e regras):\n{system_prompt.strip()}")
    blocks.append(f"Pedido atual:\n{user_text}")
    return "\n\n---\n\n".join(blocks)

def has_api_key() -> bool:
    """Verifica se existe Gemini ou OpenAI configurada."""
    return bool(config.GEMINI_API_KEY or config.OPENAI_API_KEY)

def fallback_response(text: str) -> str:
    """NLP lite / Regras para respostas offline."""
    print("USANDO FALLBACK LOCAL")
    text = text.lower().strip()
    
    mapping = {
        r"\b(oi|olá|ola|bom dia|boa tarde|boa noite)\b": [
            "Olá! Como posso ajudar você hoje?",
            "Oi! Jarvis online. O que precisa?"
        ],
        r"\b(quem é você|quem e voce|seu nome)\b": [
            f"Sou o {config.JARVIS_NAME}, seu assistente pessoal."
        ],
        r"\b(o que você faz|ajuda|help|comandos)\b": [
            "Posso gerenciar tarefas, abrir programas e responder perguntas localmente!"
        ],
        r"\b(obrigado|valeu)\b": ["Disponha!", "Sempre às ordens!"],
        r"\b(tchau|até logo)\b": ["Até mais!", "Tchau! Estarei aqui."],
        r"\b(status|versão)\b": [f"Jarvis v{config.JARVIS_VERSION} operacional."]
    }

    for pattern, responses in mapping.items():
        if re.search(pattern, text):
            return random.choice(responses)

    return "Entendido. No momento estou operando localmente para garantir sua privacidade. Como posso ser útil?"

def get_ai_response(
    text: str,
    system_prompt: str = "",
    skills: str = "",
) -> str:
    """Tenta Gemini -> OpenAI -> Fallback Local (Sem falar de falta de chave)."""
    if not text.strip(): return "Diga algo, mestre."

    has_ctx = bool((system_prompt and system_prompt.strip()) or (skills and skills.strip()))
    llm_input = compose_prompt_for_llm(text, system_prompt, skills) if has_ctx else text.strip()

    # 1. Gemini
    if config.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(config.GEMINI_MODEL)
            print("USANDO GEMINI")
            response = model.generate_content(
                f"Seja curto e direto em português. Contexto abaixo quando houver.\n\n{llm_input}"
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Erro Gemini: {e}")

    # 2. OpenAI
    if config.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            print("USANDO OPENAI")
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": llm_input}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Erro OpenAI: {e}")

    # 3. Fallback (usa só o texto do usuário, sem montar bloco longo)
    return fallback_response(text)


# --- Compatibilidade ---
def process_query(text: str): return get_ai_response(text)

class AIResponseCompat:
    def __init__(self, text, provider, intent):
        self.text, self.provider, self.intent = text, provider, intent

def process_query_detailed(
    text: str,
    system_prompt: Optional[str] = None,
    skills: Optional[str] = None,
):
    reply = get_ai_response(text, system_prompt or "", skills or "")
    provider = "local"
    if "FALLBACK" not in reply: # heurística simplista para debug
        provider = "external" 
    return AIResponseCompat(reply, provider, "geral")

def get_ai_info():
    return {
        "active_provider": "gemini" if config.GEMINI_API_KEY else "local",
        "online_mode": has_api_key(),
        "available_providers": ["local"],
        "history_turns": 0,
        "version": config.JARVIS_VERSION
    }

def get_history(): return []
def clear_history(): pass
def detect_intent(text): return "geral"
