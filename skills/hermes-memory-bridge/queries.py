"""
hermes-memory-bridge / queries.py
Hermes state.db 查询封装
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from config import HERMES_DB


def _row2dict(row: sqlite3.Row) -> dict:
    return dict(row)


def get_recent_sessions(days: int = 7, limit: int = 20) -> list[dict]:
    """返回最近 N 天的会话列表"""
    if not HERMES_DB.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    with sqlite3.connect(HERMES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, source, model, title, started_at, ended_at,
                   end_reason, message_count, tool_call_count,
                   estimated_cost_usd, actual_cost_usd
            FROM sessions
            WHERE started_at > ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (cutoff.timestamp(), limit),
        )
        return [_row2dict(r) for r in cur.fetchall()]


def get_session_messages(session_id: str, limit: int = 50) -> list[dict]:
    """返回指定会话的消息历史"""
    if not HERMES_DB.exists():
        return []

    with sqlite3.connect(HERMES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT role, content, tool_name, timestamp, finish_reason
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (session_id, limit),
        )
        return [_row2dict(r) for r in cur.fetchall()]


def search_messages(keyword: str, days: int = 30) -> list[dict]:
    """全文搜索 Hermes 会话"""
    if not HERMES_DB.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    with sqlite3.connect(HERMES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT m.session_id, m.role, m.content, m.tool_name, m.timestamp,
                   s.title, s.source
            FROM messages m
            JOIN sessions s ON m.session_id = s.id
            WHERE m.timestamp > ?
              AND m.content LIKE ?
            ORDER BY m.timestamp DESC
            LIMIT 30
            """,
            (cutoff.timestamp(), f"%{keyword}%"),
        )
        return [_row2dict(r) for r in cur.fetchall()]


def search_fts(keyword: str, limit: int = 20) -> list[dict]:
    """使用 FTS5 全文搜索"""
    if not HERMES_DB.exists():
        return []

    with sqlite3.connect(HERMES_DB) as conn:
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                """
                SELECT m.session_id, m.role, m.content, m.tool_name,
                       s.title, s.started_at,
                       highlight(messages_fts, 0, '**', '**') AS hl_content
                FROM messages_fts
                JOIN messages m ON messages_fts.rowid = m.id
                JOIN sessions s ON m.session_id = s.id
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (keyword, limit),
            )
            return [_row2dict(r) for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return search_messages(keyword, 30)


def get_session_stats(days: int = 30) -> dict[str, Any]:
    """获取 Hermes 使用统计"""
    if not HERMES_DB.exists():
        return {}

    cutoff = datetime.now() - timedelta(days=days)
    with sqlite3.connect(HERMES_DB) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE started_at > ?", (cutoff.timestamp(),)
        ).fetchone()[0]

        total_messages = conn.execute(
            "SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id WHERE s.started_at > ?",
            (cutoff.timestamp(),),
        ).fetchone()[0]

        total_tokens = conn.execute(
            "SELECT SUM(input_tokens + output_tokens) FROM sessions WHERE started_at > ?",
            (cutoff.timestamp(),),
        ).fetchone()[0] or 0

        total_cost = conn.execute(
            "SELECT SUM(actual_cost_usd) FROM sessions WHERE started_at > ? AND actual_cost_usd IS NOT NULL",
            (cutoff.timestamp(),),
        ).fetchone()[0] or 0.0

        return {
            "period_days": days,
            "total_sessions": total,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_cost, 4),
        }


def read_hermes_memory() -> dict[str, str]:
    """读取 Hermes 内置记忆文件"""
    from config import HERMES_MEMORIES_DIR

    result = {}
    for fname in ("MEMORY.md", "USER.md"):
        fpath = HERMES_MEMORIES_DIR / fname
        if fpath.exists():
            content = fpath.read_text()
            # 按 § 分隔符拆分条目
            entries = [e.strip() for e in content.split("\n§\n") if e.strip()]
            result[fname] = {"entries": entries, "raw": content}
        else:
            result[fname] = {"entries": [], "raw": ""}
    return result
