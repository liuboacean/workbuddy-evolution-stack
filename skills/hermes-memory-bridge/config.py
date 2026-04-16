"""
hermes-memory-bridge / config.py
路径与常量配置
"""
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
HERMES_MEMORIES_DIR = HERMES_HOME / "memories"
HERMES_DB = HERMES_HOME / "state.db"

# 共用互通目录（WorkBuddy ↔ Hermes）
SHARED_DIR = HERMES_HOME / "shared"
WORKBUDDY_LOG = SHARED_DIR / "workbuddy.log"
HERMES_LOG = SHARED_DIR / "hermes.log"
BRIDGE_META = SHARED_DIR / "meta.json"

WORKBUDDY_MEMORY_DIR = (
    Path.home() / "WorkBuddy" / "20260415144700" / ".workbuddy" / "memory"
)

ENTRY_DELIMITER = "\n§\n"
MAX_ENTRY_CHARS = 4000
