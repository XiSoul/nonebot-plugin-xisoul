"""XiSoul 插件包"""

from . import lunar_text
from . import lunar_image
from . import lunar_news  # 导入新闻功能模块
from nonebot import on_command, get_driver, logger
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