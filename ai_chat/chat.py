"""
核心功能：与 OpenAI 兼容 API 进行一次性（非流式）对话。

`chat(user_id, group_id, user_text)` 是上层使用的主入口：
1. 找到/创建当前作用域的 SQLite 会话；
2. 拉取最近若干轮历史拼装为 messages；
3. 调用 /chat/completions；
4. 把 user 输入和 assistant 回复都写回数据库；
5. 返回助手回复文本。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import httpx
from nonebot import logger

from . import config, database


class ChatError(RuntimeError):
    """对外抛出的统一异常。"""


def _build_messages(session: Dict, user_text: str, image_base64_list: list = None) -> List[Dict]:
    """组装提交给 API 的 messages 列表。"""
    if image_base64_list is None:
        image_base64_list = []

    messages: List[Dict] = []
    system_prompt = session.get("system_prompt") or config.DEFAULT_SYSTEM_PROMPT
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    history = database.fetch_recent_messages(
        session["id"], limit=config.MAX_CONTEXT_TURNS * 2
    )
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})

    # 检测模型是否支持 vision（简单启发式：包含特定关键词）
    model = session.get("model", config.DEFAULT_MODEL)
    supports_vision = any(kw in model.lower() for kw in ["vision", "gpt-4", "claude-3", "doubao"])

    # 构造用户消息：支持文本 + 图片（如果模型支持）
    user_content = []
    if user_text:
        user_content.append({"type": "text", "text": user_text})

    if supports_vision:
        for b64 in image_base64_list:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })
    else:
        # 模型不支持 vision，只用文本
        if image_base64_list:
            user_content.append({
                "type": "text",
                "text": "[用户发送了图片，但当前模型不支持图片分析]"
            })

    if user_content:
        if len(user_content) == 1 and user_content[0]["type"] == "text":
            # 纯文本：简化为字符串
            messages.append({"role": "user", "content": user_content[0]["text"]})
        else:
            # 混合内容：用数组格式
            messages.append({"role": "user", "content": user_content})

    return messages


async def _call_openai(model: str, messages: List[Dict[str, str]]) -> str:
    """调用 OpenAI 兼容的 /chat/completions 端点，返回首条回复内容。

    抛出 ChatError 时，熔断机制会尝试下一个模型。
    """
    if not config.has_credentials():
        raise ChatError(
            "AI 服务未配置：请在环境变量中设置 OPENAI_BASE_URL 与 OPENAI_API_KEY。"
        )

    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise ChatError(f"请求超时，将尝试其他模型") from exc
    except httpx.HTTPError as exc:
        raise ChatError(f"请求失败，将尝试其他模型：{exc}") from exc

    if resp.status_code >= 400:
        logger.warning(
            f"[ai_chat] API 返回 {resp.status_code}: {resp.text[:300]}"
        )
        # 可重试的错误（会尝试下一个模型）
        if resp.status_code == 502:
            raise ChatError("API 返回 502，将尝试其他模型")
        elif resp.status_code == 503:
            raise ChatError("API 返回 503，将尝试其他模型")
        elif resp.status_code == 504:
            raise ChatError("API 返回 504，将尝试其他模型")
        # 不可重试的错误（直接失败）
        elif resp.status_code == 401:
            raise ChatError("API 密钥无效或已过期（401）")
        elif resp.status_code == 404:
            raise ChatError(f"模型 {model} 不存在或 API 地址错误（404）")
        elif resp.status_code == 429:
            raise ChatError("请求过于频繁（429），请稍后再试")
        else:
            # 其他错误作为可重试
            raise ChatError(f"API 返回 {resp.status_code}，将尝试其他模型")

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise ChatError(f"AI 响应解析失败，将尝试其他模型：{exc}") from exc


# 外部 API ---------------------------------------------------------------
async def chat(
    *,
    user_id: str,
    group_id: Optional[str],
    user_text: str,
    image_base64_list: list = None,
) -> str:
    """一次完整的会话：读取历史 → 调用 API → 写回数据库 → 返回文本。

    支持模型熔断：若当前模型失败，自动降级到列表中的下一个模型。
    """
    if image_base64_list is None:
        image_base64_list = []

    session = database.get_or_create_session(user_id=user_id, group_id=group_id)

    # 自愈：若旧会话存的模型已不在当前可用列表里，迁移到当前默认模型。
    if (
        config.AVAILABLE_MODELS
        and session["model"] not in config.AVAILABLE_MODELS
    ):
        new_model = config.DEFAULT_MODEL
        logger.info(
            f"[ai_chat] 会话 {session['id']} 的模型 {session['model']} "
            f"已不可用，自动迁移到 {new_model}"
        )
        database.update_session_model(session["id"], new_model)
        session["model"] = new_model

    messages = _build_messages(session, user_text, image_base64_list)

    # 模型熔断机制：按照 AVAILABLE_MODELS 列表顺序尝试
    current_model = session["model"]
    available_models = config.AVAILABLE_MODELS if config.AVAILABLE_MODELS else [current_model]

    # 从当前模型开始，依次尝试列表中的后续模型
    try:
        model_index = available_models.index(current_model)
    except ValueError:
        # 当前模型不在列表中，从第一个开始
        model_index = 0

    last_error = None
    for attempt_index in range(model_index, len(available_models)):
        try_model = available_models[attempt_index]
        try:
            logger.info(f"[ai_chat] 尝试模型 {try_model} (尝试 {attempt_index - model_index + 1}/{len(available_models) - model_index})")
            reply = await _call_openai(try_model, messages)
            reply = (reply or "").strip()
            if not reply:
                raise ChatError("AI 返回了空回复。")

            # 成功：更新会话模型并保存消息
            if try_model != current_model:
                logger.info(f"[ai_chat] 模型 {current_model} 失败，已自动降级到 {try_model}")
                database.update_session_model(session["id"], try_model)

            database.append_message(session["id"], "user", user_text)
            database.append_message(session["id"], "assistant", reply)
            return reply

        except ChatError as exc:
            last_error = str(exc)
            logger.warning(f"[ai_chat] 模型 {try_model} 失败：{last_error}")
            # 继续尝试下一个模型
            continue

    # 所有模型都失败了
    if last_error:
        raise ChatError(f"所有模型均不可用。最后错误：{last_error}")
    else:
        raise ChatError("所有模型均不可用。")


def get_session_info(*, user_id: str, group_id: Optional[str]) -> Dict:
    """供指令读取当前会话状态。"""
    return database.get_or_create_session(user_id=user_id, group_id=group_id)
