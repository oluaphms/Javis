"""
main.py — Ponto de entrada do backend Jarvis.
Configura o servidor FastAPI com todos os routers e middlewares.
"""

import logging
import sys
import os

# Garante que o diretório pai está no path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import init_db
from config import API_HOST, API_PORT, JARVIS_VERSION
from routers.jarvis_router import router as jarvis_router
from routers.tasks_router import router as tasks_router

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ─── Aplicação FastAPI ────────────────────────────────────────────────────────

app = FastAPI(
    title="Jarvis API",
    description="API do assistente de produtividade Jarvis.",
    version=JARVIS_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permite requisições do frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registro de Routers ──────────────────────────────────────────────────────

app.include_router(jarvis_router)
app.include_router(tasks_router)


# ─── Eventos de Ciclo de Vida ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Jarvis v{JARVIS_VERSION} iniciando...")
    init_db()
    logger.info("✅ Banco de dados pronto.")
    logger.info(f"📡 Servidor em http://{API_HOST}:{API_PORT}")
    logger.info(f"📚 Documentação em http://localhost:{API_PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🔴 Jarvis encerrado.")


# ─── Rota Raiz ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "Jarvis API",
        "version": JARVIS_VERSION,
        "status": "online",
        "endpoints": {
            "docs": "/docs",
            "jarvis": "/jarvis",
            "tasks": "/tasks",
        }
    }


# ─── Execução Direta ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )
