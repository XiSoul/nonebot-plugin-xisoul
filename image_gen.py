"""
图片生成功能 - 基于独立 API 的文本到图片生成

支持独立配置，与 AI 聊天共用同一套 NoneBot 配置读取机制。

环境变量：
    IMAGE_GEN_BASE_URL  — 绘图 API 地址（必填）
    IMAGE_GEN_API_KEY   — 绘图 API Key（必填）
    IMAGE_GEN_MODEL     — 模型名（默认 dall-e-3）
    IMAGE_GEN_SIZE      — 图片尺寸（默认 1024x1024）
    IMAGE_GEN_QUALITY   — 质量 standard/hd（默认 standard）
    IMAGE_GEN_TIMEOUT   — 请求超时秒数（默认 120）
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
from typing import Optional

import httpx
from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment


# -----------------------------------------------------------------------
# 独立配置（从 NoneBot config 或环境变量读取）
# -----------------------------------------------------------------------
def _read_env(name: str, default: str = "") -> str:
    """先看 NoneBot 配置，再看 os.environ。"""
    try:
        from nonebot import get_driver as _gd
        val = getattr(_gd().config, name.lower(), None)
        if val is None:
            val = getattr(_gd().config, name, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get(name, default).strip()


# 生成配置（启动时初始化）
IMAGE_GEN_CONFIG: dict = {}


def _init_config() -> None:
    """从环境变量读取绘图配置。"""
    global IMAGE_GEN_CONFIG
    IMAGE_GEN_CONFIG = {
        "base_url": _read_env("IMAGE_GEN_BASE_URL", "").rstrip("/"),
        "api_key": _read_env("IMAGE_GEN_API_KEY", ""),
        "model": _read_env("IMAGE_GEN_MODEL", "dall-e-3"),
        "size": _read_env("IMAGE_GEN_SIZE", "1024x1024"),
        "quality": _read_env("IMAGE_GEN_QUALITY", "standard"),
        "n": 1,
        "timeout": int(_read_env("IMAGE_GEN_TIMEOUT", "120") or "120"),
    }


# NoneBot driver 启动时初始化
_driver = get_driver()
@_driver.on_startup
async def _image_gen_startup() -> None:
    _init_config()
    if not IMAGE_GEN_CONFIG.get("base_url") or not IMAGE_GEN_CONFIG.get("api_key"):
        logger.warning("[图片生成] 未配置 IMAGE_GEN_BASE_URL / IMAGE_GEN_API_KEY，生图功能不可用")
    else:
        logger.info(
            f"[图片生成] 已就绪：base={IMAGE_GEN_CONFIG['base_url']} "
            f"model={IMAGE_GEN_CONFIG['model']}"
        )


def has_image_gen_credentials() -> bool:
    """是否已配置绘图 API 凭据。"""
    cfg = IMAGE_GEN_CONFIG
    return bool(cfg.get("base_url")) and bool(cfg.get("api_key"))

# 命令关键词（支持多种触发方式）
COMMAND_KEYWORDS = ["生图", "生成图片", "画图", "生成图"]

# 命令匹配正则
COMMAND_PATTERN = r"^(?:生图|生成图片|画图|生成图)(?:[:：\s])(.+)$"


def parse_image_gen_command(message: str) -> Optional[str]:
    """解析生图命令，返回提示词。

    支持格式：
    - 生图 女孩 霓虹灯
    - 生图: 女孩 霓虹灯
    - 生图：女孩 霓虹灯
    - /生图 女孩 霓虹灯
    """
    message = message.strip()
    # 移除前缀 /
    if message.startswith("/"):
        message = message[1:]

    match = re.match(COMMAND_PATTERN, message)
    if match:
        return match.group(1).strip()
    return None


async def generate_image(
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    size: str = IMAGE_GEN_CONFIG.get("size", "1024x1024"),
    quality: str = IMAGE_GEN_CONFIG.get("quality", "standard"),
) -> Optional[bytes]:
    """调用绘图 API 生成图片，返回图片字节。"""
    if not base_url or not api_key:
        logger.error("[图片生成] API 未配置")
        return None

    if not prompt or len(prompt.strip()) == 0:
        logger.error("[图片生成] 提示词为空")
        return None

    url = f"{base_url}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": IMAGE_GEN_CONFIG.get("n", 1),
        "response_format": "b64_json",
    }

    try:
        logger.info(f"[图片生成] 开始生成图片：模型={model}，提示词={prompt[:50]}")
        async with httpx.AsyncClient(timeout=IMAGE_GEN_CONFIG.get("timeout", 120)) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code >= 400:
            logger.error(
                f"[图片生成] API 返回 {resp.status_code}: {resp.text[:300]}"
            )
            return None

        data = resp.json()
        # OpenAI 返回格式：{"data": [{"b64_json": "..."}]}
        if "data" in data and len(data["data"]) > 0:
            b64_str = data["data"][0].get("b64_json")
            if b64_str:
                image_bytes = base64.b64decode(b64_str)
                logger.info(f"[图片生成] 图片生成成功，大小={len(image_bytes)} bytes")
                return image_bytes

        logger.error(f"[图片生成] API 响应格式错误：{data}")
        return None

    except httpx.TimeoutException:
        logger.error("[图片生成] 请求超时")
        return None
    except Exception as e:
        logger.error(f"[图片生成] 生成失败：{type(e).__name__}: {str(e)}")
        return None


async def handle_image_gen_request(bot: Bot, event: Event, prompt: str) -> None:
    """处理生图请求。"""
    cfg = IMAGE_GEN_CONFIG

    # 检查绘图 API 配置
    if not has_image_gen_credentials():
        await bot.send(event, "⚠️ 生图服务未配置（需要 IMAGE_GEN_BASE_URL 和 IMAGE_GEN_API_KEY）")
        return

    if len(prompt) > 500:
        await bot.send(event, "❌ 提示词过长（最多500字符）")
        return

    # 异步生成图片
    asyncio.create_task(
        _generate_and_send(
            bot,
            event,
            prompt,
            cfg["base_url"],
            cfg["api_key"],
            cfg["model"],
            cfg.get("size", "1024x1024"),
            cfg.get("quality", "standard"),
        )
    )


async def _generate_and_send(
    bot: Bot,
    event: Event,
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    size: str,
    quality: str,
) -> None:
    """后台生成并发送图片。"""
    try:
        image_bytes = await generate_image(prompt, base_url, api_key, model, size, quality)

        if not image_bytes:
            await bot.send(event, "❌ 图片生成失败，请稍后重试或修改提示词")
            return

        # 发送图片
        await bot.send(event, MessageSegment.image(image_bytes))
        logger.info(f"[图片生成] 图片已成功发送给用户")

    except Exception as e:
        logger.error(f"[图片生成] 发送图片失败：{type(e).__name__}: {str(e)}")
        await bot.send(event, f"⚠️ 发送图片失败：{str(e)}")
