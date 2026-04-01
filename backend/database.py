"""
database.py — Camada de acesso ao banco de dados (Supabase Cloud + SQLite Fallback).

Este módulo agora é inteligente:
1. Se SUPABASE_URL e SUPABASE_KEY estiverem configuradas, usa o Cloud.
2. Caso contrário, mantém o funcionamento local em SQLite.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from config import DB_PATH, SUPABASE_URL, SUPABASE_KEY, DB_ONLINE
except ImportError:
    # Fallback para imports absolutos se necessário em certos ambientes
    try:
        from .config import DB_PATH, SUPABASE_URL, SUPABASE_KEY, DB_ONLINE
    except ImportError:
        DB_PATH = "database/tasks.db"
        SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
        DB_ONLINE = bool(SUPABASE_URL and SUPABASE_KEY)

logger = logging.getLogger(__name__)

# Instância global do cliente Supabase (opcional)
supabase = None
if DB_ONLINE:
    try:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("📡 Conexão estabilizada com Supabase Cloud.")
    except ImportError:
        logger.warning("⚠️ Biblioteca 'supabase' não encontrada. Usando SQLite.")
        supabase = None
    except Exception as e:
        logger.warning(f"⚠️ Falha ao conectar Supabase: {e}. Usando SQLite.")
        supabase = None

# Fallback para SQLite
import sqlite3
from contextlib import contextmanager

@contextmanager
def _sqlite_conn():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
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
        with _sqlite_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT    NOT NULL,
                    description TEXT    NOT NULL DEFAULT '',
                    priority    TEXT    NOT NULL DEFAULT 'media',
                    status      TEXT    NOT NULL DEFAULT 'pendente',
                    created_at  TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    command     TEXT    NOT NULL,
                    response    TEXT    NOT NULL,
                    source      TEXT    NOT NULL DEFAULT 'text',
                    executed_at TEXT    NOT NULL
                )
            """)
        logger.info(f"📁 Banco local SQLite inicializado: {DB_PATH}")
    else:
        logger.info("📡 Banco Supabase detectado. Certifique-se de que o Schema SQL foi executado no Editor SQL.")

# ─── CRUD de Tarefas ──────────────────────────────────────────────────────────

def task_create(title: str, description: str = "", priority: str = "media") -> Dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    task_data: Dict[str, Any] = {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pendente",
        "created_at": now,
        "updated_at": now
    }

    if supabase:
        try:
            response = supabase.table("tasks").insert(task_data).execute()
            return dict(response.data[0]) if response.data else task_data
        except Exception as e:
            logger.error(f"Erro Supabase task_create: {e}")
            return task_data
    else:
        with _sqlite_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, description, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (task_data["title"], task_data["description"], task_data["priority"], task_data["status"], task_data["created_at"], task_data["updated_at"])
            )
            task_data["id"] = cursor.lastrowid
            return task_data

def task_list(status: Optional[str] = None, priority: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    if supabase:
        try:
            query = supabase.table("tasks").select("*")
            if status:
                query = query.eq("status", status)
            if priority:
                query = query.eq("priority", priority)
            response = query.order("created_at", desc=True).limit(limit).execute()
            return [dict(r) for r in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Erro Supabase task_list: {e}")
            return []
    else:
        with _sqlite_conn() as conn:
            conditions = []
            params = []
            if status:
                conditions.append("status = ?")
                params.append(status)
            if priority:
                conditions.append("priority = ?")
                params.append(priority)
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            rows = conn.execute(f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ?", params + [limit]).fetchall()
            return [dict(r) for r in rows]

def task_update(task_id: int, **fields) -> Optional[Dict[str, Any]]:
    fields["updated_at"] = datetime.now().isoformat(timespec="seconds")
    if supabase:
        try:
            response = supabase.table("tasks").update(fields).eq("id", task_id).execute()
            return dict(response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Erro Supabase task_update: {e}")
            return None
    else:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with _sqlite_conn() as conn:
            conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", list(fields.values()) + [task_id])
            return task_get(task_id)

def task_get(task_id: int) -> Optional[Dict[str, Any]]:
    if supabase:
        try:
            response = supabase.table("tasks").select("*").eq("id", task_id).execute()
            return dict(response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Erro Supabase task_get: {e}")
            return None
    else:
        with _sqlite_conn() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None

def task_delete(task_id: int) -> bool:
    if supabase:
        try:
            response = supabase.table("tasks").delete().eq("id", task_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Erro Supabase task_delete: {e}")
            return False
    else:
        with _sqlite_conn() as conn:
            count = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount
            return count > 0

# ─── Histórico de Comandos ────────────────────────────────────────────────────

def history_save(command: str, response: str, source: str = "text") -> None:
    now = datetime.now().isoformat(timespec="seconds")
    data = {"command": command.strip(), "response": response.strip(), "source": source, "executed_at": now}
    if supabase:
        try:
            supabase.table("command_history").insert(data).execute()
        except Exception as e:
            logger.error(f"Erro Supabase history_save: {e}")
    else:
        with _sqlite_conn() as conn:
            conn.execute("INSERT INTO command_history (command, response, source, executed_at) VALUES (?, ?, ?, ?)", (data["command"], data["response"], source, now))

def history_list(limit: int = 50) -> List[Dict[str, Any]]:
    if supabase:
        try:
            response = supabase.table("command_history").select("*").order("executed_at", desc=True).limit(limit).execute()
            return [dict(r) for r in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Erro Supabase history_list: {e}")
            return []
    else:
        with _sqlite_conn() as conn:
            rows = conn.execute("SELECT * FROM command_history ORDER BY executed_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
