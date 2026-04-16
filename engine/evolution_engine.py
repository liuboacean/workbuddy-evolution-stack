"""
WorkBuddy Memory Evolution Engine
让 WorkBuddy 具备自我进化和持久记忆能力

可作为独立 pip 包安装，也可在 WorkBuddy 环境中直接运行。
"""

import os
import sqlite3
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── 路径配置（优先环境变量，支持便携）───────────────────────
_MEMORY_DIR_ENV = os.environ.get("WORKBUDDY_MEMORY_DIR", "")
if _MEMORY_DIR_ENV:
    MEMORY_DIR = Path(_MEMORY_DIR_ENV)
else:
    # 默认：跟随 WorkBuddy workspace 约定
    WB_DIR = Path.home() / "WorkBuddy"
    # 查找最新的 workspace 目录
    workspaces = sorted(WB_DIR.glob("??????????????"))
    MEMORY_DIR = (workspaces[-1] / ".workbuddy" / "memory") if workspaces else (Path.home() / ".workbuddy" / "memory")

MEMORY_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = MEMORY_DIR / "evolution.db"


class EvolutionEngine:
    """WorkBuddy 自我进化引擎"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.memory_dir = MEMORY_DIR
        self._init_db()

    def _init_db(self) -> None:
        """初始化进化数据库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 5,
                tags TEXT,
                source TEXT,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT,
                confidence REAL DEFAULT 0.5,
                updated_at TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                summary TEXT NOT NULL,
                key_decisions TEXT,
                topics TEXT,
                created_at TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS concept_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_a TEXT NOT NULL,
                concept_b TEXT NOT NULL,
                relation TEXT,
                weight REAL DEFAULT 1.0,
                created_at TEXT
            )
        """)

        c.execute("CREATE INDEX IF NOT EXISTS idx_mem_hash ON memories(hash)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON memories(category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_mem_created ON memories(created_at)")

        conn.commit()
        conn.close()

    # ── 记忆管理 ─────────────────────────────────────────

    def add_memory(self, content: str, category: str = "general",
                   importance: int = 5, tags: list = None,
                   source: str = "manual") -> bool:
        """
        添加记忆（自动 SHA256 去重，重复时增加访问计数）。
        返回 True 表示新增，False 表示已存在。
        """
        mem_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute("""
                INSERT INTO memories
                (hash, content, category, importance, tags, source, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (mem_hash, content, category, importance,
                  json.dumps(tags or [], ensure_ascii=False), source,
                  datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE hash = ?",
                (datetime.now().isoformat(), mem_hash))
            conn.commit()
            return False
        finally:
            conn.close()

    def get_relevant_memories(self, query: str, limit: int = 5) -> list:
        """基于关键词的相关记忆检索（按 importance 排序）"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        keywords = query.lower().split()
        if not keywords:
            return []

        where_clauses = ' OR '.join(['content LIKE ?' for _ in keywords])
        params = [f'%{kw}%' for kw in keywords] + [limit]

        c.execute(f"""
            SELECT content, category, importance, access_count
            FROM memories
            WHERE {where_clauses}
            ORDER BY importance DESC, access_count DESC, created_at DESC
            LIMIT ?
        """, params)

        results = c.fetchall()
        conn.close()
        return results

    def learn_from_session(self, session_id: str, messages: list) -> None:
        """从会话中自动提炼知识"""
        if not messages:
            return

        preference_keywords = {
            '技术栈': ['Java', 'Python', 'Spring', 'React', 'TypeScript'],
            '工作风格': ['简洁', '详细', '指令式', '结构化'],
            '语言': ['中文', 'English'],
        }

        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')

            if role == 'user':
                for pref_type, keywords in preference_keywords.items():
                    for kw in keywords:
                        if kw in content:
                            self.update_user_profile(pref_type, kw, confidence=0.6)

            if role == 'assistant' and len(content) > 100:
                self.add_memory(content[:500], category='session_knowledge',
                               importance=3, source=f'session:{session_id}')

        print(f"✅ 会话学习完成: {len(messages)} 条消息")

    # ── 用户画像 ─────────────────────────────────────────

    def update_user_profile(self, key: str, value: str, confidence: float = 0.7) -> bool:
        """
        更新用户画像（带置信度机制）。
        新值置信度 > 旧值时覆盖，否则忽略。
        返回 True 表示更新了值。
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT confidence FROM user_profile WHERE key = ?", (key,))
        row = c.fetchone()

        if row is None or confidence > row[0]:
            c.execute("""
                INSERT OR REPLACE INTO user_profile (key, value, confidence, updated_at)
                VALUES (?, ?, ?, ?)
            """, (key, value, confidence, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    def get_user_profile(self) -> dict:
        """获取完整用户画像"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT key, value, confidence FROM user_profile ORDER BY confidence DESC")
        rows = c.fetchall()
        conn.close()
        return {row[0]: {'value': row[1], 'confidence': row[2]} for row in rows}

    # ── 进化与上下文 ──────────────────────────────────────

    def evolve(self, days: int = 7) -> str:
        """定期进化：整合近期记忆，生成 Markdown 进化报告"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).isoformat()

        c.execute("""
            SELECT content, category, importance
            FROM memories
            WHERE created_at >= ? AND importance >= 4
            ORDER BY importance DESC
            LIMIT 20
        """, (since,))

        recent = c.fetchall()
        conn.close()

        report = f"""
## WorkBuddy 自我进化报告（近 {days} 天）

**新记忆数**: {len(recent)}
**高价值记忆**: {sum(1 for r in recent if r[2] >= 5)}
**用户画像**: {len(self.get_user_profile())} 条

### 高价值记忆
"""
        for i, (content, category, importance) in enumerate(recent[:5], 1):
            report += f"{i}. [{category}] {content[:100]}...\n"

        return report

    def get_system_prompt_context(self) -> str:
        """生成上下文注入片段，供 WorkBuddy 系统提示词使用"""
        profile = self.get_user_profile()
        memories = self.get_relevant_memories(' '.join(profile.keys()), limit=3)

        lines = ["\n\n## 已学习的用户偏好"]
        for key, info in profile.items():
            lines.append(f"- {key}: {info['value']} (置信度: {info['confidence']:.0%})")

        if memories:
            lines.append("\n## 相关历史记忆")
            for content, category, _, _ in memories:
                lines.append(f"- [{category}] {content[:150]}...\n")

        return '\n'.join(lines)

    def refresh_context_cache(self) -> Path:
        """刷新上下文缓存文件（供 Skill 读取）"""
        ctx = self.get_system_prompt_context()
        profile = self.get_user_profile()
        ctx_file = self.memory_dir / "injected_context.json"

        with open(ctx_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "context": ctx,
                "profile": profile,
                "db_path": str(self.db_path),
            }, f, ensure_ascii=False, indent=2)

        return ctx_file


# ── CLI 入口 ───────────────────────────────────────────
if __name__ == "__main__":
    e = EvolutionEngine()

    if len(sys.argv) < 2:
        print("\n用法:")
        print("  add <内容>              添加记忆")
        print("  profile                 查看用户画像")
        print("  search <关键词>         搜索记忆")
        print("  evolve [days]           生成进化报告")
        print("  context                 输出上下文片段")
        print("  cache                   刷新上下文缓存")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "add":
        content = sys.argv[2] if len(sys.argv) > 2 else "测试记忆"
        added = e.add_memory(content)
        print(f"{'✅ 新增记忆' if added else 'ℹ️ 已存在（去重）'}: {content[:50]}")

    elif cmd == "profile":
        profile = e.get_user_profile()
        print(json.dumps(profile, ensure_ascii=False, indent=2))

    elif cmd == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        results = e.get_relevant_memories(keyword)
        for content, category, importance, _ in results:
            print(f"[{category} | 重要度:{importance}] {content[:100]}...")

    elif cmd == "evolve":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print(e.evolve(days))

    elif cmd == "context":
        print(e.get_system_prompt_context())

    elif cmd == "cache":
        path = e.refresh_context_cache()
        print(f"✅ 上下文缓存已刷新: {path}")
