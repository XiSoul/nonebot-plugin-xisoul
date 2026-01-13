from nonebot import on_command, on_message, logger, require
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot, Event
from nonebot.params import CommandArg
from nonebot.typing import T_State
from datetime import datetime
import asyncio
import tempfile
import os

# 确保加载nonebot_plugin_htmlrender插件
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_new_page

from .date_parser import DateParser

# 初始化命令
lunar_calendar_by_date = on_command("黄历", aliases={"老黄历", "黄历查询", "农历"}, priority=5)
# 专门添加hl命令的处理器，确保能处理带参数的hl命令
# 使用更通用的消息处理器，确保能处理带参数的hl命令
hl_command = on_command("hl", priority=3, block=True)
hl_message = on_message(rule=lambda event: str(event.message).strip().startswith("hl "), priority=3, block=True)
logger.info("[黄历] 已注册hl命令处理器")

@hl_command.handle()
async def handle_hl_command(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """
    处理hl命令，转发给handle_lunar_calendar处理
    """
    logger.info(f"[黄历] 收到hl命令，消息内容: {event.message}")
    logger.info(f"[黄历] 命令参数: {args}")
    await handle_lunar_calendar(bot, event, state, args)

@hl_message.handle()
async def handle_hl_message(bot: Bot, event: Event, state: T_State):
    """
    处理带参数的hl消息，如hl 2026-10-11
    """
    message = str(event.message).strip()
    logger.info(f"[黄历] 收到带参数的hl消息: {message}")
    # 提取命令参数
    args_str = message[3:].strip()  # 移除 "hl " 前缀
    # 创建消息对象
    from nonebot.adapters.onebot.v11 import Message
    args = Message(args_str)
    # 调用处理函数
    await handle_lunar_calendar(bot, event, state, args)

@lunar_calendar_by_date.handle()
async def handle_lunar_calendar(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """
    处理黄历查询命令，直接返回网页截图
    
    Args:
        bot: Bot对象
        event: Event对象
        state: 状态对象
        args: 命令参数
    """
    # 获取命令参数
    arg_text = args.extract_plain_text().strip()
    
    try:
        # 解析日期
        parsed_date = DateParser.parse_date_from_command(arg_text)
        
        # 检查日期解析是否成功
        if not parsed_date:
            raise ValueError("无法识别的日期格式，请使用YYYY-MM-DD格式")
        
        # 格式化日期为YYYY-MM-DD
        date_str = DateParser.format_date(*parsed_date)
        logger.info(f"查询日期: {date_str} 的黄历信息")
        
        # 直接使用网页截图方式获取黄历
        await take_huangli_screenshot(bot, event, date_str)
        
    except ValueError as e:
        logger.error(f"日期解析错误: {e}")
        await bot.send(event, f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"查询黄历时出错: {e}")
        await bot.send(event, f"❌ 查询黄历时出错: {str(e)}")

async def take_huangli_screenshot(bot: Bot, event: Event, date_str: str):
    """
    使用nonebot-plugin-htmlrender的异步截图函数，截取指定日期的黄历网页
    """
    try:
        # 构建目标网页URL
        url = f"https://www.huangli123.net/huangli/{date_str}.html"
        logger.info(f"正在截图黄历网页: {url}")
        
        # 使用get_new_page()上下文管理器
        async with get_new_page() as page:
            # 设置页面大小
            await page.set_viewport_size({"width": 1200, "height": 1600})
            
            # 打开目标网页
            await page.goto(url, wait_until="networkidle")
            
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            
            # 可以添加一些额外的等待时间，确保动态内容加载完成
            await asyncio.sleep(2)
            
            # 截取整个页面
            img_bytes = await page.screenshot(full_page=True)
            
            logger.info(f"黄历网页截图成功: {date_str}")
            
            # 发送图片
            await bot.send(event, MessageSegment.image(img_bytes))
            logger.info("黄历图片已发送")
            
    except Exception as e:
        logger.error(f"截图过程中出错: {str(e)}")
        await bot.send(event, "❌ 截图失败，无法获取黄历图片")
        # 详细错误记录到日志
        logger.exception("获取黄历图片时发生异常:")

# 保留send_huangli_image函数，向后兼容
async def send_huangli_image(bot, event, huangli_data: dict):
    """
    生成并发送黄历图片
    
    Args:
        bot: Bot对象
        event: Event对象
        huangli_data: 黄历数据
    """
    # 保留函数定义，向后兼容
    pass

# 为lunar_image.py提供一个可调用的函数，以便在那里也可以使用日期查询功能
async def get_huangli_by_date(date_str: str) -> tuple:
    """
    获取指定日期的黄历数据
    
    Args:
        date_str: 日期字符串，格式为YYYY-MM-DD
        
    Returns:
        包含文本和HTML内容的元组 (text_content, html_content)
    """
    # 简化函数，不再依赖已移除的类
    return ("", "")
