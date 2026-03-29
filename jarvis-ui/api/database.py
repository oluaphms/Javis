"""
database.py — Camada de acesso ao banco de dados (Supabase Cloud + SQLite Fallback).
Adaptado para Vercel: Se falhar o Supabase e estiver na Vercel, usa o /tmp/ para evitar erro 500.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Configurações de PATH para Vercel
try:
    from config import DB_PATH, SUPABASE_URL, SUPABASE_KEY, DB_ONLINE
except ImportError:
    try:
        from .config import DB_PATH, SUPABASE_URL, SUPABASE_KEY, DB_ONLINE
    except ImportError:
        DB_PATH = os.path.join(os.getcwd(), "database", "tasks.db")
        SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
        DB_ONLINE = bool(SUPABASE_URL and SUPABASE_KEY)

# Ajuste crítico para Vercel: O sistema de arquivos é Read-Only
# Se não estivermos usando Supabase, tentamos usar o /tmp do Linux
if not DB_ONLINE and os.environ.get("VERCEL"):
    DB_PATH = "/tmp/tasks.db"

logger = logging.getLogger(__name__)

# Instância global do cliente Supabase
supabase = None
if DB_ONLINE:
    try:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("📡 Conexão estabilizada com Supabase Cloud.")
    except ImportError:
        logger.warning("⚠️ Biblioteca 'supabase' não encontrada.")
        supabase = None

# Fallback para SQLite
import sqlite3
from contextlib import contextmanager

@contextmanager
def _sqlite_conn():
    # Cria o diretório apenas se não for /tmp ou se tivermos permissão
    dir_path = os.path.dirname(os.path.abspath(DB_PATH))
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
    except Exception:
        pass # Ignora erro de permissão se o diretório já for /tmp

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ─── Inicialização ────────────────────────────────────────────────────────────

def init_db() -> None:
    if not supabase:
        try:
            with _sqlite_conn() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, priority TEXT, status TEXT, created_at TEXT, updated_at TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS command_history (id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, response TEXT, source TEXT, executed_at TEXT)")
            logger.info(f"📁 Banco local SQLite inicializado: {DB_PATH}")
        except Exception as e:
            logger.error(f"Falha ao iniciar SQLite: {e}")
    else:
        logger.info("📡 Usando Supabase como banco principal.")

# ... (restante das funções permanecem as mesmas mas garantindo retorno no fallback)

def task_create(title: str, description: str = "", priority: str = "media") -> Dict[str, Any]:
    now = datetime.now().isoformat()
    task_data = {"title": title, "description": description, "priority": priority, "status": "pendente", "created_at": now, "updated_at": now}
    if supabase:
        try:
            res = supabase.table("tasks").insert(task_data).execute()
            return res.data[0] if res.data else task_data
        except: return task_data
    else:
        with _sqlite_conn() as conn:
            cursor = conn.execute("INSERT INTO tasks (title, description, priority, status, created_at, updated_at) VALUES (?,?,?,?,?,?)", (title, description, priority, "pendente", now, now))
            task_data["id"] = cursor.lastrowid
            return task_data

def task_list(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    if supabase:
        try:
            q = supabase.table("tasks").select("*")
            if status: q = q.eq("status", status)
            return q.order("created_at", desc=True).limit(limit).execute().data or []
        except: return []
    else:
        with _sqlite_conn() as conn:
            rows = conn.execute(f"SELECT * FROM tasks {'WHERE status=?' if status else ''} ORDER BY created_at DESC LIMIT ?", (status, limit) if status else (limit,)).fetchall()
            return [dict(r) for r in rows]

def task_update(task_id: int, **fields) -> Optional[Dict[str, Any]]:
    if supabase:
        try: return supabase.table("tasks").update(fields).eq("id", task_id).execute().data[0]
        except: return None
    else:
        with _sqlite_conn() as conn:
            keys = ", ".join(f"{k}=?" for k in fields)
            conn.execute(f"UPDATE tasks SET {keys} WHERE id=?", list(fields.values()) + [task_id])
            return task_get(task_id)

def task_get(task_id: int) -> Optional[Dict[str, Any]]:
    if supabase:
        try: return supabase.table("tasks").select("*").eq("id", task_id).execute().data[0]
        except: return None
    else:
        with _sqlite_conn() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            return dict(row) if row else None

def task_delete(task_id: int) -> bool:
    if supabase:
        try: return bool(supabase.table("tasks").delete().eq("id", task_id).execute().data)
        except: return False
    else:
        with _sqlite_conn() as conn:
            return conn.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount > 0

def history_save(command: str, response: str, source: str = "text") -> None:
    now = datetime.now().isoformat()
    data = {"command": command, "response": response, "source": source, "executed_at": now}
    if supabase:
        try: supabase.table("command_history").insert(data).execute()
        except: pass
    else:
        try:
            with _sqlite_conn() as conn:
                conn.execute("INSERT INTO command_history (command, response, source, executed_at) VALUES (?,?,?,?)", (command, response, source, now))
        except: pass

def history_list(limit: int = 50) -> List[Dict[str, Any]]:
    if supabase:
        try: return supabase.table("command_history").select("*").order("executed_at", desc=True).limit(limit).execute().data or []
        except: return []
    else:
        with _sqlite_conn() as conn:
            rows = conn.execute("SELECT * FROM command_history ORDER BY executed_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
