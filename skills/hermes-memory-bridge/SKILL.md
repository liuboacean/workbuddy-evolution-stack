---
name: hermes-memory-bridge
description: Hermes Agent 与 WorkBuddy 双向记忆互通 Skill。触发词：同步到hermes、读取hermes记忆、hermes会话历史、跨记忆搜索、记忆互通、bridge状态、hermes统计
---

# hermes-memory-bridge

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
| `~/.hermes/shared/meta.json` | 桥接事件记录 |

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

**WorkBuddy → Hermes（读）**：
- 启动时调用 `sync_from_hermes`，获取 Hermes 侧最新动态
- 使用 `search` 命令跨两边记忆全文搜索

**WorkBuddy ← Hermes**：
- 读取 `~/.hermes/shared/hermes.log`（Hermes 运行后主动写入）
- 查询 `~/.hermes/state.db` 获取会话历史

## 触发词示例

- "把今天的工作同步到 Hermes"
- "搜索一下 Hermes 里关于 MCP 的记录"
- "Hermes 最近有多少会话"
- "两个系统的记忆里有没有关于 deepseek 的内容"
- "查看 bridge 状态"
