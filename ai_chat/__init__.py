"""
xisoul.ai_chat —— AI 聊天子模块
=================================
OneBot V11 适配的 AI 聊天功能：
- 群聊 @机器人 触发；
- 私聊直接对话；
- SQLite 持久化每个 (group, user) / (user) 的会话上下文；
- 斜杠指令：/help、/new、/clear、/model、/models。
- OpenAI 兼容 API（地址与密钥通过环境变量配置）。

被 nonebot_plugin_xisoul 主包 import 时自动注册 matcher。
"""

import base64
import re
import httpx
from nonebot import get_driver, logger, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageEvent,
    PrivateMessageEvent,
)
from nonebot.rule import Rule, to_me

from . import chat, commands, config, database


_driver = get_driver()


# -----------------------------------------------------------------------
# 启动钩子：初始化配置与 SQLite
# -----------------------------------------------------------------------
@_driver.on_startup
async def _ai_chat_startup() -> None:
    config.init_settings()
    database.init_db()
    if not config.has_credentials():
        logger.warning(
            "[xisoul.ai_chat] 未检测到 OPENAI_BASE_URL / OPENAI_API_KEY，"
            "AI 对话将无法使用。"
        )
    else:
        logger.info(
            f"[xisoul.ai_chat] 已就绪：base={config.OPENAI_BASE_URL} "
            f"model={config.DEFAULT_MODEL} "
            f"models={config.AVAILABLE_MODELS}"
        )


# -----------------------------------------------------------------------
# 工具
# -----------------------------------------------------------------------
def _extract_segments_text(message_segs) -> tuple[str, list[str]]:
    """从消息段列表中提取文本和图片 URL。

    返回：(文本内容, 图片URL列表)
    """
    text_parts = []
    image_urls = []
    for seg in message_segs:
        seg_type = seg.type if hasattr(seg, "type") else seg.get("type", "")
        seg_data = seg.data if hasattr(seg, "data") else seg.get("data", {})

        if seg_type == "text":
            text_parts.append(seg_data.get("text", ""))
        elif seg_type == "image":
            url = seg_data.get("url") or seg_data.get("file")
            if url:
                image_urls.append(url)
        elif seg_type == "face":
            text_parts.append(f"[表情:{seg_data.get('id', '')}]")
        elif seg_type == "at":
            text_parts.append(f"@{seg_data.get('qq', '')}")
        elif seg_type == "video":
            text_parts.append("[视频]")
        elif seg_type == "file":
            text_parts.append(f"[文件:{seg_data.get('name', '')}]")
        elif seg_type == "record":
            text_parts.append("[语音]")
        elif seg_type == "forward":
            # 合并转发消息标记，需要后续通过 API 获取
            text_parts.append(f"[__FORWARD__:{seg_data.get('id', '')}]")

    return "".join(text_parts).strip(), image_urls


async def _fetch_forward_content(bot: Bot, forward_id: str, depth: int = 0) -> tuple[str, list[str]]:
    """递归获取合并转发消息的内容。

    返回：(文本内容, 图片URL列表)
    """
    if depth > 3:  # 限制递归深度，防止循环
        return "[转发消息嵌套过深]", []

    try:
        result = await bot.call_api("get_forward_msg", message_id=forward_id)
        # result 可能是 {"messages": [...]} 或直接是 messages 列表
        messages = result.get("messages") if isinstance(result, dict) else result
        if not messages:
            return "[转发消息为空]", []

        all_text = []
        all_images = []
        for idx, msg in enumerate(messages):
            sender = msg.get("sender", {}) if isinstance(msg, dict) else {}
            nickname = sender.get("nickname", "") or sender.get("card", "") or "未知用户"

            content = msg.get("content") or msg.get("message", [])
            if isinstance(content, str):
                all_text.append(f"[{nickname}]: {content}")
                continue

            sub_text, sub_images = _extract_segments_text(content)

            # 检测嵌套转发
            if "[__FORWARD__:" in sub_text:
                forward_match = re.search(r"\[__FORWARD__:([^\]]+)\]", sub_text)
                if forward_match:
                    nested_id = forward_match.group(1)
                    nested_text, nested_images = await _fetch_forward_content(
                        bot, nested_id, depth + 1
                    )
                    sub_text = sub_text.replace(
                        f"[__FORWARD__:{nested_id}]",
                        f"[嵌套转发: {nested_text}]",
                    )
                    all_images.extend(nested_images)

            if sub_text:
                all_text.append(f"[{nickname}]: {sub_text}")
            all_images.extend(sub_images)

        return "\n".join(all_text), all_images

    except Exception as e:
        logger.warning(f"[xisoul.ai_chat] 获取转发消息失败 {forward_id}: {e}")
        return f"[转发消息读取失败: {type(e).__name__}]", []


async def _extract_reply_content(bot: Bot, event: MessageEvent) -> tuple[str, list[str]]:
    """提取引用消息的完整内容（文本+图片+嵌套转发）。

    返回：(引用消息文本, 图片URL列表)
    """
    if not (hasattr(event, "reply") and event.reply):
        return "", []

    reply_msg = event.reply
    sender = getattr(reply_msg, "sender", None)
    sender_name = ""
    if sender:
        sender_name = (
            getattr(sender, "nickname", "")
            or getattr(sender, "card", "")
            or ""
        )

    if not hasattr(reply_msg, "message"):
        return "", []

    text, images = _extract_segments_text(reply_msg.message)

    # 兜底1：如果引用消息文本提示是聊天记录但没有 forward 段，尝试通过 get_msg 重新获取
    is_likely_forward = (
        "[__FORWARD__:" not in text
        and any(kw in text for kw in ["聊天记录", "[聊天记录]", "[转发", "群聊的聊天记录", "合并转发"])
    )
    reply_message_id = getattr(reply_msg, "message_id", None)

    if is_likely_forward and reply_message_id:
        logger.info(f"[xisoul.ai_chat] 引用消息可能是合并转发，尝试通过 get_msg 获取详情")
        try:
            msg_detail = await bot.call_api("get_msg", message_id=reply_message_id)
            if isinstance(msg_detail, dict):
                msg_content = msg_detail.get("message", []) or msg_detail.get("content", [])
                if msg_content:
                    if isinstance(msg_content, str):
                        # 字符串格式，尝试用正则找 forward id
                        fwd_match = re.search(r'\[CQ:forward,id=([^\]]+)\]', msg_content)
                        if fwd_match:
                            fwd_id = fwd_match.group(1)
                            fwd_text, fwd_images = await _fetch_forward_content(bot, fwd_id)
                            text = (text + f"\n--- 合并转发内容 ---\n{fwd_text}\n--- 转发结束 ---").strip()
                            images.extend(fwd_images)
                    else:
                        # 数组格式，重新提取
                        new_text, new_images = _extract_segments_text(msg_content)
                        if "[__FORWARD__:" in new_text:
                            text = new_text
                            images = new_images
        except Exception as e:
            logger.warning(f"[xisoul.ai_chat] get_msg 获取引用消息失败: {e}")

    # 检测引用消息中的合并转发
    if "[__FORWARD__:" in text:
        forward_match = re.search(r"\[__FORWARD__:([^\]]+)\]", text)
        if forward_match:
            forward_id = forward_match.group(1)
            forward_text, forward_images = await _fetch_forward_content(bot, forward_id)
            text = text.replace(
                f"[__FORWARD__:{forward_id}]",
                f"\n--- 合并转发内容 ---\n{forward_text}\n--- 转发结束 ---",
            )
            images.extend(forward_images)

    # 兜底2：如果文本包含明显的转发标记但仍没拿到内容，尝试用 reply_message_id 当作 forward_id
    if reply_message_id and "聊天记录" in text and "--- 合并转发内容 ---" not in text:
        logger.info(f"[xisoul.ai_chat] 尝试用 message_id 当作 forward_id 获取内容")
        try:
            fwd_text, fwd_images = await _fetch_forward_content(bot, str(reply_message_id))
            if fwd_text and "失败" not in fwd_text:
                text = (text + f"\n--- 合并转发内容 ---\n{fwd_text}\n--- 转发结束 ---").strip()
                images.extend(fwd_images)
        except Exception as e:
            logger.warning(f"[xisoul.ai_chat] 用 message_id 获取转发失败: {e}")

    if sender_name:
        text = f"{sender_name}: {text}" if text else f"{sender_name}: [无文本内容]"

    return text, images


def _extract_current_message(event: MessageEvent) -> tuple[str, list[str]]:
    """提取当前消息的文本和图片。"""
    return _extract_segments_text(event.get_message())


async def _download_image_as_base64(url: str) -> str:
    """下载图片并转换为 base64 字符串。"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                return base64.b64encode(resp.content).decode("utf-8")
    except Exception as e:
        logger.warning(f"[xisoul.ai_chat] 下载图片失败: {e}")
    return ""


async def _reply(bot: Bot, event: MessageEvent, text: str) -> None:
    if isinstance(event, GroupMessageEvent):
        await bot.send(event, text, at_sender=True, reply_message=True)
    else:
        await bot.send(event, text)


async def _handle(bot: Bot, event: MessageEvent) -> None:
    # 提取当前消息内容
    current_text, current_images = _extract_current_message(event)

    # 提取引用消息内容（含合并转发）
    reply_text, reply_images = await _extract_reply_content(bot, event)

    # 拼接文本：引用消息在前
    if reply_text:
        user_text = f"[引用消息]\n{reply_text}\n[/引用消息]\n\n{current_text}".strip()
    else:
        user_text = current_text

    # 合并图片 URL（引用的图片在前）
    image_urls = reply_images + current_images

    # 如果有图片，尝试下载并转换为 base64
    image_base64_list = []
    for url in image_urls:
        b64 = await _download_image_as_base64(url)
        if b64:
            image_base64_list.append(b64)

    # 如果有图片但都下载失败，提示用户
    if image_urls and not image_base64_list:
        await _reply(bot, event, "⚠️ 图片无法加载，请尝试重新发送或直接描述图片内容。")
        return

    # 如果没有文本且没有图片，忽略
    if not user_text and not image_base64_list:
        return

    user_id = str(event.user_id)
    group_id = (
        str(event.group_id) if isinstance(event, GroupMessageEvent) else None
    )

    cmd_reply = commands.dispatch(
        text=current_text, user_id=user_id, group_id=group_id
    )
    if cmd_reply is not None:
        await _reply(bot, event, cmd_reply)
        return

    try:
        reply = await chat.chat(
            user_id=user_id,
            group_id=group_id,
            user_text=user_text,
            image_base64_list=image_base64_list,
        )
    except chat.ChatError as exc:
        await _reply(bot, event, f"⚠️ {exc}")
        return
    except Exception as exc:  # 兜底
        logger.exception("[xisoul.ai_chat] 处理消息时出错")
        await _reply(bot, event, f"⚠️ 处理出错：{exc}")
        return

    await _reply(bot, event, reply)


# -----------------------------------------------------------------------
# Matcher 注册
# -----------------------------------------------------------------------
async def _is_group(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent)


async def _is_private(event: MessageEvent) -> bool:
    return isinstance(event, PrivateMessageEvent)


# 群聊：必须 @机器人
group_chat = on_message(
    rule=Rule(_is_group) & to_me(),
    priority=20,
    block=True,
)


@group_chat.handle()
async def _on_group(bot: Bot, event: GroupMessageEvent) -> None:
    await _handle(bot, event)


# 私聊：所有私聊消息
private_chat = on_message(rule=Rule(_is_private), priority=20, block=True)


@private_chat.handle()
async def _on_private(bot: Bot, event: PrivateMessageEvent) -> None:
    await _handle(bot, event)


logger.info("[xisoul.ai_chat] 子模块已加载（群聊需 @机器人 触发）")
