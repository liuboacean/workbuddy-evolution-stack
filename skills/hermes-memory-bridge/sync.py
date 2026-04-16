"""
hermes-memory-bridge / sync.py
WorkBuddy ↔ Hermes 双向同步引擎
"""
import json
from datetime import datetime
from pathlib import Path

from config import (
    BRIDGE_META,
    HERMES_DB,
    HERMES_MEMORIES_DIR,
    SHARED_DIR,
    WORKBUDDY_LOG,
    WORKBUDDY_MEMORY_DIR,
)
from memory_writer import (
    append_hermes_memory,
    read_shared_events as read_bridge_events,
    write_bridge_event,
    write_shared_log,
)
from queries import (
    get_recent_sessions,
    get_session_messages,
    get_session_stats,
    read_hermes_memory,
    search_fts,
    search_messages,
)


def sync_workbuddy_to_hermes(
    work_summary: str,
    work_type: str = "task",
    tags: list[str] = None,
) -> dict:
    """
    将 WorkBuddy 完成的工作同步到 Hermes 记忆系统。

    1. 写入 Hermes MEMORY.md
    2. 写入共用互通日志
    3. 写入桥接元事件
    """
    tags = tags or []

    # ① 写入 Hermes MEMORY.md
    entry = append_hermes_memory(
        target="memory",
        content=work_summary,
        source="WorkBuddy",
    )

    # ② 写入共用日志
    log_path = write_shared_log(
        f"[{work_type}] {work_summary}", log_type="workbuddy"
    )

    # ③ 写入桥接元事件
    write_bridge_event("task_done", {
        "summary": work_summary,
        "work_type": work_type,
        "tags": tags,
    })

    return {
        "entry": entry,
        "log_path": str(log_path),
        "status": "synced",
    }


def sync_hermes_to_workbuddy_context(days: int = 7) -> dict:
    """
    将 Hermes 最近的重要上下文同步到 WorkBuddy 可读格式，
    用于在 WorkBuddy 启动时了解 Hermes 侧的最新动态。
    """
    sessions = get_recent_sessions(days=days)
    stats = get_session_stats(days=days)
    hermes_mem = read_hermes_memory()

    summary_lines = [
        f"## Hermes 近 {days} 天动态",
        "",
        f"**会话数**: {stats.get('total_sessions', 0)}",
        f"**消息数**: {stats.get('total_messages', 0)}",
        "",
        "### 最近会话",
    ]

    for s in sessions[:5]:
        ts = datetime.fromtimestamp(s["started_at"]).strftime("%m-%d %H:%M")
        title = s.get("title") or s["source"] or "无标题"
        summary_lines.append(f"- [{ts}] {title}")

    # Hermes 记忆中的 WorkBuddy 相关条目
    wb_entries = []
    for entry in hermes_mem.get("MEMORY.md", {}).get("entries", []):
        if "WorkBuddy" in entry:
            wb_entries.append(entry)

    if wb_entries:
        summary_lines.append("")
        summary_lines.append("### Hermes 中关于 WorkBuddy 的记忆")
        for e in wb_entries[-5:]:
            summary_lines.append(f"- {e[:200]}")

    return {
        "sessions": sessions,
        "stats": stats,
        "summary_text": "\n".join(summary_lines),
        "workbuddy_entries": wb_entries,
    }


def search_both_memories(keyword: str, days: int = 30) -> dict:
    """
    跨 WorkBuddy 和 Hermes 记忆的全文搜索。
    返回两份结果，供用户对比。
    """
    # Hermes 侧搜索
    hermes_results = search_messages(keyword, days=days)

    # WorkBuddy 侧搜索（读日志文件）
    wb_results = _search_workbuddy_memory(keyword)

    return {
        "keyword": keyword,
        "hermes": hermes_results,
        "workbuddy": wb_results,
    }


def _search_workbuddy_memory(keyword: str) -> list[dict]:
    """在 WorkBuddy 记忆文件中搜索"""
    results = []
    if not WORKBUDDY_MEMORY_DIR.exists():
        return results

    for fpath in WORKBUDDY_MEMORY_DIR.glob("*.md"):
        content = fpath.read_text()
        if keyword.lower() in content.lower():
            # 找含关键词的行及上下文
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    context = lines[max(0, i-1):i+3]
                    results.append({
                        "file": fpath.name,
                        "line": i + 1,
                        "snippet": " ... ".join(c.strip() for c in context if c.strip())[:200],
                    })
    return results


def read_bridge_status() -> dict:
    """读取桥接状态总览"""
    HERMES_MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
    SHARED_DIR.mkdir(parents=True, exist_ok=True)

    mem_files = list(HERMES_MEMORIES_DIR.glob("*.md"))
    shared_files = list(SHARED_DIR.glob("*"))
    events = read_bridge_events(limit=10)

    return {
        "hermes_memory_files": [f.name for f in mem_files],
        "shared_files": [f.name for f in shared_files],
        "recent_events": events,
        "db_exists": HERMES_DB.exists(),
    }


def _format_results_for_user(results: dict, keyword: str) -> str:
    """将搜索结果格式化为友好文本"""
    lines = [f"🔍 搜索「{keyword}」\n"]

    if results.get("hermes"):
        lines.append("**Hermes 会话记录：**")
        for r in results["hermes"][:5]:
            ts = datetime.fromtimestamp(r["timestamp"]).strftime("%m-%d %H:%M") if isinstance(r.get("timestamp"), float) else "?"
            content_preview = (r.get("content") or "")[:150]
            lines.append(f"- [{ts}] {r.get('role','')}: {content_preview}...")
        lines.append("")

    if results.get("workbuddy"):
        lines.append("**WorkBuddy 记忆文件：**")
        for r in results["workbuddy"][:5]:
            lines.append(f"- [{r['file']}:{r['line']}] {r['snippet']}")
    else:
        lines.append("_WorkBuddy 记忆文件中无匹配结果_")

    return "\n".join(lines)
