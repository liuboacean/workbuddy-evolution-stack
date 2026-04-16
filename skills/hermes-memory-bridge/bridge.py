#!/usr/bin/env python3
"""
hermes-memory-bridge / bridge.py
WorkBuddy 与 Hermes Agent 双向记忆互通主引擎

用法（作为 Skill 被 WorkBuddy 调用）：
    python3 bridge.py <command> [args...]

命令：
    sync_to_hermes    <summary> <work_type> [tags...]
    sync_from_hermes  [days]
    search            <keyword> [days]
    status
    stats             [days]
    sessions          [days] [limit]
    memory            [memory|user]
    events            [limit]
    help
"""

import json
import sys
import textwrap
from datetime import datetime

from config import HERMES_DB
from memory_writer import read_shared_events as read_bridge_events, read_workbuddy_log
from queries import (
    get_recent_sessions,
    get_session_messages,
    get_session_stats,
    read_hermes_memory,
    search_fts,
    search_messages,
)
from sync import (
    read_bridge_status,
    search_both_memories,
    sync_hermes_to_workbuddy_context,
    sync_workbuddy_to_hermes,
)


def cmd_sync_to_hermes(args: list) -> None:
    """同步 WorkBuddy 工作到 Hermes"""
    summary = args[0] if args else ""
    work_type = args[1] if len(args) > 1 else "task"
    tags = args[2:] if len(args) > 2 else []

    if not summary:
        print("用法: sync_to_hermes <summary> [work_type] [tags...]")
        return

    result = sync_workbuddy_to_hermes(summary, work_type, tags)
    print(f"✅ 已同步到 Hermes")
    print(f"   记忆条目: {result['entry'][:80]}...")
    print(f"   日志路径: {result['log_path']}")


def cmd_sync_from_hermes(args: list) -> None:
    """拉取 Hermes 最新上下文到 WorkBuddy"""
    days = int(args[0]) if args else 7
    result = sync_hermes_to_workbuddy_context(days=days)
    print(result["summary_text"])


def cmd_search(args: list) -> None:
    """跨 WorkBuddy + Hermes 全文搜索"""
    keyword = args[0] if args else ""
    days = int(args[1]) if len(args) > 1 else 30

    if not keyword:
        print("用法: search <keyword> [days]")
        return

    results = search_both_memories(keyword, days=days)
    _print_search_results(results, keyword)


def cmd_status(args: list) -> None:
    """桥接状态总览"""
    status = read_bridge_status()
    print("=" * 48)
    print("  Hermes-Memory-Bridge 状态总览")
    print("=" * 48)
    print(f"  数据库:      {'✅ 存在' if status['db_exists'] else '❌ 不存在'}")
    print(f"  记忆文件:    {', '.join(status['hermes_memory_files']) or '（暂无）'}")
    print(f"  共用文件:    {', '.join(status['shared_files']) or '（暂无）'}")
    print(f"  近期事件:    {len(status['recent_events'])} 条")
    print("=" * 48)

    for ev in status["recent_events"][-5:]:
        print(f"  [{ev['timestamp'][:16]}] {ev['type']}: {str(ev)[:60]}")


def cmd_stats(args: list) -> None:
    """Hermes 使用统计"""
    days = int(args[0]) if args else 30
    stats = get_session_stats(days=days)
    print(f"📊 Hermes 近 {days} 天统计")
    print(f"   会话数:   {stats.get('total_sessions', 0)}")
    print(f"   消息数:   {stats.get('total_messages', 0)}")
    print(f"   Token数: {stats.get('total_tokens', 0):,}")
    print(f"   估算费用: ${stats.get('estimated_cost_usd', 0):.4f}")


def cmd_sessions(args: list) -> None:
    """列出最近会话"""
    days = int(args[0]) if args else 7
    limit = int(args[1]) if len(args) > 1 else 10
    sessions = get_recent_sessions(days=days, limit=limit)

    if not sessions:
        print(f"近 {days} 天无会话记录")
        return

    print(f"📋 近 {days} 天会话（共 {len(sessions)} 条）")
    for s in sessions:
        ts = datetime.fromtimestamp(s["started_at"]).strftime("%m-%d %H:%M")
        title = s.get("title") or s["source"] or "无标题"
        msgs = s.get("message_count", 0)
        cost = s.get("estimated_cost_usd") or 0
        print(f"  [{ts}] {title} | {msgs}条消息 | ${cost:.4f}")


def cmd_memory(args: list) -> None:
    """读取 Hermes 记忆文件"""
    target = args[0] if args else "memory"
    mem = read_hermes_memory()

    key = "MEMORY.md" if target == "memory" else "USER.md"
    data = mem.get(key, {})
    entries = data.get("entries", [])

    print(f"🧠 Hermes {key}（共 {len(entries)} 条记忆）")
    print("-" * 48)
    if not entries:
        print("  （记忆为空）")
    for i, entry in enumerate(entries, 1):
        print(f"  [{i}] {entry[:300]}")
        print()


def cmd_events(args: list) -> None:
    """读取桥接事件历史"""
    limit = int(args[0]) if args else 20
    events = read_bridge_events(limit=limit)

    print(f"🔗 桥接事件历史（共 {len(events)} 条）")
    for ev in events[-limit:]:
        ts = ev.get("timestamp", "")[:16]
        etype = ev.get("type", "")
        # 去除 timestamp 字段以免重复显示
        ev_clean = {k: v for k, v in ev.items() if k != "timestamp"}
        info = str(ev_clean)[:100]
        print(f"  [{ts}] {etype}: {info}")


def _print_search_results(results: dict, keyword: str) -> None:
    print(f"\n🔍 搜索「{keyword}」\n")

    hermes = results.get("hermes", [])
    workbuddy = results.get("workbuddy", [])

    if hermes:
        print(f"**Hermes 会话**（{len(hermes)} 条）")
        for r in hermes[:5]:
            ts = (
                datetime.fromtimestamp(r["timestamp"]).strftime("%m-%d %H:%M")
                if isinstance(r.get("timestamp"), float)
                else "?"
            )
            role = r.get("role", "")
            content = (r.get("content") or "")[:120]
            print(f"  [{ts}] [{role}]: {content}...")
    else:
        print("**Hermes 会话**：无匹配结果")

    print()

    if workbuddy:
        print(f"**WorkBuddy 记忆文件**（{len(workbuddy)} 条）")
        for r in workbuddy[:5]:
            print(f"  [{r['file']}:{r['line']}] {r['snippet']}")
    else:
        print("**WorkBuddy 记忆文件**：无匹配结果")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print(textwrap.dedent(cmd_sync_to_hermes.__doc__ or ""))
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "sync_to_hermes": cmd_sync_to_hermes,
        "sync_from_hermes": cmd_sync_from_hermes,
        "search": cmd_search,
        "status": cmd_status,
        "stats": cmd_stats,
        "sessions": cmd_sessions,
        "memory": cmd_memory,
        "events": cmd_events,
    }

    if cmd not in commands:
        print(f"未知命令: {cmd}")
        print(f"可用命令: {', '.join(commands)}")
        return

    commands[cmd](args)


if __name__ == "__main__":
    main()
