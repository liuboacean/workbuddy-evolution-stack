---
name: hermes-memory-bridge
description: Hermes Agent 与 WorkBuddy 双向记忆互通 Skill。触发词：同步到hermes、读取hermes记忆、hermes会话历史、跨记忆搜索、记忆互通、bridge状态、hermes统计、环境变量、错误处理
---

# hermes-memory-bridge

> v1.1.0 | WorkBuddy ↔ Hermes Agent 双向记忆桥梁

WorkBuddy 与 Hermes Agent 之间的双向记忆桥梁，让两个 AI Agent 共享上下文与记忆。

## 架构

```
WorkBuddy  ←── bridge.py ──▶  Hermes
                   ↓
            ~/.hermes/shared/
            ~/.hermes/memories/MEMORY.md
            ~/.hermes/state.db
```

## 存储布局

| 路径 | 用途 |
|------|------|
| `~/.hermes/memories/MEMORY.md` | Hermes 个人笔记（WorkBuddy 可写） |
| `~/.hermes/memories/USER.md` | 用户画像 |
| `~/.hermes/state.db` | SQLite：sessions + messages |
| `~/.hermes/shared/workbuddy.log` | WorkBuddy 工作日志（Hermes 可读） |
| `~/.hermes/shared/hermes.log` | Hermes 运行日志（WorkBuddy 可读） |
| `~/.hermes/shared/meta.json` | 桥接事件记录（双方均可解析） |

## 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_HOME` | `~/.hermes` | Hermes 根目录 |
| `WORKBUDDY_HOME` | `~/WorkBuddy` | WorkBuddy 根目录（自动找最新时间戳子目录） |
| `WORKBUDDY_MEMORY_DIR` | （自动发现） | 强制指定 WorkBuddy 记忆目录完整路径 |
| `BRIDGE_LOG_LEVEL` | `INFO` | 日志级别：DEBUG / INFO / WARNING / ERROR |

**路径查找优先级**（WORKBUDDY_MEMORY_DIR）：
1. `WORKBUDDY_MEMORY_DIR` 环境变量（完整路径）
2. `WORKBUDDY_HOME` → 其下最新时间戳子目录 → `.workbuddy/memory`
3. `~/WorkBuddy` → 找最新时间戳子目录 → `.workbuddy/memory`

## 命令行用法

```bash
# 同步 WorkBuddy 工作到 Hermes 记忆
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py \
  sync_to_hermes "完成了XXX" <work_type> [tags...]

# 拉取 Hermes 近 N 天上下文
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py \
  sync_from_hermes [days]

# 跨 WorkBuddy + Hermes 全文搜索
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py \
  search <keyword> [days]

# 查看桥接状态
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py status

# Hermes 使用统计
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py stats [days]

# 列出最近会话
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py sessions [days] [limit]

# 读取 Hermes 记忆
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py memory [memory|user]

# 查看桥接事件历史
python3 ~/.workbuddy/skills/hermes-memory-bridge/bridge.py events [limit]
```

## 同步规则

**WorkBuddy → Hermes**：
- 每次完成重要工作后，调用 `sync_to_hermes`，自动写入：
  - `~/.hermes/memories/MEMORY.md`（Hermes 下次启动时自动注入系统提示词）
  - `~/.hermes/shared/workbuddy.log`（Hermes 的 `on_delegation` hook 可读取）
  - `~/.hermes/shared/meta.json`（结构化事件，双方均可解析）

**WorkBuddy ← Hermes**：
- 启动时调用 `sync_from_hermes`，获取 Hermes 侧最新动态
- 使用 `search` 命令跨两边记忆全文搜索
- 读取 `~/.hermes/shared/hermes.log`（Hermes 运行后主动写入）
- 查询 `~/.hermes/state.db` 获取会话历史

## 错误处理

所有命令均有健壮错误处理：
- **文件不存在**：优雅降级，返回空列表/空结果，不抛异常
- **权限不足**：记录警告日志，返回友好错误信息
- **数据库错误**：自动降级（如 FTS5 不可用 → 降级为 LIKE 搜索）
- **同步部分失败**：返回 `status: partial`，仍输出成功写入的部分

**返回值约定**：
- `exit code 0` = 成功
- `exit code 1` = 失败（含参数错误、全部写入失败等）

## API 参考（Python 模块）

```python
from config import get_workbuddy_memory_dir, _get_logger

# 动态获取 WorkBuddy 记忆目录
wb_dir = get_workbuddy_memory_dir()
# 返回 Path 或 None

# 获取子模块 logger
logger = _get_logger("module_name")

# 同步 WorkBuddy → Hermes
from sync import sync_workbuddy_to_hermes
result = sync_workbuddy_to_hermes(
    work_summary="完成了某项工作",
    work_type="task",
    tags=["mcp", "integration"]
)
# result: {status: "synced"|"partial"|"failed", entry, log_path}

# 同步 Hermes → WorkBuddy
from sync import sync_hermes_to_workbuddy_context
ctx = sync_hermes_to_workbuddy_context(days=7)

# 跨系统搜索
from sync import search_both_memories
results = search_both_memories("deepseek", days=30)

# 读取桥接状态
from sync import read_bridge_status
status = read_bridge_status()

# 直接写 Hermes 记忆
from memory_writer import append_hermes_memory
entry = append_hermes_memory("memory", "内容", "WorkBuddy")

# 写入桥接事件
from memory_writer import write_bridge_event
write_bridge_event("task_done", {"summary": "...", "tags": []})

# 查询 Hermes 数据库
from queries import get_recent_sessions, get_session_stats
sessions = get_recent_sessions(days=7)
stats = get_session_stats(days=30)
```

## 触发词示例

- "把今天的工作同步到 Hermes"
- "搜索一下 Hermes 里关于 MCP 的记录"
- "Hermes 最近有多少会话"
- "两个系统的记忆里有没有关于 deepseek 的内容"
- "查看 bridge 状态"
- "设置了哪些环境变量"
