import os
import asyncio
import os  # 需要导入os模块用于创建目录
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
    return message == "黄历"

__plugin_meta__ = PluginMetadata(
    name="黄历",
    description="获取当天的黄历网页截图",
    usage="黄历 获取网页截图版",
)

# 命令定义
# 保留原有的命令以便兼容
image_lunar = on_command("黄历", priority=10, block=True)
# 添加新的不需要/的命令
image_lunar_direct = on_message(rule=is_image_lunar_command, priority=10, block=True)

def create_temp_directory(temp_dir="temp"):
    """创建临时文件目录"""
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def generate_unique_filename(temp_dir="temp", prefix="huangli_", ext=".png"):
    """生成唯一的文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(temp_dir, f"{prefix}{timestamp}{ext}")

@image_lunar.handle()
@image_lunar_direct.handle()
async def handle_image_lunar(bot: Bot, event: Event):
    """处理图片黄历命令"""
    logger.info("收到图片黄历命令请求")
    
    # 发送提示消息告知用户正在获取截图
    await bot.send(event, "正在获取今日黄历图片，请稍候...")
    
    try:
        # 创建临时文件目录
        temp_dir = create_temp_directory()
        
        # 生成唯一的文件名
        image_path = generate_unique_filename(temp_dir)
        
        # 使用nonebot-plugin-htmlrender进行网页截图
        await take_huangli_screenshot(image_path)
        
        logger.info(f"黄历截图已保存至: {image_path}")
        
        # 检查文件是否存在且大小大于0
        if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            # 使用MessageSegment发送图片
            await bot.send(event, MessageSegment.image("file:///" + os.path.abspath(image_path)))
            logger.info("黄历图片已发送")
            
            # 延迟删除临时文件，避免占用过多磁盘空间
            asyncio.create_task(delete_temp_file(image_path, delay=60))
        else:
            await bot.send(event, "❌ 截图失败，无法获取黄历图片")
            logger.error("黄历截图文件不存在或为空")
    except Exception as e:
        logger.error(f"获取黄历图片失败: {str(e)}")
        error_msg = f"❌ 获取黄历图片失败: {str(e)}"
        await bot.send(event, error_msg)

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