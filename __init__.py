"""
XiSoul 插件

提供农历黄历信息和实时新闻图片功能，以及Ollama对话功能
"""

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
from .random_images import handle_image_request, IMAGE_TYPES

# 注册帮助命令
help_cmd = on_command("帮助", priority=1, block=True)
help_cmd_prefix = on_command("/帮助", priority=1, block=True)
help_cmd_xi = on_command("xihelp", priority=1, block=True)
help_cmd_plugin = on_command("插件帮助", priority=1, block=True)

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
    
    help_message = [
        "📚 XiSoul 插件帮助信息",
        "",
        "🔄 命令格式说明：",
        "• 所有命令支持直接发送或带/前缀发送",
        "• 部分功能支持AI前缀触发",
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
        "",
        "🤖 4. AI聊天功能",
        "• ai + 问题内容 - 智能问答",
        "• 切换千问/切换gpt/切换deepseek - 切换AI模型",
        "• 当前模型 - 查看当前使用的模型",
        "• 清理历史 - 清理对话历史",
        "• 重置模型 - 重置到默认模型",
        "• ollama帮助 - 查看AI功能详细帮助",
        "",
        "💡 提示：输入 'ollama帮助' 可查看AI聊天功能的详细说明"
    ]
    
    await bot.send(event, "\n".join(help_message))

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
    return message == "sjbs"

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
                    return message == image_type
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

# 尝试导入并注册Ollama命令
try:
    from .ollama_chat import handle_ollama_chat, is_ai_prefix, handle_show_current_model, \
                           handle_switch_qwen, handle_switch_gpt, handle_switch_deepseek, \
                           handle_reset_model, handle_ollama_help, handle_clear_history

    # Ollama命令处理
    ollama_cmd = on_command("ollama", priority=10, block=True)
    ollama_cmd_prefix = on_command("/ollama", priority=10, block=True)

    @ollama_cmd.handle()
    @ollama_cmd_prefix.handle()
    async def handle_ollama(bot: Bot, event: Event):
        """处理Ollama对话命令"""
        await handle_ollama_chat(bot, event)
    
    # 添加当前模型命令
    current_model_cmd = on_command("当前模型", priority=10, block=True)
    current_model_cmd_prefix = on_command("/当前模型", priority=10, block=True)
    
    @current_model_cmd.handle()
    @current_model_cmd_prefix.handle()
    async def handle_current_model(bot: Bot, event: Event):
        """处理当前模型命令"""
        await handle_show_current_model(bot, event)
    
    # 添加当前模型直接消息规则支持
    async def is_current_model_command(event: Event) -> bool:
        """检测消息是否为当前模型命令"""
        message = str(event.message).strip()
        return message == "当前模型"
    
    # 注册基于消息内容的监听器
    current_model_listener = on_message(rule=is_current_model_command, priority=10, block=True)
    
    @current_model_listener.handle()
    async def handle_current_model_direct(bot: Bot, event: Event):
        """处理直接发送的当前模型命令"""
        await handle_show_current_model(bot, event)
    
    # 添加切换模型命令 - 千问
    switch_qwen_cmd = on_command("切换千问", priority=10, block=True)
    switch_qwen_cmd_prefix = on_command("/切换千问", priority=10, block=True)
    
    @switch_qwen_cmd.handle()
    @switch_qwen_cmd_prefix.handle()
    async def handle_switch_to_qwen(bot: Bot, event: Event):
        """处理切换到千问模型命令"""
        await handle_switch_qwen(bot, event)
    
    # 添加切换千问直接消息规则支持
    async def is_switch_qwen_command(event: Event) -> bool:
        """检测消息是否为切换千问命令"""
        message = str(event.message).strip()
        return message == "切换千问"
    
    switch_qwen_listener = on_message(rule=is_switch_qwen_command, priority=10, block=True)
    
    @switch_qwen_listener.handle()
    async def handle_switch_qwen_direct(bot: Bot, event: Event):
        """处理直接发送的切换千问命令"""
        await handle_switch_qwen(bot, event)
    
    # 添加切换模型命令 - GPT
    switch_gpt_cmd = on_command("切换gpt", priority=10, block=True)
    switch_gpt_cmd_prefix = on_command("/切换gpt", priority=10, block=True)
    
    @switch_gpt_cmd.handle()
    @switch_gpt_cmd_prefix.handle()
    async def handle_switch_to_gpt(bot: Bot, event: Event):
        """处理切换到GPT模型命令"""
        await handle_switch_gpt(bot, event)
    
    # 添加切换gpt直接消息规则支持
    async def is_switch_gpt_command(event: Event) -> bool:
        """检测消息是否为切换gpt命令"""
        message = str(event.message).strip()
        return message == "切换gpt"
    
    switch_gpt_listener = on_message(rule=is_switch_gpt_command, priority=10, block=True)
    
    @switch_gpt_listener.handle()
    async def handle_switch_gpt_direct(bot: Bot, event: Event):
        """处理直接发送的切换gpt命令"""
        await handle_switch_gpt(bot, event)
    
    # 添加切换模型命令 - DeepSeek
    switch_deepseek_cmd = on_command("切换deepseek", priority=10, block=True)
    switch_deepseek_cmd_prefix = on_command("/切换deepseek", priority=10, block=True)
    
    @switch_deepseek_cmd.handle()
    @switch_deepseek_cmd_prefix.handle()
    async def handle_switch_to_deepseek(bot: Bot, event: Event):
        """处理切换到DeepSeek模型命令"""
        await handle_switch_deepseek(bot, event)
    
    # 添加切换deepseek直接消息规则支持
    async def is_switch_deepseek_command(event: Event) -> bool:
        """检测消息是否为切换deepseek命令"""
        message = str(event.message).strip()
        return message == "切换deepseek"
    
    switch_deepseek_listener = on_message(rule=is_switch_deepseek_command, priority=10, block=True)
    
    @switch_deepseek_listener.handle()
    async def handle_switch_deepseek_direct(bot: Bot, event: Event):
        """处理直接发送的切换deepseek命令"""
        await handle_switch_deepseek(bot, event)
    
    # 添加重置模型命令
    reset_model_cmd = on_command("重置模型", priority=10, block=True)
    reset_model_cmd_prefix = on_command("/重置模型", priority=10, block=True)
    
    @reset_model_cmd.handle()
    @reset_model_cmd_prefix.handle()
    async def handle_reset_current_model(bot: Bot, event: Event):
        """处理重置模型命令"""
        await handle_reset_model(bot, event)
    
    # 添加重置模型直接消息规则支持
    async def is_reset_model_command(event: Event) -> bool:
        """检测消息是否为重置模型命令"""
        message = str(event.message).strip()
        return message == "重置模型"
    
    reset_model_listener = on_message(rule=is_reset_model_command, priority=10, block=True)
    
    @reset_model_listener.handle()
    async def handle_reset_model_direct(bot: Bot, event: Event):
        """处理直接发送的重置模型命令"""
        await handle_reset_model(bot, event)
    
    # 添加清理历史命令
    clear_history_cmd = on_command("清理历史", priority=10, block=True)
    clear_history_cmd_prefix = on_command("/清理历史", priority=10, block=True)
    
    @clear_history_cmd.handle()
    @clear_history_cmd_prefix.handle()
    async def handle_clear_chat_history(bot: Bot, event: Event):
        """处理清理对话历史命令"""
        await handle_clear_history(bot, event)
    
    # 添加清理历史直接消息规则支持
    async def is_clear_history_command(event: Event) -> bool:
        """检测消息是否为清理历史命令"""
        message = str(event.message).strip()
        return message == "清理历史"
    
    clear_history_listener = on_message(rule=is_clear_history_command, priority=10, block=True)
    
    @clear_history_listener.handle()
    async def handle_clear_history_direct(bot: Bot, event: Event):
        """处理直接发送的清理历史命令"""
        await handle_clear_history(bot, event)
    
    # 添加Ollama帮助命令
    ollama_help_cmd = on_command("ollama帮助", priority=10, block=True)
    ollama_help_cmd_prefix = on_command("/ollama帮助", priority=10, block=True)
    
    @ollama_help_cmd.handle()
    @ollama_help_cmd_prefix.handle()
    async def handle_ollama_help_cmd(bot: Bot, event: Event):
        """处理Ollama帮助命令"""
        await handle_ollama_help(bot, event)
    
    # 添加ollama帮助直接消息规则支持
    async def is_ollama_help_command(event: Event) -> bool:
        """检测消息是否为ollama帮助命令"""
        message = str(event.message).strip()
        return message == "ollama帮助"
    
    ollama_help_listener = on_message(rule=is_ollama_help_command, priority=10, block=True)
    
    @ollama_help_listener.handle()
    async def handle_ollama_help_direct(bot: Bot, event: Event):
        """处理直接发送的ollama帮助命令"""
        await handle_ollama_help(bot, event)
    
    # 添加AI前缀消息监听
    async def is_ai_message(event: Event) -> bool:
        """检测消息是否以"ai "开头"""
        message = str(event.message).strip()
        return is_ai_prefix(message)
    
    # 注册基于消息内容的监听器
    ai_chat_listener = on_message(rule=is_ai_message, priority=10, block=True)
    
    @ai_chat_listener.handle()
    async def handle_ai_message(bot: Bot, event: Event):
        """处理以"ai "开头的消息"""
        await handle_ollama_chat(bot, event)

    print("[XiSoul] 已注册所有Ollama相关命令和AI前缀消息监听")
    logger.info("[XiSoul] 已注册所有Ollama相关命令和AI前缀消息监听")
except ImportError:
    print("[XiSoul] Ollama功能未启用（缺少依赖）")
    logger.warning("[XiSoul] Ollama功能未启用（缺少依赖）")

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
    print("[XiSoul] 插件已关闭")
    logger.info("[XiSoul] 插件已关闭")

print("[XiSoul] 插件加载完成，所有命令已注册")
logger.info("[XiSoul] 插件加载完成，所有命令已注册")