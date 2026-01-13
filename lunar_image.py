import os
import asyncio
import io  # 导入io模块用于内存操作
from datetime import datetime
from nonebot import on_command, on_message, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.plugin import PluginMetadata
from nonebot import require

# 确保加载nonebot_plugin_htmlrender插件
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_new_page

# 定义图片黄历规则
async def is_image_lunar_command(event: Event) -> bool:
    message = str(event.message).strip()
    # 只处理纯"hl"消息，带参数的消息由lunar_calendar_by_date.py处理
    return message == "hl"

__plugin_meta__ = PluginMetadata(
    name="黄历",
    description="获取当天的黄历网页截图",
    usage="hl 获取网页截图版",
)

# 命令定义
# 移除on_command处理器，避免与lunar_calendar_by_date.py中的hl_command冲突
# 只保留on_message处理器处理纯"hl"消息
image_lunar_direct = on_message(rule=is_image_lunar_command, priority=15, block=True)

def create_temp_directory(temp_dir=None):
    """创建临时文件目录，根据不同操作系统和环境选择最佳存储位置"""
    # 尝试使用操作系统的环境变量或配置来确定最佳存储位置
    try:
        # 首先尝试使用系统临时目录（适用于所有平台）
        import tempfile
        base_temp_dir = tempfile.gettempdir()
        temp_dir = os.path.join(base_temp_dir, "nonebot_xisoul_temp")
        
        # 确保使用绝对路径
        temp_dir = os.path.abspath(temp_dir)
        
        # 创建目录（包括所有中间目录）
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(f"在系统临时目录创建临时文件夹成功: {temp_dir}")
        
        return temp_dir
    except Exception as e:
        logger.warning(f"使用系统临时目录失败: {str(e)}，尝试使用插件目录")
        
        # 如果系统临时目录失败，尝试使用插件目录下的temp文件夹
        try:
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            temp_dir = os.path.abspath(temp_dir)
            
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
                logger.info(f"在插件目录创建临时文件夹成功: {temp_dir}")
            
            return temp_dir
        except Exception as e2:
            logger.error(f"创建临时目录失败: {str(e2)}")
            # 最后返回当前工作目录作为最后的备选
            fallback_dir = os.path.abspath(os.getcwd())
            logger.warning(f"使用当前工作目录作为最后的备选: {fallback_dir}")
            return fallback_dir

def generate_unique_filename(temp_dir=None, prefix="huangli_", ext=".png"):
    """生成唯一的文件名，确保使用绝对路径"""
    # 获取有效的临时目录
    temp_dir = create_temp_directory(temp_dir)
    
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 更精确的时间戳，避免文件名冲突
    unique_filename = os.path.join(temp_dir, f"{prefix}{timestamp}{ext}")
    
    logger.debug(f"生成的文件路径: {unique_filename}")
    return unique_filename

async def handle_image_lunar(bot: Bot, event: Event):
    """处理图片黄历命令"""
    message = str(event.message).strip()
    logger.info(f"收到图片黄历命令请求: {message}")
    
    try:
        # 生成唯一的文件名（内部已处理目录创建）
        image_path = generate_unique_filename()
        
        # 使用nonebot-plugin-htmlrender进行网页截图
        await take_huangli_screenshot(image_path)
        
        logger.info(f"黄历截图已保存至: {image_path}")
        
        # 检查文件是否存在且大小大于0
        if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            logger.info(f"截图文件大小: {os.path.getsize(image_path)} bytes")
            
            # 针对Docker环境优化：使用BytesIO从内存读取图片并发送，避免路径映射问题
            try:
                # 从文件读取图片数据到内存
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                
                # 使用bytes模式发送图片
                await bot.send(event, MessageSegment.image(image_bytes))
                logger.info("黄历图片已发送（内存读取方式）")
            except Exception as e:
                logger.error(f"发送图片失败: {str(e)}")
                await bot.send(event, "❌ 发送黄历图片失败，请稍后重试")
            finally:
                # 延迟删除临时文件，避免占用过多磁盘空间
                asyncio.create_task(delete_temp_file(image_path, delay=60))
        else:
            await bot.send(event, "❌ 截图失败，无法获取黄历图片")
            logger.error("黄历截图文件不存在或为空")
    except Exception as e:
        logger.error(f"获取黄历图片失败: {str(e)}")
        # 简化错误消息，不暴露系统路径信息
        error_msg = "❌ 获取黄历图片失败，请稍后重试"
        await bot.send(event, error_msg)
        # 详细错误记录到日志
        logger.exception("获取黄历图片时发生异常:")

@image_lunar_direct.handle()
async def handle_image_lunar_direct(bot: Bot, event: Event):
    """处理直接发送的图片黄历命令"""
    # 这个处理器只处理纯"hl"消息，由is_image_lunar_command规则保证
    await handle_image_lunar(bot, event)

async def take_huangli_screenshot(image_path):
    """使用nonebot-plugin-htmlrender的异步截图函数"""
    # 直接使用get_new_page()上下文管理器
    async with get_new_page() as page:
        try:
            # 设置页面大小
            await page.set_viewport_size({"width": 1200, "height": 1600})
            
            # 打开目标网页
            await page.goto("https://www.huangli123.net/huangli/")
            
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            
            # 可以添加一些额外的等待时间，确保动态内容加载完成
            await asyncio.sleep(2)
            
            # 截取整个页面
            await page.screenshot(path=image_path, full_page=True)
            
            logger.info("黄历网页截图成功")
        except Exception as e:
            logger.error(f"截图过程中出错: {str(e)}")
            raise

async def delete_temp_file(file_path, delay=60):
    """延迟删除临时文件"""
    # 等待指定秒数
    await asyncio.sleep(delay)
    
    # 检查文件是否存在，存在则删除
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"临时文件已删除: {file_path}")
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")