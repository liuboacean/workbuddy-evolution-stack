# WorkBuddy AI Evolution Stack

[![GitHub stars](https://img.shields.io/github/stars/liuboacean/workbuddy-evolution-stack?style=social)](https://github.com/liuboacean/workbuddy-evolution-stack/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/liuboacean/workbuddy-evolution-stack?style=social)](https://github.com/liuboacean/workbuddy-evolution-stack/network/members)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


让 WorkBuddy 具备自我进化和跨 Agent 记忆互通能力的技术栈。

## 包含项目

### 1. hermes-memory-bridge (WorkBuddy Skill)

WorkBuddy 与 Hermes Agent 之间的双向记忆桥梁，让两个 AI Agent 共享上下文与记忆。

**功能**：
- 将 WorkBuddy 工作记录同步到 Hermes 记忆文件
- 从 Hermes 会话历史中提取上下文
- 跨两系统全文搜索
- 查看桥接状态、统计、事件历史

**触发词**：
> 同步到hermes、读取hermes记忆、hermes会话历史、跨记忆搜索、记忆互通、bridge状态、hermes统计

**安装**：
```bash
# 方法1：从 ClawHub 安装
npx clawhub install hermes-memory-bridge --workdir ~ --dir .workbuddy/skills

# 方法2：从源码安装
cp -r skills/hermes-memory-bridge ~/.workbuddy/skills/
```

**前置依赖**：
- Hermes Agent（`~/.hermes/`）
- WorkBuddy with Skill system

---

### 2. WorkBuddy Evolution Engine（独立 Python 包）

让 WorkBuddy 具备独立的自我进化和持久记忆能力，不依赖 Hermes。

**功能**：
- SQLite 知识库（SHA256 去重）
- 用户画像（置信度机制）
- 自动学习脚本（定时从日志提取知识）
- 上下文注入器（启动时自动加载）
- 进化报告生成

**快速开始**：

```bash
# 安装
cd engine && pip install -e .

# 初始化数据库
python3 -m workbuddy_evolution

# 添加记忆
python3 -m workbuddy_evolution add "今天完成了XXX"

# 查看画像
python3 -m workbuddy_evolution profile

# 搜索记忆
python3 -m workbuddy_evolution search deepseek

# 生成进化报告
python3 -m workbuddy_evolution evolve 7

# 输出上下文片段
python3 -m workbuddy_evolution context
```

**自动化配置（WorkBuddy）**：

```python
# 定时任务：每日 22:00 自动学习
automation_update(
    name="WorkBuddy 自动学习",
    prompt="读取今日工作日志，从日志中提炼新知识存入进化数据库，更新用户画像，并刷新上下文缓存。",
    rrule="FREQ=DAILY;BYHOUR=22;BYMINUTE=0",
    cwds="/path/to/memory/",
)
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│  WorkBuddy                                             │
│  ├── hermes-memory-bridge Skill                         │
│  │   └── bridge.py → 写入 ~/.hermes/memories/MEMORY.md  │
│  │                                                          │
│  └── evolution_engine.py                                  │
│      ├── auto_learn.py  →  每日 22:00 自动运行             │
│      ├── context_injector.py →  每次启动自动调用           │
│      └── evolution.db   →  持久知识库                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Hermes Agent                                           │
│  ├── ~/.hermes/memories/MEMORY.md ←  WorkBuddy 可写     │
│  ├── ~/.hermes/shared/workbuddy.log ←  WorkBuddy 日志   │
│  └── ~/.hermes/state.db ←  会话历史查询                   │
└─────────────────────────────────────────────────────────┘
```

---

## 文件结构

```
workbuddy-evolution-stack/
├── skills/
│   └── hermes-memory-bridge/
│       ├── SKILL.md          # WorkBuddy Skill 定义
│       ├── bridge.py         # 主入口（8个命令）
│       ├── config.py         # 路径配置
│       ├── queries.py        # Hermes state.db 查询
│       ├── memory_writer.py  # 记忆写入模块
│       └── sync.py           # 双向同步引擎
├── engine/
│   ├── setup.py              # pip 安装配置
│   ├── evolution_engine.py   # 核心引擎
│   ├── auto_learn.py         # 定时学习脚本
│   └── context_injector.py  # 上下文注入器
├── README.md
└── LICENSE
```

---

## 环境要求

- Python 3.10+
- WorkBuddy（或 CodeBuddy）
- Hermes Agent（仅 hermes-memory-bridge 需要）
- SQLite3（Python 内置）

---

## License

MIT
