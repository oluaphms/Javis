"""
routers/jarvis_router.py — Rota principal do assistente Jarvis.
Processa queries de texto e voz e executa comandos.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import ai
import voice
import commands
import database as db

router = APIRouter(prefix="/jarvis", tags=["Jarvis"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    text: str
    speak: Optional[bool] = False
    confirm_dangerous: Optional[bool] = False
    system_prompt: Optional[str] = None
    skills: Optional[str] = None


class QueryResponse(BaseModel):
    input: str
    reply: str
    command_name: Optional[str] = None
    command_executed: Optional[bool] = None
    requires_confirm: Optional[bool] = False
    source: str = "text"
    ai_provider: Optional[str] = None   # qual provider de IA foi usado
    ai_intent: Optional[str] = None     # intenção detectada


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
def jarvis_status():
    """Verifica o status completo do sistema Jarvis, incluindo o motor de IA."""
    from config import JARVIS_VERSION
    ai_info = ai.get_ai_info()
    return {
        "status":          "online",
        "version":         JARVIS_VERSION,
        "ai_provider":     ai_info["active_provider"],
        "ai_online":       ai_info["online_mode"],
        "providers_ready": ai_info["available_providers"],
        "history_turns":   ai_info["history_turns"],
        "voice_available": voice.is_voice_available(),
    }


@router.get("/ai/info")
def ai_info():
    """Retorna informações detalhadas do motor de IA."""
    return ai.get_ai_info()


@router.get("/ai/history")
def ai_conversation_history():
    """Retorna o histórico de conversa da sessão atual (in-memory)."""
    return ai.get_history()


@router.post("/ai/detect-intent")
def detect_intent_endpoint(body: dict):
    """Detecta a intenção de um texto. Útil para debug e testes."""
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Campo 'text' obrigatório.")
    intent = ai.detect_intent(text)
    return {"text": text, "intent": intent}


@router.post("/query", response_model=QueryResponse)
def handle_query(body: QueryRequest, background_tasks: BackgroundTasks):
    """Processa uma query de texto e retorna a resposta do Jarvis."""
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto não pode ser vazio.")

    command_name     = None
    command_executed = None
    requires_confirm = False
    ai_provider      = None
    ai_intent        = None
    reply            = ""

    # 1. Tenta executar como comando de sistema
    if body.confirm_dangerous:
        cmd_result = commands.execute_dangerous(text)
    else:
        cmd_result = commands.execute_command(text)

    if cmd_result is not None:
        reply            = cmd_result.message
        command_name     = cmd_result.command_name
        command_executed = cmd_result.success
        requires_confirm = cmd_result.requires_confirm
        ai_intent        = "comando_sistema"
    else:
        # 2. Nenhum comando reconhecido → envia para IA
        ai_response  = ai.process_query_detailed(
            text,
            body.system_prompt,
            body.skills,
        )
        reply        = ai_response.text
        ai_provider  = ai_response.provider
        ai_intent    = ai_response.intent

    # 3. Salva no histórico
    db.history_save(text, reply, source="text")

    # 4. Síntese de voz em background se solicitado
    if body.speak:
        background_tasks.add_task(voice.synthesize, reply)

    return QueryResponse(
        input=text,
        reply=reply,
        command_name=command_name,
        command_executed=command_executed,
        requires_confirm=requires_confirm,
        source="text",
        ai_provider=ai_provider,
        ai_intent=ai_intent,
    )


@router.get("/voice/listen")
def listen_voice():
    """Captura a fala do microfone, processa e retorna a resposta."""
    voice_result = voice.listen()
    if not voice_result["success"]:
        return {"success": False, "error": voice_result["error"], "input": "", "reply": ""}

    text = voice_result["text"]
    cmd_result = commands.execute_command(text)

    if cmd_result is not None:
        reply            = cmd_result.message
        command_name     = cmd_result.command_name
        command_executed = cmd_result.success
        requires_confirm = cmd_result.requires_confirm
        ai_provider      = None
        ai_intent        = "comando_sistema"
    else:
        ai_response      = ai.process_query_detailed(text)
        reply            = ai_response.text
        command_name     = None
        command_executed = None
        requires_confirm = False
        ai_provider      = ai_response.provider
        ai_intent        = ai_response.intent

    db.history_save(text, reply, source="voice")

    return {
        "success":          True,
        "input":            text,
        "reply":            reply,
        "command_name":     command_name,
        "command_executed": command_executed,
        "requires_confirm": requires_confirm,
        "ai_provider":      ai_provider,
        "ai_intent":        ai_intent,
        "source":           "voice",
    }


@router.get("/history")
def get_history(limit: int = 50):
    """Retorna o histórico de comandos e conversas."""
    return db.history_list(limit)


@router.post("/clear-history")
def clear_history():
    """Limpa o histórico de conversa da IA."""
    ai.clear_history()
    return {"detail": "Histórico limpo com sucesso."}


@router.get("/commands")
def list_commands():
    """Lista todos os comandos de sistema disponíveis."""
    return commands.list_commands()


@router.get("/commands/by-category")
def list_commands_by_category():
    """Lista comandos agrupados por categoria."""
    return commands.list_commands_by_category()
