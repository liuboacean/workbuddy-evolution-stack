"""
hermes-memory-bridge / memory_writer.py
写入 Hermes 记忆文件
"""
import re
from datetime import datetime
from pathlib import Path

from config import (
    ENTRY_DELIMITER,
    HERMES_MEMORIES_DIR,
    MAX_ENTRY_CHARS,
    SHARED_DIR,
    WORKBUDDY_LOG,
)


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _sanitize(content: str) -> str:
    """去除注入风险内容（与 Hermes 内存工具一致的检查）"""
    patterns = [
        r"ignore\s+(previous|all|above|prior)\s+instructions",
        r"you\s+are\s+now\s+",
        r"system\s+prompt\s+override",
    ]
    for pat in patterns:
        content = re.sub(pat, "[FILTERED]", content, flags=re.IGNORECASE)
    return content[:MAX_ENTRY_CHARS]


def append_hermes_memory(
    target: str, content: str, source: str = "WorkBuddy"
) -> str:
    """
    向 Hermes 的 MEMORY.md 或 USER.md 追加一条记忆条目。

    target: 'memory' | 'user'
    content: 要写入的内容
    source: 来源标记（默认为 WorkBuddy）
    """
    HERMES_MEMORIES_DIR.mkdir(parents=True, exist_ok=True)

    fname = "MEMORY.md" if target == "memory" else "USER.md"
    fpath = HERMES_MEMORIES_DIR / fname

    timestamp = datetime.now().strftime("%Y-%m-%d")
    safe_content = _sanitize(content)
    entry = f"[{timestamp} · {source}]\n{safe_content}"

    if fpath.exists():
        existing = fpath.read_text()
    else:
        existing = ""

    if existing.strip():
        new_content = existing.rstrip() + ENTRY_DELIMITER + entry
    else:
        new_content = entry

    fpath.write_text(new_content)
    return entry


def write_shared_log(
    content: str, log_type: str = "workbuddy"
) -> Path:
    """
    写入共用互通日志（Hermes 可通过 on_delegation hook 读取）。
    log_type: 'workbuddy' | 'hermes'
    """
    _ensure_dir(SHARED_DIR)
    log_file = SHARED_DIR / f"{log_type}.log"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp}] {content}\n"

    existing = log_file.read_text() if log_file.exists() else ""
    log_file.write_text(existing + entry)
    return log_file


def write_bridge_event(event_type: str, data: dict) -> None:
    """
    写入桥接元事件，供两边 Agent 在下次启动时读取。
    event_type: 'task_done' | 'config_change' | 'sync'
    """
    import json

    _ensure_dir(SHARED_DIR)
    meta_file = SHARED_DIR / "meta.json"

    if meta_file.exists():
        meta = json.loads(meta_file.read_text())
    else:
        meta = {"events": []}

    meta["events"].append({
        "type": event_type,
        "timestamp": datetime.now().isoformat(),
        **data,
    })
    # 保留最近 100 条
    meta["events"] = meta["events"][-100:]

    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def read_shared_events(event_type: str = None, limit: int = 20) -> list:
    """读取共用互通事件"""
    import json

    meta_file = SHARED_DIR / "meta.json"
    if not meta_file.exists():
        return []

    meta = json.loads(meta_file.read_text())
    events = meta.get("events", [])
    if event_type:
        events = [e for e in events if e.get("type") == event_type]
    return events[-limit:]


def read_workbuddy_log(lines: int = 20) -> list[str]:
    """读取 WorkBuddy 写给 Hermes 的最新日志"""
    log_file = SHARED_DIR / "workbuddy.log"
    if not log_file.exists():
        return []
    all_lines = log_file.read_text().strip().split("\n")
    return all_lines[-lines:]
