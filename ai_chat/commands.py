"""
指令处理层（仅指令逻辑，不直接注册 matcher）。

风格参考 Codex / Claude Code：以 `/` 开头的斜杠指令。
当前支持：/help、/new（别名 /clear）、/model。

每个 handle_* 函数接收已解析的参数，返回应回复给用户的文本字符串。
由 __init__.py 中的 matcher 负责调用与回复。
"""

from __future__ import annotations

from typing import Optional

from . import chat, config, database


HELP_TEXT = (
    "🤖 AI 聊天插件\n"
    "—— 群聊：@机器人 + 内容 进行对话\n"
    "—— 私聊：直接发送内容\n"
    "\n"
    "可用指令（@机器人 或私聊后跟指令）：\n"
    "  /help              查看本帮助\n"
    "  /new   (或 /clear) 开始新会话，清空上下文\n"
    "  /model             查看当前模型\n"
    "  /models            查看所有可用模型\n"
    "  /model <名称>      切换模型（必须在可用列表中）\n"
)


def handle_help() -> str:
    return HELP_TEXT


def handle_new(*, user_id: str, group_id: Optional[str]) -> str:
    session = database.get_or_create_session(user_id=user_id, group_id=group_id)
    database.reset_session(session["id"])
    return "✅ 已开启新会话，之前的上下文已清空。"


def handle_model(
    *,
    user_id: str,
    group_id: Optional[str],
    target: Optional[str],
) -> str:
    session = chat.get_session_info(user_id=user_id, group_id=group_id)
    current = session["model"]

    if not target:
        available = "\n".join(f"  • {m}" for m in config.AVAILABLE_MODELS)
        return (
            f"📦 当前模型：{current}\n"
            f"可用模型：\n{available}\n\n"
            f"切换：/model <名称>"
        )

    if config.AVAILABLE_MODELS and target not in config.AVAILABLE_MODELS:
        available = ", ".join(config.AVAILABLE_MODELS)
        return (
            f"❌ 未知模型：{target}\n"
            f"仅允许使用：{available}"
        )

    database.update_session_model(session["id"], target)
    return f"✅ 已切换模型：{current} → {target}"


def handle_models() -> str:
    if not config.AVAILABLE_MODELS:
        return "⚠️ 未配置任何可用模型，请检查环境变量 OPENAI_MODELS。"
    lines = [f"📦 可用模型（共 {len(config.AVAILABLE_MODELS)} 个）："]
    for m in config.AVAILABLE_MODELS:
        mark = " ⭐" if m == config.DEFAULT_MODEL else ""
        lines.append(f"  • {m}{mark}")
    lines.append("")
    lines.append("切换：/model <名称>")
    return "\n".join(lines)


# 路由 -------------------------------------------------------------------
def dispatch(
    *,
    text: str,
    user_id: str,
    group_id: Optional[str],
) -> Optional[str]:
    """
    尝试把消息当作斜杠指令解析；
    返回应回复的文本，若不是已知指令则返回 None。
    """
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None

    parts = stripped.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        return handle_help()

    if cmd in ("/new", "/clear"):
        return handle_new(user_id=user_id, group_id=group_id)

    if cmd == "/model":
        return handle_model(
            user_id=user_id,
            group_id=group_id,
            target=arg or None,
        )

    if cmd == "/models":
        return handle_models()

    return f"❓ 未知指令：{cmd}\n输入 /help 查看可用指令。"
