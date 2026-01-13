"""随机图片获取核心功能 - 仅提供功能函数，命令已移至__init__.py"""

import asyncio
import os
import io
import httpx
from datetime import datetime
from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment

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
    """下载图片到指定路径"""
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
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                
                if any(ctype in content_type.lower() for ctype in ["image", "jpeg", "png", "gif", "webp"]):
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    
                    return True
                else:
                    logger.error(f"响应不是有效的图片类型: {content_type}")
                    return False
            else:
                logger.error(f"下载失败，状态码: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"下载图片时发生异常: {type(e).__name__}: {str(e)}")
        return False

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

# 处理图片请求
async def handle_image_request(bot: Bot, event: Event, image_type: str):
    """处理图片请求"""
    if image_type not in IMAGE_TYPES:
        logger.error(f"未知的图片类型: {image_type}")
        await bot.send(event, "❌ 未知的图片类型")
        return
    
    desc = IMAGE_TYPES[image_type]["description"]
    
    try:
        save_path = await generate_unique_filename(image_type)
        
        if await download_image(image_type, save_path):
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                
                if file_size > 0:
                    try:
                        with open(save_path, 'rb') as f:
                            image_bytes = f.read()
                        await bot.send(event, MessageSegment.image(image_bytes))
                        logger.info(f"{desc}图片已成功发送")
                    except Exception as e:
                        logger.error(f"发送图片失败: {str(e)}")
                        await bot.send(event, f"❌ {desc}图片发送失败，请稍后重试")
                    finally:
                        asyncio.create_task(delete_temp_file(save_path, delay=60))
            else:
                logger.error(f"图片文件不存在: {save_path}")
                await bot.send(event, f"❌ {desc}下载失败，文件不存在")
        else:
            logger.error(f"下载图片失败: {image_type}")
            await bot.send(event, f"❌ {desc}下载失败，请稍后重试。可能是API暂时不可用或网络问题。")
    except Exception as e:
        logger.error(f"获取{desc}时发生错误: 类型={type(e).__name__}, 详情={str(e)}")
        await bot.send(event, f"❌ 获取{desc}失败，请稍后重试。错误信息: {type(e).__name__}")

logger.info("[随机图片] 核心功能加载完成，命令已移至__init__.py")