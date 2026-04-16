"""
context_injector.py - 上下文注入器
在每次 WorkBuddy 启动时自动调用，将进化引擎的上下文输出到标准输出
WorkBuddy 会将此内容注入到 System Prompt 中

使用方式：
1. 直接运行：python3 context_injector.py
2. 在 WorkBuddy 启动时自动调用（由 WorkBuddy automation 或 hook 触发）
"""
import sys
import json
from pathlib import Path
from datetime import datetime

def main():
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from evolution_engine import EvolutionEngine

        e = EvolutionEngine()
        context = e.get_system_prompt_context()

        # 输出到 stdout（WorkBuddy 启动日志可见）
        print("\n" + "=" * 50)
        print("🧠 WorkBuddy 自我进化上下文注入")
        print("=" * 50)
        print(context)
        print("=" * 50)

        # 写入缓存文件（供 Skill 读取）
        ctx_file = e.refresh_context_cache()
        print(f"\n✅ 上下文已注入并缓存到 {ctx_file}")

    except Exception as ex:
        print(f"⚠️ 上下文注入失败: {ex}", file=sys.stderr)

if __name__ == "__main__":
    main()
