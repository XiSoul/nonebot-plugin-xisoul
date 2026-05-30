"""随机图片获取核心功能 - 仅提供功能函数，命令已移至__init__.py"""

import asyncio
import os
import re
import httpx
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

# 图片API基础URL
BASE_URL = "https://api.yviii.com/img/"

# 命令映射关系
IMAGE_TYPES = {
    "sjbs": {"api_param": "baisi", "description": "随机白丝"},
    "sjhs": {"api_param": "heisi", "description": "随机黑丝"},
    "sjmt": {"api_param": "suiji", "description": "随机美图"},
    "sjecy": {"api_param": "ecy", "description": "二次元图片"},
    "sjsk": {"api_param": "meitu", "description": "4K美女高青图片"},
}

MAX_IMAGE_COUNT = 10
FORWARD_RECALL_DELAY = 8


@dataclass
class DownloadedImage:
    path: str
    source_url: Optional[str] = None


def _image_segment(image: "DownloadedImage") -> MessageSegment:
    """构造图片消息段。

    优先使用本地文件路径（file:// URI）+ ``cache=False`` 发送，
    多数 OneBot 客户端在这种情况下会走"原图"上传链路，
    比 base64 / bytes 走法更不容易被 QQ 服务端重新压缩。
    """
    return MessageSegment.image(file=Path(image.path), cache=False)


def parse_image_request_count(message: str, image_type: str) -> Optional[int]:
    """解析随机图片命令中的图片数量。

    支持以下格式：
    - sjbs
    - /sjbs
    - sjbs10
    - /sjbs10
    - sjbs 10
    - /sjbs 10
    """
    pattern = rf"^/?{re.escape(image_type)}(?:\s*(\d+))?$"
    match = re.fullmatch(pattern, message.strip())
    if not match:
        return None
    count_text = match.group(1)
    return int(count_text) if count_text else 1

# 创建临时目录
async def create_temp_directory():
    """创建临时文件目录，根据不同操作系统和环境选择最佳存储位置"""
    try:
        import tempfile
        base_temp_dir = tempfile.gettempdir()
        temp_dir = os.path.join(base_temp_dir, "nonebot_xisoul_temp")
        
        temp_dir = os.path.abspath(temp_dir)
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(f"在系统临时目录创建临时文件夹成功: {temp_dir}")
        
        return temp_dir
    except Exception as e:
        logger.warning(f"使用系统临时目录失败: {str(e)}，尝试使用插件目录")
        
        try:
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            temp_dir = os.path.abspath(temp_dir)
            
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
                logger.info(f"在插件目录创建临时文件夹成功: {temp_dir}")
            
            return temp_dir
        except Exception as e2:
            logger.error(f"创建临时目录失败: {str(e2)}")
            fallback_dir = os.path.abspath(os.getcwd())
            logger.warning(f"使用当前工作目录作为最后的备选: {fallback_dir}")
            return fallback_dir

# 生成唯一文件名
async def generate_unique_filename(image_type):
    """生成唯一的文件名"""
    temp_dir = await create_temp_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = os.path.join(temp_dir, f"{image_type}_{timestamp}.jpg")
    return filename

# 下载图片
async def download_image(image_type, save_path):
    """下载图片到指定路径并返回最终图片URL。"""
    try:
        api_param = IMAGE_TYPES[image_type]["api_param"]
        url = f"{BASE_URL}{api_param}"

        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }

            response = await client.get(url, headers=headers, follow_redirects=True)
            logger.info(f"API 响应状态: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}, 内容大小: {len(response.content)} bytes")

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "").lower()

                # 更宽松的 content-type 检查
                is_image = (
                    "image" in content_type or
                    "jpeg" in content_type or
                    "png" in content_type or
                    "gif" in content_type or
                    "webp" in content_type or
                    len(response.content) > 1000  # 如果内容大于 1KB，可能是图片
                )

                if is_image:
                    # 检查内容是否为空
                    if not response.content or len(response.content) == 0:
                        logger.error(f"下载的图片内容为空")
                        return None

                    with open(save_path, "wb") as f:
                        f.write(response.content)

                    # 验证文件是否成功写入
                    if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
                        logger.error(f"图片文件写入失败或为空: {save_path}")
                        return None

                    logger.info(f"图片下载成功: {save_path}")
                    return str(response.url)
                else:
                    logger.error(f"响应不是有效的图片类型: {content_type}, 内容预览: {response.text[:200]}")
                    return None
            else:
                logger.error(f"下载失败，状态码: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"下载图片时发生异常: {type(e).__name__}: {str(e)}")
        return None

# 延迟删除临时文件
async def delete_temp_file(file_path, delay=60):
    """延迟删除临时文件"""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"临时文件已删除: {file_path}")
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")


async def fetch_image_file(image_type: str) -> Optional[DownloadedImage]:
    """下载单张图片并返回临时文件信息。"""
    save_path = await generate_unique_filename(image_type)
    try:
        source_url = await download_image(image_type, save_path)
        if not source_url:
            return None
        if not os.path.exists(save_path):
            logger.error(f"图片文件不存在: {save_path}")
            return None
        if os.path.getsize(save_path) <= 0:
            logger.error(f"图片文件为空: {save_path}")
            return None
        return DownloadedImage(path=save_path, source_url=source_url)
    except Exception as e:
        logger.error(f"准备图片文件失败: {type(e).__name__}: {str(e)}")
        return None


async def read_image_bytes(file_path: str) -> Optional[bytes]:
    """读取本地图片字节。"""
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except Exception as e:
        logger.error(f"读取图片失败: {type(e).__name__}: {str(e)}")
        return None


def extract_message_id(api_result) -> Optional[int]:
    """从 send_msg 返回结果中提取 message_id。"""
    if isinstance(api_result, dict):
        message_id = api_result.get("message_id")
        return int(message_id) if message_id is not None else None
    message_id = getattr(api_result, "message_id", None)
    return int(message_id) if message_id is not None else None


async def send_temp_images_and_collect_ids(
    bot: Bot, event: Event, images: list[DownloadedImage]
) -> list[int]:
    """逐条发送图片消息并收集 message_id，用于构造引用型合并转发。"""
    message_ids: list[int] = []
    for image in images:
        if not os.path.exists(image.path) or os.path.getsize(image.path) <= 0:
            continue
        image_bytes = await read_image_bytes(image.path)
        if not image_bytes:
            continue
        params = {
            "message_type": getattr(event, "message_type", "group"),
            "message": MessageSegment.image(image_bytes),
        }
        if getattr(event, "message_type", "") == "group" and hasattr(event, "group_id"):
            params["group_id"] = event.group_id
        else:
            params["user_id"] = event.user_id
        result = await bot.call_api("send_msg", **params)
        message_id = extract_message_id(result)
        if message_id is not None:
            message_ids.append(message_id)
        await asyncio.sleep(0.4)
    return message_ids


async def send_temp_images_to_self_and_collect_ids(
    bot: Bot, images: list[DownloadedImage]
) -> list[int]:
    """将图片临时私聊发送给机器人自己，收集 message_id 用于群聊合并转发。"""
    message_ids: list[int] = []
    for image in images:
        if not os.path.exists(image.path) or os.path.getsize(image.path) <= 0:
            continue
        image_bytes = await read_image_bytes(image.path)
        if not image_bytes:
            continue
        result = await bot.call_api(
            "send_private_msg",
            user_id=int(bot.self_id),
            message=MessageSegment.image(image_bytes),
        )
        message_id = extract_message_id(result)
        if message_id is not None:
            message_ids.append(message_id)
        await asyncio.sleep(0.4)
    return message_ids


async def delete_messages(bot: Bot, message_ids: list[int]) -> None:
    """撤回临时消息。"""
    for message_id in message_ids:
        try:
            await bot.call_api("delete_msg", message_id=message_id)
        except Exception as e:
            logger.warning(f"撤回临时消息失败 {message_id}: {type(e).__name__}: {str(e)}")


async def delete_messages_after_delay(
    bot: Bot, message_ids: list[int], delay: float = FORWARD_RECALL_DELAY
) -> None:
    """延迟撤回原始图片消息，给合并转发留出落库时间。"""
    await asyncio.sleep(delay)
    await delete_messages(bot, message_ids)


async def send_forward_by_message_ids(
    bot: Bot, event: Event, message_ids: list[int]
) -> None:
    """使用已发送消息的 message_id 发送真正的合并转发卡片。"""
    nodes = [
        {"type": "node", "data": {"id": str(message_id)}}
        for message_id in message_ids
    ]
    if getattr(event, "message_type", "") == "group" and hasattr(event, "group_id"):
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=nodes)
        return
    await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=nodes)


async def send_group_forward_by_message_ids(
    bot: Bot, group_id: int, message_ids: list[int]
) -> None:
    """将已发送消息的 message_id 作为节点合并转发到指定群。"""
    nodes = [
        {"type": "node", "data": {"id": str(message_id)}}
        for message_id in message_ids
    ]
    await bot.call_api("send_group_forward_msg", group_id=group_id, messages=nodes)


async def send_combined_images(bot: Bot, event: Event, images: list[DownloadedImage]) -> None:
    """将多张图片作为一条普通消息发送。"""
    message = Message()
    for index, image in enumerate(images):
        if not os.path.exists(image.path) or os.path.getsize(image.path) <= 0:
            continue
        if index > 0:
            message += MessageSegment.text("\n")
        message += _image_segment(image)

    if len(message) == 0:
        raise RuntimeError("没有可发送的图片内容")

    await bot.send(event, message)


async def send_images_sequentially(bot: Bot, event: Event, images: list[DownloadedImage]) -> None:
    """逐条发送多张图片，作为组合消息失败时的兜底。"""
    for image in images:
        if os.path.exists(image.path) and os.path.getsize(image.path) > 0:
            await bot.send(event, _image_segment(image))

# 处理图片请求
async def handle_image_request(bot: Bot, event: Event, image_type: str):
    """处理图片请求"""
    if image_type not in IMAGE_TYPES:
        logger.error(f"未知的图片类型: {image_type}")
        await bot.send(event, "❌ 未知的图片类型")
        return

    desc = IMAGE_TYPES[image_type]["description"]
    raw_message = getattr(event, "raw_message", str(event.message))
    count = parse_image_request_count(raw_message, image_type)
    if count is None:
        count = 1
    if count < 1 or count > MAX_IMAGE_COUNT:
        await bot.send(
            event,
            f"❌ 数量必须在1到{MAX_IMAGE_COUNT}之间，例如：{image_type} 或 {image_type}{MAX_IMAGE_COUNT}",
        )
        return

    try:
        images: list[DownloadedImage] = []
        for _ in range(count):
            image = await fetch_image_file(image_type)
            if image:
                images.append(image)

        if not images:
            logger.error(f"下载图片失败: {image_type}")
            await bot.send(
                event,
                f"❌ {desc}下载失败，请稍后重试。可能是API暂时不可用或网络问题。",
            )
            return

        if len(images) == 1:
            if not os.path.exists(images[0].path) or os.path.getsize(images[0].path) <= 0:
                await bot.send(event, f"❌ {desc}图片发送失败，请稍后重试")
                return
            image_bytes = await read_image_bytes(images[0].path)
            if not image_bytes:
                await bot.send(event, f"❌ {desc}图片发送失败，请稍后重试")
                return
            await bot.send(event, MessageSegment.image(image_bytes))
            logger.info(f"{desc}图片已成功发送")
            return

        try:
            if getattr(event, "message_type", "") == "group" and hasattr(event, "group_id"):
                private_message_ids = await send_temp_images_to_self_and_collect_ids(bot, images)
                if len(private_message_ids) != len(images):
                    raise RuntimeError(
                        f"私聊临时消息数量不足: {len(private_message_ids)}/{len(images)}"
                    )
                await asyncio.sleep(1.2)
                await send_group_forward_by_message_ids(bot, event.group_id, private_message_ids)
                logger.info(f"{desc}图片已成功通过私聊消息引用合并转发到群，共{len(images)}张")
                asyncio.create_task(delete_messages_after_delay(bot, private_message_ids))
            else:
                temp_message_ids = await send_temp_images_and_collect_ids(bot, event, images)
                if len(temp_message_ids) != len(images):
                    raise RuntimeError(f"临时消息数量不足: {len(temp_message_ids)}/{len(images)}")
                await asyncio.sleep(1.2)
                await send_forward_by_message_ids(bot, event, temp_message_ids)
                logger.info(f"{desc}图片已成功通过消息引用合并转发，共{len(images)}张")
                asyncio.create_task(delete_messages_after_delay(bot, temp_message_ids))
        except Exception as e:
            logger.warning(f"{desc}私聊引用合并失败，回退到群内逐条消息方案: {type(e).__name__}: {str(e)}")
            try:
                temp_message_ids = await send_temp_images_and_collect_ids(bot, event, images)
                if len(temp_message_ids) != len(images):
                    raise RuntimeError(f"群内临时消息数量不足: {len(temp_message_ids)}/{len(images)}")
                await asyncio.sleep(1.2)
                await send_forward_by_message_ids(bot, event, temp_message_ids)
                logger.info(f"{desc}图片已成功回退到群内消息引用合并转发，共{len(images)}张")
                asyncio.create_task(delete_messages_after_delay(bot, temp_message_ids))
            except Exception as inner_e:
                logger.warning(f"{desc}群内消息引用合并也失败，已保留逐条图片消息: {type(inner_e).__name__}: {str(inner_e)}")
                await bot.send(event, "⚠️ 聊天记录合并失败，已保留逐条发送的图片消息。")

        if len(images) < count:
            await bot.send(
                event,
                f"⚠️ 目标{count}张，实际成功获取{len(images)}张，已先发送成功部分。",
            )
    except Exception as e:
        logger.error(f"获取{desc}时发生错误: 类型={type(e).__name__}, 详情={str(e)}")
        await bot.send(event, f"❌ 获取{desc}失败，请稍后重试。错误信息: {type(e).__name__}")
    finally:
        for image in locals().get("images", []):
            asyncio.create_task(delete_temp_file(image.path, delay=60))

logger.info("[随机图片] 核心功能加载完成，命令已移至__init__.py")
