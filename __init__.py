"""
XiSoul 插件

提供农历黄历信息、实时新闻图片、随机图片，以及基于 OpenAI 兼容 API 的 AI 聊天功能
"""

# ============================================================
# 自动依赖安装（必须在所有其他 import 之前执行）
# 检测缺失的 pip 包和 Playwright 浏览器，首次启动时自动安装
# 使用 .deps_installed 标记文件避免重复检查
# ============================================================
from .deps_installer import ensure_deps
ensure_deps()

# 插件元数据
__plugin_name__ = "xisoul"
__plugin_version__ = "0.1.0"
__plugin_description__ = "XiSoul 测试插件"
__plugin_author__ = "XiSoul"
__plugin_type__ = "application"

# 导入必要的模块
from nonebot import on_command, on_message, logger, get_driver
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.rule import Rule

# 打印插件加载信息
print(f"[XiSoul] 开始加载插件: {__plugin_name__} v{__plugin_version__}")
logger.info(f"[XiSoul] 开始加载插件: {__plugin_name__} v{__plugin_version__}")

# 获取驱动实例
_driver = get_driver()

# 导入功能模块
from .lunar_text import handle_lunar_calendar, is_text_lunar_command
from .lunar_image import handle_image_lunar, is_image_lunar_command
from .lunar_calendar_by_date import lunar_calendar_by_date, hl_command
from .lunar_news import clear_news_cache, get_news_image
from .random_images import handle_image_request, IMAGE_TYPES, parse_image_request_count
from .image_gen import parse_image_gen_command, handle_image_gen_request

# 注册帮助命令
help_cmd = on_command("帮助", priority=1, block=True)
help_cmd_prefix = on_command("/帮助", priority=1, block=True)
help_cmd_xi = on_command("xihelp", priority=1, block=True)
help_cmd_plugin = on_command("插件帮助", priority=1, block=True)
help_cmd_test = on_command("测试帮助", priority=1, block=True)

# 定义命令规则
async def is_help_command(event: Event) -> bool:
    message = str(event.message).strip()
    return message in ["帮助", "插件帮助", "xihelp"]

# 直接消息规则的帮助命令
help_cmd_direct = on_message(rule=is_help_command, priority=1, block=True)

# 帮助命令处理函数
@help_cmd.handle()
@help_cmd_prefix.handle()
@help_cmd_xi.handle()
@help_cmd_plugin.handle()
@help_cmd_direct.handle()
async def handle_help(bot: Bot, event: Event):
    """处理帮助命令"""
    user_id = event.get_user_id()
    print(f"[XiSoul] 帮助命令被触发! 用户: {user_id}")
    logger.info(f"[XiSoul] 帮助命令被触发! 用户: {user_id}")
    
    # 重新定义帮助信息，确保包含所有命令
    help_message = [
        "📚 XiSoul 插件帮助信息",
        "",
        "🔄 命令格式说明：",
        "• 所有命令支持直接发送或带/前缀发送",
        "",
        "📅 1. 黄历功能",
        "• 文字黄历/文本黄历 - 获取文本版黄历",
        "• hl - 获取图片版黄历",
        "",
        "📰 2. 新闻功能",
        "• 新闻图片 - 获取今日热榜新闻图片",
        "",
        "🖼️ 3. 随机图片功能",
        "• sjbs - 随机白丝图片",
        "• sjhs - 随机黑丝图片",
        "• sjmt - 随机美图",
        "• sjecy - 二次元图片",
        "• sjsk - 4K美女高清图片",
        "• 随机图片命令支持尾部数字，例如 sjbs10",
        "",
        "🎨 4. AI 绘图功能",
        "• 生图 女孩 霓虹灯 - 根据提示词生成图片",
        "• 支持格式：生图 提示词、生图: 提示词、/生图 提示词",
        "",
        "🤖 5. AI 聊天（OpenAI 兼容）",
        "• 群聊：@机器人 + 内容 进行对话",
        "• 私聊：直接发送内容",
        "• /help、/new (或 /clear)、/model、/models",
    ]
    
    # 打印帮助信息到日志，以便调试
    logger.info(f"帮助信息: {help_message}")
    
    await bot.send(event, "\n".join(help_message))

# 测试帮助命令处理函数
@help_cmd_test.handle()
async def handle_test_help(bot: Bot, event: Event):
    """处理测试帮助命令"""
    user_id = event.get_user_id()
    print(f"[XiSoul] 测试帮助命令被触发! 用户: {user_id}")
    logger.info(f"[XiSoul] 测试帮助命令被触发! 用户: {user_id}")
    
    # 定义测试帮助信息
    test_help_message = [
        "📚 XiSoul 测试帮助信息",
        "",
        "🤖 AI聊天功能",
        "• 模型列表 - 从云端获取并查看所有可用模型",
        "• 切换 模型名称 - 切换到指定模型（例如：切换 glm-5）"
    ]
    
    # 打印帮助信息到日志，以便调试
    logger.info(f"测试帮助信息: {test_help_message}")
    
    await bot.send(event, "\n".join(test_help_message))

# 注册随机图片命令 - 白丝命令
sjbs_cmd = on_command("sjbs", priority=10, block=True)
sjbs_cmd_prefix = on_command("/sjbs", priority=10, block=True)

@sjbs_cmd.handle()
@sjbs_cmd_prefix.handle()
async def handle_sjbs(bot: Bot, event: Event):
    """处理白丝图片命令"""
    await handle_image_request(bot, event, "sjbs")

# 直接消息规则的白丝命令
async def is_sjbs_command(event: Event) -> bool:
    message = str(event.message).strip()
    return parse_image_request_count(message, "sjbs") is not None

sjbs_cmd_direct = on_message(rule=is_sjbs_command, priority=10, block=True)

@sjbs_cmd_direct.handle()
async def handle_sjbs_direct(bot: Bot, event: Event):
    """处理直接发送的白丝图片命令"""
    await handle_image_request(bot, event, "sjbs")

# 注册其他随机图片命令
def register_other_image_commands():
    """注册其他随机图片相关命令"""
    other_types = ["sjhs", "sjmt", "sjecy", "sjsk"]
    
    # 使用辅助函数创建处理函数，避免闭包问题
    def create_handler(image_type):
        async def handler(bot: Bot, event: Event):
            await handle_image_request(bot, event, image_type)
        return handler
    
    for cmd_type in other_types:
        if cmd_type in IMAGE_TYPES:
            # 不带前缀的命令
            cmd = on_command(cmd_type, priority=10, block=True)
            cmd.handle()(create_handler(cmd_type))
            
            # 带前缀的命令
            cmd_prefix = on_command(f"/{cmd_type}", priority=10, block=True)
            cmd_prefix.handle()(create_handler(cmd_type))
            
            # 直接消息规则的命令 - 使用辅助函数捕获cmd_type值
            def create_image_rule(image_type):
                async def _image_rule(event: Event) -> bool:
                    message = str(event.message).strip()
                    return parse_image_request_count(message, image_type) is not None
                return _image_rule
            cmd_direct = on_message(rule=create_image_rule(cmd_type), priority=10, block=True)
            cmd_direct.handle()(create_handler(cmd_type))
            
            print(f"[XiSoul] 已注册随机图片命令: {cmd_type} 和 /{cmd_type}")
            logger.info(f"[XiSoul] 已注册随机图片命令: {cmd_type} 和 /{cmd_type}")

# 注册新闻图片命令
async def handle_news_command(bot: Bot, event: Event):
    """处理新闻图片命令"""
    user_id = event.get_user_id()
    print(f"[XiSoul] 新闻图片命令被触发! 用户: {user_id}")
    logger.info(f"[XiSoul] 新闻图片命令被触发! 用户: {user_id}")
    
    try:
        # 获取新闻图片
        image_data = await get_news_image()
        if image_data:
            from nonebot.adapters.onebot.v11 import MessageSegment
            await bot.send(event, MessageSegment.image(image_data))
        else:
            await bot.send(event, "获取新闻图片失败，请稍后再试")
    except Exception as e:
        logger.error(f"处理新闻图片命令时出错: {str(e)}")
        await bot.send(event, f"处理新闻图片时出错: {str(e)}")

# 注册新闻图片命令
news_cmd = on_command("新闻图片", priority=10, block=True)
news_cmd_prefix = on_command("/新闻图片", priority=10, block=True)

@news_cmd.handle()
@news_cmd_prefix.handle()
async def handle_news(bot: Bot, event: Event):
    """处理新闻图片命令"""
    await handle_news_command(bot, event)
    
# 添加直接消息规则的新闻图片命令
async def is_news_command(event: Event) -> bool:
    """检测消息是否为新闻图片命令"""
    message = str(event.message).strip()
    return message == "新闻图片"

news_cmd_direct = on_message(rule=is_news_command, priority=10, block=True)

@news_cmd_direct.handle()
async def handle_news_direct(bot: Bot, event: Event):
    """处理直接发送的新闻图片命令"""
    await handle_news_command(bot, event)

# AI 聊天功能（OpenAI 兼容）已迁入 .ai_chat 子模块
from . import ai_chat  # noqa: F401

# 导入 playwright_helper 的清理函数
from .playwright_helper import cleanup as playwright_cleanup

# 注册生图命令 - 使用 on_message 来捕获所有生图相关消息
async def is_image_gen_command(event: Event) -> bool:
    """检测消息是否为生图命令"""
    message = str(event.message).strip()
    return parse_image_gen_command(message) is not None

image_gen_cmd = on_message(rule=is_image_gen_command, priority=10, block=True)

@image_gen_cmd.handle()
async def handle_image_gen(bot: Bot, event: Event):
    """处理生图命令"""
    message = str(event.message).strip()
    prompt = parse_image_gen_command(message)
    if prompt:
        await handle_image_gen_request(bot, event, prompt)

# 插件启动事件
@_driver.on_startup
async def plugin_startup():
    print("[XiSoul] 插件启动中...")
    logger.info("[XiSoul] 插件启动中...")
    
    # 打印配置信息
    command_start = getattr(_driver.config, "command_start", [])
    print(f"[XiSoul] 命令前缀配置: {command_start}")
    logger.info(f"[XiSoul] 命令前缀配置: {command_start}")
    
    # 注册其他图片命令
    register_other_image_commands()
    
    print("[XiSoul] 插件启动完成!")
    logger.info("[XiSoul] 插件启动完成!")

# 插件关闭事件
@_driver.on_shutdown
async def plugin_shutdown():
    print("[XiSoul] 插件正在关闭...")
    logger.info("[XiSoul] 插件正在关闭...")
    
    # 清理 Playwright 资源
    await playwright_cleanup()
    
    print("[XiSoul] 插件已关闭")
    logger.info("[XiSoul] 插件已关闭")

print("[XiSoul] 插件加载完成，所有命令已注册")
logger.info("[XiSoul] 插件加载完成，所有命令已注册")
