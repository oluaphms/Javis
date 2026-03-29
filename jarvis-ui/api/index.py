"""
main.py — Ponto de entrada do backend Jarvis para Vercel.
Refatorado para ser robusto em ambiente Serverless (ReadOnly).
"""

import logging
import sys
import os

# Garante que o diretório atual está no path para imports relativos
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importações seguras (podem falhar em ambientes sem dependências nativas)
try:
    from database import init_db
    from config import JARVIS_VERSION
    from routers.jarvis_router import router as jarvis_router
    from routers.tasks_router import router as tasks_router
except ImportError as e:
    print(f"Erro crítico de importação: {e}")
    # Não levantamos o erro aqui para evitar crash imediato, mas o app vai falhar nas rotas

# ─── Logging (Apenas Console) ─────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─── Aplicação FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="Jarvis API",
    description="API do assistente de produtividade Jarvis (Vercel Edition).",
    version="1.1.0",
)

# CORS Permissivo para Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registro de Routers ──────────────────────────────────────────────────────
try:
    app.include_router(jarvis_router)
    app.include_router(tasks_router)
except NameError:
    logger.error("Routers não puderam ser registrados devido a erros de importação.")

# ─── Eventos de Ciclo de Vida ─────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Jarvis Serverless iniciando...")
    try:
        init_db()
        logger.info("✅ Banco de dados pronto.")
    except Exception as e:
        logger.error(f"⚠️ Erro ao inicializar banco: {e}")

@app.get("/api/status")
def status():
    return {"status": "online", "message": "Jarvis está pronto."}

@app.get("/api")
@app.get("/")
def root():
    return {"name": "Jarvis API", "status": "online"}
