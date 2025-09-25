"""XiSoul 插件包"""

from . import lunar_text
from . import lunar_image
from . import lunar_news  # 导入新闻功能模块
from . import ollama_chat  # 导入Ollama聊天功能模块
from nonebot import on_command, on_message, get_driver, logger
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.plugin import PluginMetadata
from datetime import datetime

__plugin_meta__ = PluginMetadata(
    name="XiSoul 农历黄历",
    description="获取当天的农历黄历信息和实时新闻，包含详细的传统命理、民俗数据和热榜新闻图片",
    usage="/文字黄历 或 @机器人 文字黄历 获取文本版\n/黄历 获取网页截图版\n/新闻图片 获取热榜新闻图片\n/测试黄历 测试插件功能",
    type="application",
    homepage="https://github.com/xisoul/nonebot-plugin-xisoul",  # 更新为连字符版本
    supported_adapters=["nonebot.adapters.onebot.v11"],
)

# 添加全局帮助命令
# 更激进的修复方案：重新设计帮助命令，增强可靠性
# 1. 首先移除旧的帮助命令定义
# global_help = on_command(...)

# 2. 创建一个新的帮助命令，使用更简单的实现
from nonebot.adapters.onebot.v11 import Message, MessageSegment

# 移除之前所有的帮助命令定义
# simple_help = on_command(...) 
# simple_help_alias1 = on_command(...)
# simple_help_alias2 = on_command(...)

# 使用最基础的on_message规则，直接检查消息内容
from nonebot.rule import Rule
from nonebot.typing import T_State

# 创建一个非常简单的规则，直接检查消息是否以特定命令开头
def is_help_command():
    async def _is_help_command(bot: Bot, event: Event, state: T_State) -> bool:
        # 获取原始消息文本
        raw_message = event.get_plaintext().strip()
        # 检查是否是帮助命令
        return raw_message in ["帮助", "/帮助", "插件帮助", "/插件帮助", "xihelp", "/xihelp"]
    return Rule(_is_help_command)

# 使用on_message和自定义规则创建帮助命令处理器
basic_help = on_message(rule=is_help_command(), priority=1, block=True)

@basic_help.handle()
async def handle_basic_help(bot: Bot, event: Event):
    """使用最基础的方式处理帮助命令"""
    # 记录详细日志以便调试
    logger.info("[BASIC HELP] 检测到帮助命令")
    logger.info(f"[BASIC HELP] 消息内容: {event.get_plaintext()}")
    logger.info(f"[BASIC HELP] 事件类型: {type(event).__name__}")
    logger.info(f"[BASIC HELP] 用户ID: {event.get_user_id()}")
    
    try:
        # 使用最简单的纯文本消息格式
        help_text = "XiSoul插件帮助\n"
        help_text += "1. 文字黄历 - 获取文本版黄历\n"
        help_text += "2. 黄历 - 获取图片版黄历\n"
        help_text += "3. 新闻图片 - 获取热榜新闻\n"
        help_text += "4. @机器人+消息 - 开始聊天\n"
        help_text += "5. 切换千问/切换gpt/切换deepseek - 切换模型\n"
        help_text += "6. 测试黄历 - 测试插件功能\n"
        help_text += "7. 当前模型/模型列表 - 查看模型信息"
        
        logger.info(f"[BASIC HELP] 准备发送帮助文本: {help_text}")
        
        # 使用最简单的send方法，不使用任何特殊格式
        await bot.send(event, help_text)
        logger.info("[BASIC HELP] 帮助消息发送成功")
        
    except Exception as e:
        logger.error(f"[BASIC HELP] 发送失败: {type(e).__name__}: {str(e)}")
        
        # 作为最后的尝试，使用finish方法
        try:
            await basic_help.finish("帮助: 文字黄历/黄历/新闻图片/@机器人聊天")
        except Exception as e2:
            logger.error(f"[BASIC HELP] 最后的尝试也失败: {type(e2).__name__}: {str(e2)}")

# 从环境变量获取配置
config = get_driver().config
lunar_calendar_api_key = getattr(config, "lunar_calendar_api_key", "")

# 测试命令定义
test_lunar = on_command("测试黄历", priority=10, block=True)

@test_lunar.handle()
async def handle_test_lunar(bot: Bot, event: Event):
    """处理测试黄历命令"""
    logger.info("收到测试黄历命令")
    
    # 构造测试消息
    test_message = [
        "✅ XiSoul 插件测试成功",
        "=" * 30,
        f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "⚙️ 插件状态: 正常运行",
        "🔑 API密钥: " + ("已配置" if lunar_calendar_api_key else "未配置"),
        "💡 使用方法:",
        "  /文字黄历 或 @机器人 文字黄历 获取文本版",
        "  /黄历 获取网页截图版",
        "  /新闻图片 获取热榜新闻图片",
        "=" * 30,
        "🎉 测试完成！可以使用以上命令查询当日黄历信息和新闻。"
    ]
    
    # 使用bot.send发送测试消息
    await bot.send(event, "\n".join(test_message))