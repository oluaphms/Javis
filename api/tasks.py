"""
tasks.py — Serviço de gerenciamento de tarefas do Jarvis.

Responsabilidades:
    - Lógica de negócio sobre as operações do banco (database.py)
    - Respostas sempre em texto amigável para humanos e síntese de voz
    - Validações adicionais de regras de negócio
    - Formatação de listas e relatórios

Interface pública:
    criar_tarefa(titulo, descricao, prioridade) → str
    listar_tarefas(status)                      → str
    concluir_tarefa(id)                         → str
    deletar_tarefa(id)                          → str
    atualizar_tarefa(id, **campos)              → str
    resumo_tarefas()                            → str
    buscar_tarefas(termo)                       → str

Cada função retorna uma string pronta para exibir ao usuário ou sintetizar em voz.
"""

import logging
from typing import Optional
import database as db

logger = logging.getLogger(__name__)

# ─── Mapeamentos de Exibição ──────────────────────────────────────────────────

_PRIORIDADE_LABEL = {
    "baixa":  "🟢 Baixa",
    "media":  "🟡 Média",
    "alta":   "🔴 Alta",
}

_STATUS_LABEL = {
    "pendente":     "⏳ Pendente",
    "em_progresso": "🔄 Em andamento",
    "concluida":    "✅ Concluída",
}

_PRIORIDADE_VALIDAS = {"baixa", "media", "alta"}
_STATUS_VALIDOS     = {"pendente", "em_progresso", "concluida"}


# ─── Formatadores Internos ────────────────────────────────────────────────────

def _formatar_tarefa(t: dict, detalhe: bool = False) -> str:
    """
    Formata uma tarefa como linha de texto.

    Formato resumido:  #1 · Estudar Python  [🟡 Média | ⏳ Pendente]
    Formato detalhado: adiciona descrição e datas
    """
    status   = _STATUS_LABEL.get(t["status"],   t["status"])
    prioridade = _PRIORIDADE_LABEL.get(t["priority"], t["priority"])
    linha = f"  #{t['id']} · {t['title']}  [{prioridade} | {status}]"

    if detalhe:
        if t.get("description"):
            linha += f"\n       Descrição: {t['description']}"
        linha += f"\n       Criada em: {_formatar_data(t['created_at'])}"
        if t["updated_at"] != t["created_at"]:
            linha += f" | Atualizada: {_formatar_data(t['updated_at'])}"

    return linha


def _formatar_data(iso: str) -> str:
    """Converte ISO 8601 em formato legível brasileiro."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso


def _tarefa_nao_encontrada(task_id: int) -> str:
    return f"❌ Tarefa #{task_id} não encontrada."


# ─── Funções de Serviço ───────────────────────────────────────────────────────

def criar_tarefa(
    titulo: str,
    descricao: str = "",
    prioridade: str = "media",
) -> str:
    """
    Cria uma nova tarefa e retorna confirmação em texto.

    Args:
        titulo:    Nome da tarefa (obrigatório).
        descricao: Detalhes adicionais (opcional).
        prioridade: 'baixa' | 'media' | 'alta'. Default 'media'.

    Returns:
        Mensagem de confirmação ou erro.

    Exemplos:
        criar_tarefa("Estudar FastAPI")
        → "✅ Tarefa criada com sucesso!\n  #1 · Estudar FastAPI  [🟡 Média | ⏳ Pendente]"

        criar_tarefa("Deploy produção", prioridade="alta")
        → "✅ Tarefa criada com sucesso!\n  #2 · Deploy produção  [🔴 Alta | ⏳ Pendente]"
    """
    titulo = titulo.strip()
    if not titulo:
        return "❌ O título da tarefa não pode ser vazio."

    prioridade = prioridade.lower().strip()
    if prioridade not in _PRIORIDADE_VALIDAS:
        opcoes = ", ".join(sorted(_PRIORIDADE_VALIDAS))
        return f"❌ Prioridade inválida: '{prioridade}'. Opções: {opcoes}."

    try:
        tarefa = db.task_create(titulo, descricao, prioridade)
        logger.info(f"Tarefa criada: id={tarefa['id']} | '{titulo}'")
        return (
            f"✅ Tarefa criada com sucesso!\n"
            f"{_formatar_tarefa(tarefa)}"
        )
    except Exception as e:
        logger.error(f"Erro ao criar tarefa: {e}")
        return f"❌ Não foi possível criar a tarefa: {e}"


def listar_tarefas(
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    detalhe: bool = False,
) -> str:
    """
    Lista tarefas com filtros opcionais.

    Args:
        status:    Filtra por status ('pendente', 'em_progresso', 'concluida').
        prioridade: Filtra por prioridade ('baixa', 'media', 'alta').
        detalhe:   Se True, exibe descrição e datas.

    Returns:
        Lista formatada em texto ou mensagem de lista vazia.

    Exemplos:
        listar_tarefas()
        → "📋 3 tarefas encontradas:\n  #1 · Estudar FastAPI ..."

        listar_tarefas(status="pendente")
        → "📋 2 tarefas pendentes:\n ..."

        listar_tarefas()  # sem tarefas
        → "📭 Nenhuma tarefa encontrada."
    """
    # Validações de filtro
    if status:
        status = status.lower().strip()
        if status not in _STATUS_VALIDOS:
            opcoes = ", ".join(sorted(_STATUS_VALIDOS))
            return f"❌ Status inválido: '{status}'. Opções: {opcoes}."

    if prioridade:
        prioridade = prioridade.lower().strip()
        if prioridade not in _PRIORIDADE_VALIDAS:
            opcoes = ", ".join(sorted(_PRIORIDADE_VALIDAS))
            return f"❌ Prioridade inválida: '{prioridade}'. Opções: {opcoes}."

    try:
        tarefas = db.task_list(status=status, priority=prioridade)
    except Exception as e:
        logger.error(f"Erro ao listar tarefas: {e}")
        return f"❌ Erro ao listar tarefas: {e}"

    if not tarefas:
        if status:
            label = _STATUS_LABEL.get(status, status)
            return f"📭 Nenhuma tarefa com status {label}."
        return "📭 Nenhuma tarefa cadastrada ainda. Use 'criar tarefa' para começar!"

    # Cabeçalho dinâmico
    total = len(tarefas)
    if status:
        label = _STATUS_LABEL.get(status, status)
        cabecalho = f"📋 {total} tarefa{'s' if total > 1 else ''} {label.split(' ', 1)[-1].lower()}:"
    else:
        cabecalho = f"📋 {total} tarefa{'s' if total > 1 else ''} encontrada{'s' if total > 1 else ''}:"

    linhas = [cabecalho]
    linhas += [_formatar_tarefa(t, detalhe=detalhe) for t in tarefas]

    return "\n".join(linhas)


def concluir_tarefa(task_id: int) -> str:
    """
    Marca uma tarefa como concluída.

    Args:
        task_id: ID da tarefa a concluir.

    Returns:
        Mensagem de confirmação ou erro.

    Exemplos:
        concluir_tarefa(1)
        → "🎉 Tarefa #1 concluída!\n  #1 · Estudar FastAPI  [🟡 Média | ✅ Concluída]"

        concluir_tarefa(99)
        → "❌ Tarefa #99 não encontrada."
    """
    tarefa_atual = db.task_get(task_id)
    if not tarefa_atual:
        return _tarefa_nao_encontrada(task_id)

    if tarefa_atual["status"] == "concluida":
        return f"ℹ️ Tarefa #{task_id} já estava concluída.\n{_formatar_tarefa(tarefa_atual)}"

    try:
        tarefa = db.task_update(task_id, status="concluida")
        if not tarefa:
            return _tarefa_nao_encontrada(task_id)
        logger.info(f"Tarefa concluída: id={task_id}")
        return (
            f"🎉 Muito bem! Tarefa #{task_id} marcada como concluída!\n"
            f"{_formatar_tarefa(tarefa)}"
        )
    except Exception as e:
        logger.error(f"Erro ao concluir tarefa {task_id}: {e}")
        return f"❌ Erro ao concluir tarefa: {e}"


def deletar_tarefa(task_id: int) -> str:
    """
    Remove uma tarefa permanentemente.

    Exemplo:
        deletar_tarefa(1)
        → "🗑️ Tarefa #1 'Estudar FastAPI' removida."
    """
    tarefa = db.task_get(task_id)
    if not tarefa:
        return _tarefa_nao_encontrada(task_id)

    titulo = tarefa["title"]
    try:
        removida = db.task_delete(task_id)
        if removida:
            logger.info(f"Tarefa removida: id={task_id}")
            return f"🗑️ Tarefa #{task_id} '{titulo}' removida com sucesso."
        return _tarefa_nao_encontrada(task_id)
    except Exception as e:
        logger.error(f"Erro ao deletar tarefa {task_id}: {e}")
        return f"❌ Erro ao remover tarefa: {e}"


def atualizar_tarefa(task_id: int, **campos) -> str:
    """
    Atualiza campos de uma tarefa.

    Args:
        task_id: ID da tarefa.
        **campos: title, description, priority, status.

    Exemplo:
        atualizar_tarefa(1, prioridade="alta")
        → "✏️ Tarefa #1 atualizada.\n  #1 · Estudar FastAPI  [🔴 Alta | ⏳ Pendente]"
    """
    # Aceita nomes em português também
    mapa_campos = {
        "titulo":     "title",
        "descricao":  "description",
        "prioridade": "priority",
        "status":     "status",
    }
    campos_normalizados = {
        mapa_campos.get(k, k): v for k, v in campos.items()
    }

    if not db.task_get(task_id):
        return _tarefa_nao_encontrada(task_id)

    try:
        tarefa = db.task_update(task_id, **campos_normalizados)
        if not tarefa:
            return _tarefa_nao_encontrada(task_id)
        logger.info(f"Tarefa atualizada: id={task_id} campos={list(campos_normalizados.keys())}")
        return (
            f"✏️ Tarefa #{task_id} atualizada com sucesso.\n"
            f"{_formatar_tarefa(tarefa)}"
        )
    except ValueError as e:
        return f"❌ Dado inválido: {e}"
    except Exception as e:
        logger.error(f"Erro ao atualizar tarefa {task_id}: {e}")
        return f"❌ Erro ao atualizar tarefa: {e}"


def iniciar_tarefa(task_id: int) -> str:
    """
    Marca uma tarefa como 'em andamento'.

    Exemplo:
        iniciar_tarefa(1)
        → "🔄 Tarefa #1 marcada como em andamento!\n  ..."
    """
    if not db.task_get(task_id):
        return _tarefa_nao_encontrada(task_id)

    try:
        tarefa = db.task_update(task_id, status="em_progresso")
        return (
            f"🔄 Tarefa #{task_id} em andamento!\n"
            f"{_formatar_tarefa(tarefa)}"
        )
    except Exception as e:
        return f"❌ Erro: {e}"


def buscar_tarefas(termo: str) -> str:
    """
    Busca tarefas que contenham o termo no título ou descrição.

    Args:
        termo: Texto a pesquisar (case-insensitive).

    Exemplo:
        buscar_tarefas("python")
        → "🔍 2 tarefas encontradas para 'python':\n  #1 · Estudar Python..."
    """
    termo = termo.strip()
    if not termo:
        return "❌ Informe um termo para pesquisa."

    try:
        todas = db.task_list()
        termo_lower = termo.lower()
        encontradas = [
            t for t in todas
            if termo_lower in t["title"].lower()
            or termo_lower in t.get("description", "").lower()
        ]
    except Exception as e:
        return f"❌ Erro na busca: {e}"

    if not encontradas:
        return f"🔍 Nenhuma tarefa encontrada para '{termo}'."

    total = len(encontradas)
    cabecalho = f"🔍 {total} tarefa{'s' if total > 1 else ''} encontrada{'s' if total > 1 else ''} para '{termo}':"
    linhas = [cabecalho] + [_formatar_tarefa(t) for t in encontradas]
    return "\n".join(linhas)


def resumo_tarefas() -> str:
    """
    Retorna um resumo textual completo do estado das tarefas.

    Exemplo de retorno:
        📊 Resumo das suas tarefas:
           Total:        5
           ⏳ Pendentes:  2
           🔄 Andamento:  1
           ✅ Concluídas: 2
           Progresso: ████████░░ 60%
    """
    try:
        todas = db.task_list()
    except Exception as e:
        return f"❌ Erro ao carregar tarefas: {e}"

    total       = len(todas)
    pendentes   = sum(1 for t in todas if t["status"] == "pendente")
    andamento   = sum(1 for t in todas if t["status"] == "em_progresso")
    concluidas  = sum(1 for t in todas if t["status"] == "concluida")

    if total == 0:
        return "📊 Nenhuma tarefa cadastrada ainda."

    pct = int((concluidas / total) * 100)
    barra = _barra_progresso(pct)

    alta    = sum(1 for t in todas if t["priority"] == "alta" and t["status"] != "concluida")
    urgente = f"\n   ⚠️  {alta} tarefa{'s' if alta > 1 else ''} de alta prioridade pendente{'s' if alta > 1 else ''}!" if alta else ""

    return (
        f"📊 Resumo das suas tarefas:\n"
        f"   Total:          {total}\n"
        f"   ⏳ Pendentes:   {pendentes}\n"
        f"   🔄 Andamento:   {andamento}\n"
        f"   ✅ Concluídas:  {concluidas}\n"
        f"   Progresso: {barra} {pct}%"
        f"{urgente}"
    )


# ─── Aliases para Compatibilidade ────────────────────────────────────────────
# Mantém nomes antigos funcionando caso outras partes do código os usem.

obter_tarefa    = db.task_get
listar_raw      = db.task_list   # retorna list[dict] em vez de str


# ─── Utilitários Privados ─────────────────────────────────────────────────────

def _barra_progresso(pct: int, largura: int = 10) -> str:
    """Gera uma barra de progresso textual. Ex: ████░░░░░░"""
    preenchido = round(pct / 100 * largura)
    return "█" * preenchido + "░" * (largura - preenchido)
