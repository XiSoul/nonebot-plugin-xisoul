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
    return message == "hl"

__plugin_meta__ = PluginMetadata(
    name="黄历",
    description="获取当天的黄历网页截图",
    usage="hl 获取网页截图版",
)

# 命令定义
# 移除汉字命令，只保留hl命令，避免误触发
image_lunar_hl = on_command("hl", priority=10, block=True)
# 添加新的不需要/的命令
image_lunar_direct = on_message(rule=is_image_lunar_command, priority=10, block=True)

def create_temp_directory(temp_dir=None):
    """创建临时文件目录，优先使用系统临时目录，确保在Docker环境中正常工作"""
    # 如果没有指定temp_dir，使用系统临时目录
    if temp_dir is None:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    
    # 确保使用绝对路径
    temp_dir = os.path.abspath(temp_dir)
    
    # 创建目录（包括所有中间目录）
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

def generate_unique_filename(temp_dir=None, prefix="huangli_", ext=".png"):
    """生成唯一的文件名，确保使用绝对路径"""
    # 获取有效的临时目录
    temp_dir = create_temp_directory(temp_dir)
    
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 更精确的时间戳，避免文件名冲突
    unique_filename = os.path.join(temp_dir, f"{prefix}{timestamp}{ext}")
    
    logger.debug(f"生成的文件路径: {unique_filename}")
    return unique_filename

@image_lunar_hl.handle()
@image_lunar_direct.handle()
async def handle_image_lunar(bot: Bot, event: Event):
    """处理图片黄历命令"""
    logger.info("收到图片黄历命令请求")
    
    # 发送提示消息告知用户正在获取截图
    await bot.send(event, "正在获取今日黄历图片，请稍候...")
    
    try:
        # 生成唯一的文件名（内部已处理目录创建）
        image_path = generate_unique_filename()
        
        # 使用nonebot-plugin-htmlrender进行网页截图
        await take_huangli_screenshot(image_path)
        
        logger.info(f"黄历截图已保存至: {image_path}")
        
        # 检查文件是否存在且大小大于0
        if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            logger.info(f"截图文件大小: {os.path.getsize(image_path)} bytes")
            
            # 针对Docker环境优化发送方式
            try:
                # 先尝试不使用file:///前缀
                await bot.send(event, MessageSegment.image(os.path.abspath(image_path)))
                logger.info("黄历图片已发送（直接路径）")
            except Exception:
                # 如果失败，再尝试使用file:///前缀
                await bot.send(event, MessageSegment.image("file:///" + os.path.abspath(image_path)))
                logger.info("黄历图片已发送（带file:///前缀）")
            
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