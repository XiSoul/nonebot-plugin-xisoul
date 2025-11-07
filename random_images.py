import asyncio
import os
import httpx
from datetime import datetime
from nonebot import on_command, on_message, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="随机图片",
    description="获取各种类型的随机图片，包括白丝、黑丝、随机美图、二次元和4K美女高青图片",
    usage="sjbs - 随机白丝\nsjhs - 随机黑丝\nsjmt - 随机美图\nsjecy - 二次元图片\nsjsk - 4K美女高青图片",
)

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
    """创建临时文件目录，确保在Docker环境中正常工作"""
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    temp_dir = os.path.abspath(temp_dir)
    
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(f"创建临时目录成功: {temp_dir}")
        except Exception as e:
            logger.error(f"创建临时目录失败: {str(e)}")
            # 尝试使用系统临时目录作为备选
            import tempfile
            temp_dir = os.path.join(tempfile.gettempdir(), "nonebot_xisoul_temp")
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(f"使用系统临时目录作为备选: {temp_dir}")
    
    return temp_dir

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
            
            # 检查响应状态
            if response.status_code == 200:
                # 检查内容类型是否为图片
                content_type = response.headers.get("content-type", "")
                
                if any(ctype in content_type.lower() for ctype in ["image", "jpeg", "png", "gif", "webp"]):
                    # 保存图片
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
    # 检查图片类型是否存在
    if image_type not in IMAGE_TYPES:
        logger.error(f"未知的图片类型: {image_type}")
        await bot.send(event, "❌ 未知的图片类型")
        return
    
    desc = IMAGE_TYPES[image_type]["description"]
    
    try:
        # 生成保存路径
        save_path = await generate_unique_filename(image_type)
        
        # 下载图片
        if await download_image(image_type, save_path):
            # 检查文件是否存在且大小大于0
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                
                if file_size > 0:
                            try:
                                # 尝试方式1: 直接使用绝对路径
                                await bot.send(event, MessageSegment.image(save_path))
                            except Exception as e1:
                                logger.warning(f"方式1发送失败，尝试方式2: {str(e1)}")
                                try:
                                    # 尝试方式2: 使用file:///前缀
                                    file_url = f"file:///{save_path}"
                                    await bot.send(event, MessageSegment.image(file_url))
                                except Exception as e2:
                                    logger.warning(f"方式2发送失败，尝试方式3: {str(e2)}")
                                    try:
                                        # 尝试方式3: 使用相对路径
                                        relative_path = os.path.relpath(save_path)
                                        await bot.send(event, MessageSegment.image(relative_path))
                                    except Exception as e3:
                                        logger.error(f"所有发送方式都失败: {str(e3)}")
                                        await bot.send(event, f"❌ 图片发送失败: {type(e3).__name__}")
                else:
                    logger.error(f"图片文件为空: {save_path}")
                    await bot.send(event, f"❌ {desc}下载失败，文件内容为空")
            else:
                logger.error(f"图片文件不存在: {save_path}")
                await bot.send(event, f"❌ {desc}下载失败，文件不存在")
        else:
            logger.error(f"下载图片失败: {image_type}")
            await bot.send(event, f"❌ {desc}下载失败，请稍后重试。可能是API暂时不可用或网络问题。")
    except Exception as e:
        logger.error(f"获取{desc}时发生错误: 类型={type(e).__name__}, 详情={str(e)}")
        await bot.send(event, f"❌ 获取{desc}失败，请稍后重试。错误信息: {type(e).__name__}")

# 定义消息规则
async def is_image_command(event: Event) -> bool:
    """检查是否为图片命令，支持直接命令和带斜杠前缀的命令"""
    message = str(event.message).strip()
    # 检查直接命令或带斜杠前缀的命令
    return message in IMAGE_TYPES.keys() or message.lstrip('/') in IMAGE_TYPES.keys()

# 创建直接消息处理器
image_direct = on_message(rule=is_image_command, priority=10, block=True)

# 创建命令处理器
command_handlers = {}
for image_type in IMAGE_TYPES.keys():
    command_handlers[image_type] = on_command(image_type, priority=10, block=True)
    
    # 动态定义处理函数
    def create_handler(img_type=image_type):
        async def handler(bot: Bot, event: Event):
            await handle_image_request(bot, event, img_type)
        return handler
    
    # 注册处理函数
    command_handlers[image_type].handle()(create_handler())

# 处理直接消息
@image_direct.handle()
async def handle_direct_image(bot: Bot, event: Event):
    """处理直接消息中的图片命令"""
    message = str(event.message).strip()
    # 移除可能的斜杠前缀
    clean_message = message.lstrip('/')
    
    if clean_message in IMAGE_TYPES.keys():
        await handle_image_request(bot, event, clean_message)

# 初始化日志
logger.info("随机图片插件已加载")