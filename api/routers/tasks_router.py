"""
routers/tasks_router.py — Endpoints REST para gerenciamento de tarefas.
Usa o serviço tasks.py que retorna respostas em texto amigável.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator
from typing import Optional
import tasks as svc
import database as db

router = APIRouter(prefix="/tasks", tags=["Tarefas"])


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = "media"

    @field_validator("title")
    @classmethod
    def title_nao_vazio(cls, v):
        if not v.strip():
            raise ValueError("O título não pode ser vazio.")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def priority_valida(cls, v):
        validas = {"baixa", "media", "alta"}
        v = v.lower().strip()
        if v not in validas:
            raise ValueError(f"Prioridade inválida. Use: {validas}")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class TaskResponse(BaseModel):
    """Retorna tanto os dados estruturados quanto a mensagem amigável."""
    message: str
    task: Optional[dict] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/")
def list_tasks(
    status: Optional[str] = Query(None, description="pendente | em_progresso | concluida"),
    priority: Optional[str] = Query(None, description="baixa | media | alta"),
    detalhe: bool = Query(False, description="Incluir descrição e datas"),
):
    """
    Lista tarefas com filtros opcionais.
    Retorna a lista estruturada para o frontend e o texto amigável para o chat.
    """
    tarefas = db.task_list(status=status, priority=priority)
    mensagem = svc.listar_tarefas(status=status, prioridade=priority, detalhe=detalhe)
    return {"message": mensagem, "tasks": tarefas}


@router.get("/summary")
def task_summary():
    """Retorna um resumo em texto e dados estruturados das tarefas."""
    todas = db.task_list()
    total = len(todas)
    return {
        "message": svc.resumo_tarefas(),
        "data": {
            "total": total,
            "pendentes": sum(1 for t in todas if t["status"] == "pendente"),
            "em_progresso": sum(1 for t in todas if t["status"] == "em_progresso"),
            "concluidas": sum(1 for t in todas if t["status"] == "concluida"),
        }
    }


@router.get("/search")
def search_tasks(q: str = Query(..., description="Termo de busca")):
    """Busca tarefas por título ou descrição."""
    tarefas = db.task_list()
    termo = q.lower()
    encontradas = [
        t for t in tarefas
        if termo in t["title"].lower() or termo in t.get("description", "").lower()
    ]
    return {
        "message": svc.buscar_tarefas(q),
        "tasks": encontradas
    }


@router.get("/{task_id}")
def get_task(task_id: int):
    """Retorna uma tarefa específica pelo ID."""
    task = db.task_get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Tarefa #{task_id} não encontrada.")
    return task


@router.post("/", status_code=201, response_model=TaskResponse)
def create_task(body: TaskCreate):
    """Cria uma nova tarefa."""
    message = svc.criar_tarefa(body.title, body.description, body.priority)
    # Obtém o dado estruturado da última tarefa criada
    todas = db.task_list()
    tarefa = todas[0] if todas else None
    return TaskResponse(message=message, task=tarefa)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, body: TaskUpdate):
    """Atualiza campos de uma tarefa."""
    campos = {k: v for k, v in body.dict().items() if v is not None}
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")
    message = svc.atualizar_tarefa(task_id, **campos)
    tarefa = db.task_get(task_id)
    return TaskResponse(message=message, task=tarefa)


@router.patch("/{task_id}/start", response_model=TaskResponse)
def start_task(task_id: int):
    """Marca uma tarefa como 'em andamento'."""
    message = svc.iniciar_tarefa(task_id)
    tarefa = db.task_get(task_id)
    return TaskResponse(message=message, task=tarefa)


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int):
    """Marca uma tarefa como concluída."""
    message = svc.concluir_tarefa(task_id)
    tarefa = db.task_get(task_id)
    return TaskResponse(message=message, task=tarefa)


@router.delete("/{task_id}", response_model=TaskResponse)
def delete_task(task_id: int):
    """Remove uma tarefa permanentemente."""
    message = svc.deletar_tarefa(task_id)
    if "não encontrada" in message:
        raise HTTPException(status_code=404, detail=message)
    return TaskResponse(message=message, task=None)
