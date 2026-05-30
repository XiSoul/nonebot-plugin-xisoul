"""
SQLite 会话存储。

数据模型：
    sessions(id, scope, scope_key, user_id, group_id, model, system_prompt, created_at, updated_at)
    messages(id, session_id, role, content, created_at)

scope = 'group' 时，scope_key = f"{group_id}:{user_id}"  —— 每个群内每个用户独立会话
scope = 'private' 时，scope_key = f"{user_id}"           —— 每个 QQ 用户一个会话
"""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from . import config


_lock = threading.RLock()


def _connect() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def _cursor() -> Iterator[sqlite3.Cursor]:
    with _lock:
        conn = _connect()
        try:
            cur = conn.cursor()
            yield cur
        finally:
            conn.close()


def init_db() -> None:
    """初始化数据库表结构。幂等。"""
    with _cursor() as cur:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                scope         TEXT NOT NULL,
                scope_key     TEXT NOT NULL UNIQUE,
                user_id       TEXT NOT NULL,
                group_id      TEXT,
                model         TEXT NOT NULL,
                system_prompt TEXT,
                created_at    INTEGER NOT NULL,
                updated_at    INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, id);
            """
        )


# 会话 key 计算 -----------------------------------------------------------
def make_scope_key(*, user_id: str, group_id: Optional[str]) -> tuple[str, str]:
    """返回 (scope, scope_key)。"""
    if group_id:
        return "group", f"{group_id}:{user_id}"
    return "private", str(user_id)


# 会话操作 ---------------------------------------------------------------
def get_or_create_session(
    *,
    user_id: str,
    group_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict:
    scope, scope_key = make_scope_key(user_id=user_id, group_id=group_id)
    now = int(time.time())
    with _cursor() as cur:
        row = cur.execute(
            "SELECT * FROM sessions WHERE scope_key = ?", (scope_key,)
        ).fetchone()
        if row:
            return dict(row)

        cur.execute(
            """
            INSERT INTO sessions
                (scope, scope_key, user_id, group_id, model, system_prompt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope,
                scope_key,
                str(user_id),
                str(group_id) if group_id else None,
                model or config.DEFAULT_MODEL,
                config.DEFAULT_SYSTEM_PROMPT,
                now,
                now,
            ),
        )
        new_id = cur.lastrowid
        row = cur.execute("SELECT * FROM sessions WHERE id = ?", (new_id,)).fetchone()
        return dict(row)


def update_session_model(session_id: int, model: str) -> None:
    with _cursor() as cur:
        cur.execute(
            "UPDATE sessions SET model = ?, updated_at = ? WHERE id = ?",
            (model, int(time.time()), session_id),
        )


def reset_session(session_id: int) -> None:
    """清空当前会话的所有消息（保留 session 元数据）。"""
    with _cursor() as cur:
        cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (int(time.time()), session_id),
        )


# 消息操作 ---------------------------------------------------------------
def append_message(session_id: int, role: str, content: str) -> None:
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, int(time.time())),
        )
        cur.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (int(time.time()), session_id),
        )


def fetch_recent_messages(session_id: int, limit: int) -> List[Dict]:
    """按时间正序返回最近 limit 条消息。"""
    with _cursor() as cur:
        rows = cur.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
