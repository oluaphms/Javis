"""
config.py — Configurações centralizadas do Jarvis.
Altere as variáveis aqui para personalizar o comportamento do sistema.
"""

import os
from pathlib import Path

# Carrega .env do diretório do backend
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass  # python-dotenv não instalado, usa variáveis de ambiente do sistema

# ─── Banco de dados ───────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'tasks.db')

# Supabase (Modo Vendável)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
DB_ONLINE = bool(SUPABASE_URL and SUPABASE_KEY)

# ─── Servidor ─────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8008

# ─── IA: Configuração de Providers ───────────────────────────────────────────
#
# Provider ativo e ordem de prioridade:
#   1. Google Gemini  → PROVIDER PRINCIPAL (gratuito: aistudio.google.com/apikey)
#   2. OpenAI         → se OPENAI_API_KEY estiver definida
#   3. Groq           → se GROQ_API_KEY estiver definida  (gratuito, ultra-rápido)
#   4. Fallback Local → sempre disponível, sem internet
#
# ──────────────────────────────────────────────────────────────────────────────
# ★  INSIRA SUA CHAVE GEMINI AQUI (ou defina a variável de ambiente):
# ──────────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY",  "")  # ← Cole sua chave aqui

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY",  "")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY",    "")

# Modelos padrão de cada provider
GEMINI_MODEL    = os.getenv("GEMINI_MODEL",  "gemini-1.5-flash")  # rápido e gratuito
OPENAI_MODEL    = os.getenv("OPENAI_MODEL",  "gpt-3.5-turbo")
GROQ_MODEL      = os.getenv("GROQ_MODEL",    "llama3-8b-8192")

# Limites de geração
AI_MAX_TOKENS   = int(os.getenv("AI_MAX_TOKENS",  "400"))
AI_TEMPERATURE  = float(os.getenv("AI_TEMPERATURE", "0.7"))

# Detecta automaticamente se há algum provider online disponível
AI_ONLINE_AVAILABLE = bool(GEMINI_API_KEY or OPENAI_API_KEY or GROQ_API_KEY)
AI_FALLBACK_MODE    = not AI_ONLINE_AVAILABLE  # True = usa apenas modo local

# ─── Voz ──────────────────────────────────────────────────────────────────────
VOICE_LANGUAGE = "pt-BR"
VOICE_RATE     = 170      # velocidade da fala (palavras por minuto)
VOICE_VOLUME   = 1.0      # volume de 0.0 a 1.0

# ─── Sistema ──────────────────────────────────────────────────────────────────
JARVIS_VERSION = "1.1.0"
JARVIS_NAME    = "Jarvis"
