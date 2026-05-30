"""
插件配置：从 NoneBot 配置（.env / .env.prod）或操作系统环境变量读取 OpenAI 兼容 API 的参数。

读取优先级：
    1. nonebot.get_driver().config 上的同名字段（小写，pydantic 习惯）
    2. 操作系统环境变量

支持的变量：
    OPENAI_BASE_URL   — API base，例如 https://api.openai.com/v1
    OPENAI_API_KEY    — API key
    OPENAI_MODEL      — 默认模型名（如 gpt-4o-mini）
    OPENAI_MODELS     — 可切换的模型列表，逗号分隔
    AI_CHAT_DB_PATH   — SQLite 数据库文件路径
    AI_CHAT_MAX_TURNS — 携带上下文的最大对话轮数（默认 20）
    AI_CHAT_TIMEOUT   — HTTP 请求超时（秒，默认 120）

由于 NoneBot 在插件 import 期间可能尚未完成 driver 初始化，
本模块的关键变量在 `init_settings()` 中由启动钩子赋值。
"""

import os
from pathlib import Path
from typing import List, Optional


# ----- 默认值（也是模块导入时的占位） -------------------------------
_default_db = Path(__file__).resolve().parent / "ai_chat.db"

OPENAI_BASE_URL: str = ""
OPENAI_API_KEY: str = ""
DEFAULT_MODEL: str = "gpt-4o-mini"
AVAILABLE_MODELS: List[str] = []
DB_PATH: str = str(_default_db)
MAX_CONTEXT_TURNS: int = 20
REQUEST_TIMEOUT: int = 120

# 插件元信息 ----------------------------------------------------------
PLUGIN_NAME = "ai_chat"
PLUGIN_VERSION = "0.1.0"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


# ----- 工具函数 ------------------------------------------------------
def _read(name: str, default: str = "") -> str:
    """先看 NoneBot 配置（小写字段名），再看 os.environ。"""
    try:
        from nonebot import get_driver  # 延迟导入

        cfg = get_driver().config
        # pydantic 通常把 ENV 名小写化
        val = getattr(cfg, name.lower(), None)
        if val is None:
            val = getattr(cfg, name, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    except (ValueError, RuntimeError, ImportError):
        pass
    return os.environ.get(name, default).strip()


def _read_int(name: str, default: int) -> int:
    raw = _read(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def init_settings() -> None:
    """从 NoneBot/系统环境读取配置并填充模块全局变量。

    必须在 NoneBot driver 初始化完成后调用（例如 on_startup 钩子里）。
    可重复调用。
    """
    global OPENAI_BASE_URL, OPENAI_API_KEY, DEFAULT_MODEL, AVAILABLE_MODELS
    global DB_PATH, MAX_CONTEXT_TURNS, REQUEST_TIMEOUT

    OPENAI_BASE_URL = _read("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    OPENAI_API_KEY = _read("OPENAI_API_KEY")

    raw_default = _read("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
    models_raw = _read("OPENAI_MODELS")

    if models_raw:
        # OPENAI_MODELS 作为白名单：只有这里列出的模型可用
        whitelist = [m.strip() for m in models_raw.split(",") if m.strip()]
    else:
        whitelist = [raw_default]

    # DEFAULT_MODEL 必须落在白名单内；不在则改用白名单第一项
    if raw_default in whitelist:
        DEFAULT_MODEL = raw_default
    else:
        DEFAULT_MODEL = whitelist[0] if whitelist else raw_default

    AVAILABLE_MODELS = whitelist

    DB_PATH = _read("AI_CHAT_DB_PATH", str(_default_db))
    MAX_CONTEXT_TURNS = _read_int("AI_CHAT_MAX_TURNS", 20)
    REQUEST_TIMEOUT = _read_int("AI_CHAT_TIMEOUT", 120)


def has_credentials() -> bool:
    """是否已配置可用的 API 凭据。"""
    return bool(OPENAI_API_KEY) and bool(OPENAI_BASE_URL)
