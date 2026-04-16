"""
auto_learn.py - 自动学习脚本
定时从今日工作日志中提炼新知识，自动存入进化数据库
由 WorkBuddy 自动化任务驱动（每日 22:00 执行）
"""
import re
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加 engine 目录到 path
sys.path.insert(0, str(Path(__file__).parent))
from evolution_engine import EvolutionEngine

MEMORY_DIR = Path(__file__).parent
TODAY = datetime.now().strftime("%Y-%m-%d")
DAILY_FILE = MEMORY_DIR / f"{TODAY}.md"


def extract_knowledge_from_daily() -> list:
    """从今日工作日志中提取可学习的知识点"""
    if not DAILY_FILE.exists():
        return []

    content = DAILY_FILE.read_text(encoding='utf-8')

    patterns = [
        r'完成(?:了|的)?([^\n，。]{5,60})',
        r'开发(?:了|的)?([^\n，。]{5,60})',
        r'配置(?:了|的)?([^\n，。]{5,60})',
        r'模型[:：]\s*([^\n]{3,40})',
    ]

    knowledge = []
    for pat in patterns:
        for match in re.finditer(pat, content):
            text = match.group(1).strip()
            if text and len(text) > 5:
                knowledge.append(text)

    return list(set(knowledge))


def extract_preferences() -> list:
    """从 MEMORY.md 推断用户偏好"""
    prefs = []
    mf = MEMORY_DIR / "MEMORY.md"
    if mf.exists():
        c = mf.read_text(encoding='utf-8')
        if '简体中文' in c:
            prefs.append(('交互偏好', '简洁指令式，使用简体中文', 0.95))
        if '结构化' in c:
            prefs.append(('决策风格', '结构化对比分析，从推荐选项组合', 0.85))
        if '辽宁' in c:
            prefs.append(('单位', '辽宁报刊传媒集团', 0.9))
    return prefs


def main():
    print(f"🔄 开始自动学习 ({TODAY})...")
    e = EvolutionEngine()
    new_count = 0

    knowledge = extract_knowledge_from_daily()
    for item in knowledge:
        added = e.add_memory(f"今日工作：{item}", category="work",
                             importance=3, source="auto_learn")
        if added:
            new_count += 1
            print(f"  📝 新知识: {item[:50]}")

    for key, value, conf in extract_preferences():
        profile = e.get_user_profile()
        if key not in profile or profile[key]['confidence'] < conf:
            e.update_user_profile(key, value, conf)
            print(f"  👤 画像更新: {key} = {value}")

    evolve_report = e.evolve(days=1)
    print(f"\n📊 今日进化摘要:")
    print(evolve_report)

    # 刷新上下文缓存
    ctx_file = e.refresh_context_cache()

    print(f"\n✅ 自动学习完成！新增 {new_count} 条知识")
    print(f"   上下文缓存: {ctx_file}")


if __name__ == "__main__":
    main()
