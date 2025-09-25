"""Ollama云模型聊天插件"""

import json
import asyncio
from datetime import datetime
from nonebot import on_command, on_message, get_driver, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

# 导入Ollama的Python客户端库 - 这是官方推荐的调用方式
try:
    from ollama import Client
except ImportError:
    logger.error("未安装ollama Python库，请运行: pip install ollama")
    # 为了防止导入失败导致整个插件无法加载，创建一个模拟的Client类
    class Client:
        def __init__(self, host=None, headers=None):
            self.host = host
            self.headers = headers
        def chat(self, model, messages, stream=False):
            raise ImportError("未安装ollama Python库")

__plugin_meta__ = PluginMetadata(
    name="Ollama云模型聊天",
    description="使用Ollama云模型进行聊天，支持切换不同模型",
    usage="@机器人 发送消息进行聊天\n/切换千问 切换到qwen3-coder:480b-cloud模型\n/切换gpt 切换到gpt-oss:120b-cloud模型\n/切换deepseek 切换到deepseek-v3.1:671b-cloud模型\n/当前模型 查看当前使用的模型",
)

# 从环境变量获取配置
config = get_driver().config
ollama_api_key = getattr(config, "ollama_api_key", "")

# 默认模型 - 根据官方文档，云端模型需要带-cloud后缀
DEFAULT_MODEL = "qwen3-coder:480b-cloud"
# 当前使用的模型
current_model = DEFAULT_MODEL
# 对话历史缓存
conversation_histories = {}
# Ollama API主机地址
OLLAMA_HOST = "https://ollama.com"

# 在文件顶部的命令定义部分添加新命令
# 命令定义
switch_qwen = on_command("切换千问", priority=10, block=True)
switch_gpt = on_command("切换gpt", priority=10, block=True)
switch_deepseek = on_command("切换deepseek", priority=10, block=True)
show_current_model = on_command("当前模型", priority=10, block=True)
model_list = on_command("模型列表", priority=10, block=True)
ollama_help = on_command("ollama帮助", aliases={"Ollama帮助", "ollama菜单", "Ollama菜单"}, priority=10, block=True)

# 聊天消息处理
ollama_chat = on_message(rule=to_me(), priority=15, block=False)

# 可用模型列表
available_models = [
    {"name": "qwen3-coder:480b-cloud", "chinese_name": "千问", "description": "高性能中文编码模型"},
    {"name": "gpt-oss:120b-cloud", "chinese_name": "GPT", "description": "通用语言模型"},
    {"name": "deepseek-v3.1:671b-cloud", "chinese_name": "DeepSeek", "description": "专业编程模型"}
]

# 添加模型列表命令处理函数
@model_list.handle()
async def handle_model_list(bot: Bot, event: Event):
    """显示可用的模型列表"""
    response = "📋 **可用模型列表**\n\n"
    for i, model in enumerate(available_models, 1):
        is_current = " ✅" if model["name"] == current_model else ""
        response += f"{i}. {model['chinese_name']} ({model['name']}){is_current}\n"
        response += f"   简介: {model['description']}\n\n"
    await bot.send(event, response)

# 添加插件帮助菜单命令处理函数
@ollama_help.handle()
async def handle_ollama_help(bot: Bot, event: Event):
    """显示Ollama聊天插件的帮助菜单"""
    response = "🤖 **Ollama聊天插件帮助菜单**\n\n"
    response += "📝 **聊天功能**\n"
    response += "@机器人 + 消息内容\n\n"
    
    response += "🔄 **模型管理**\n"
    response += "/切换千问 - 切换到千问模型\n"
    response += "/切换gpt - 切换到GPT模型\n"
    response += "/切换deepseek - 切换到DeepSeek模型\n"
    response += "/当前模型 - 查看当前使用的模型\n"
    response += "/模型列表 - 查看所有可用模型\n"
    response += "/重置模型 - 重置到默认模型\n\n"
    
    response += "🧹 **对话管理**\n"
    response += "/清理对话 - 清理您的对话历史\n"
    response += "/清理对话 全部 - 超级用户清理所有对话历史\n\n"
    
    response += "ℹ️ **帮助信息**\n"
    response += "/ollama帮助 - 显示此帮助菜单\n"
    
    await bot.send(event, response)

@switch_qwen.handle()
async def handle_switch_qwen(bot: Bot, event: Event):
    """切换到千问模型"""
    global current_model
    current_model = "qwen3-coder:480b-cloud"
    logger.info(f"模型已切换为: {current_model}")
    await bot.send(event, f"✅ 模型已切换为: 千问 (qwen3-coder:480b-cloud)")

@switch_gpt.handle()
async def handle_switch_gpt(bot: Bot, event: Event):
    """切换到GPT模型"""
    global current_model
    current_model = "gpt-oss:120b-cloud"
    logger.info(f"模型已切换为: {current_model}")
    await bot.send(event, f"✅ 模型已切换为: GPT (gpt-oss:120b-cloud)")

@switch_deepseek.handle()
async def handle_switch_deepseek(bot: Bot, event: Event):
    """切换到DeepSeek模型"""
    global current_model
    current_model = "deepseek-v3.1:671b-cloud"
    logger.info(f"模型已切换为: {current_model}")
    await bot.send(event, f"✅ 模型已切换为: DeepSeek (deepseek-v3.1:671b-cloud)")

@show_current_model.handle()
async def handle_show_current_model(bot: Bot, event: Event):
    """显示当前使用的模型"""
    model_name = {
        "qwen3-coder:480b-cloud": "千问",
        "gpt-oss:120b-cloud": "GPT",
        "deepseek-v3.1:671b-cloud": "DeepSeek"
    }.get(current_model, current_model)
    await bot.send(event, f"当前使用的模型: {model_name} ({current_model})")

@ollama_chat.handle()
async def handle_ollama_chat(bot: Bot, event: Event):
    """处理聊天消息"""
    # 获取用户发送的消息，去除@机器人的部分
    message = str(event.message)
    # 如果消息为空或仅包含命令，不处理
    if not message or message.strip() in ["清理", "重置"]:
        return
    
    # 获取用户ID
    user_id = event.get_user_id()
    
    # 初始化用户的对话历史
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
        logger.info(f"初始化用户 {user_id} 的对话历史")
    
    try:
        logger.info(f"收到用户 {user_id} 的消息: {message}")
        
        # 调用Ollama API获取回复
        response_text = await get_ollama_response(message, user_id)
        
        if response_text:
            logger.info(f"获取Ollama回复成功，用户 {user_id}")
            # 如果回复内容过长，分段发送
            if len(response_text) > 2000:
                chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                for chunk in chunks:
                    await bot.send(event, chunk)
                    await asyncio.sleep(1)  # 避免消息发送过快
            else:
                await bot.send(event, response_text)
        else:
            await bot.send(event, "❌ 获取Ollama回复失败，请稍后再试")
            
    except Exception as e:
        logger.error(f"Ollama聊天处理异常: {type(e).__name__}: {str(e)}")
        await bot.send(event, f"❌ 聊天处理异常: {type(e).__name__}: {str(e)}")

async def get_ollama_response(message: str, user_id: str) -> str:
    """调用Ollama API获取回复 - 使用官方Python客户端库"""
    global current_model
    
    # 更新对话历史
    conversation_histories[user_id].append({"role": "user", "content": message})
    
    logger.info(f"调用Ollama API: 模型={current_model}, 用户ID={user_id}")
    logger.info(f"Ollama主机地址: {OLLAMA_HOST}")
    logger.info(f"消息内容: {message}")
    
    try:
        # 使用Ollama官方Python客户端库
        client = Client(
            host=OLLAMA_HOST,
            headers={'Authorization': f'Bearer {ollama_api_key}'}
        )
        
        # 同步函数需要在异步环境中运行，使用loop.run_in_executor
        loop = asyncio.get_event_loop()
        
        # 修复：只传递模拟Client类支持的三个参数
        response = await loop.run_in_executor(
            None, 
            lambda: client.chat(
                model=current_model, 
                messages=conversation_histories[user_id],
                stream=False
            )
        )
        
        logger.info(f"API响应成功: {response}")
        
        if "message" in response:
            response_text = response["message"]["content"]
            # 将助手回复添加到对话历史
            conversation_histories[user_id].append({"role": "assistant", "content": response_text})
            return response_text
        else:
            logger.error(f"Ollama API返回无效响应: {response}")
            return ""
    
    except ImportError as e:
        logger.error(f"未安装ollama Python库: {str(e)}")
        return "❌ 请先安装ollama Python库: pip install ollama"
    except Exception as e:
        logger.error(f"Ollama API调用异常: {type(e).__name__}: {str(e)}")
        # 尝试识别常见错误
        if "No API key provided" in str(e) or "Unauthorized" in str(e):
            return "❌ API密钥错误或未配置，请检查OLLAMA_API_KEY环境变量"
        elif "Connection refused" in str(e) or "Cannot connect" in str(e):
            return "❌ 无法连接到Ollama服务器，请检查网络连接"
        elif "Model not found" in str(e):
            return "❌ 模型未找到，请确认模型名称是否正确"
        else:
            return f"❌ API调用错误: {str(e)}"

# 清理对话历史的命令
clear_history = on_command("清理历史", aliases={"重置对话"}, priority=10, block=True)

@clear_history.handle()
async def handle_clear_history(bot: Bot, event: Event):
    """清理指定用户的对话历史"""
    # 获取用户ID
    user_id = event.get_user_id()
    
    # 检查是否为超级用户
    if user_id in config.superusers:
        # 获取命令参数，尝试解析要清理的用户ID
        args = str(event.message).strip()
        if args:
            # 尝试将参数解析为用户ID
            target_user_id = args
        else:
            # 没有参数，清理所有用户的对话历史
            conversation_histories.clear()
            logger.info(f"超级用户 {user_id} 清理了所有用户的对话历史")
            await bot.send(event, "✅ 已清理所有用户的对话历史")
            return
    else:
        # 普通用户只能清理自己的对话历史
        target_user_id = user_id
    
    # 清理指定用户的对话历史
    if target_user_id in conversation_histories:
        del conversation_histories[target_user_id]
        logger.info(f"用户 {user_id} 清理了用户 {target_user_id} 的对话历史")
        if user_id == target_user_id:
            await bot.send(event, "✅ 已清理您的对话历史")
        else:
            await bot.send(event, f"✅ 已清理用户 {target_user_id} 的对话历史")
    else:
        if user_id == target_user_id:
            await bot.send(event, "❌ 您没有对话历史可以清理")
        else:
            await bot.send(event, f"❌ 用户 {target_user_id} 没有对话历史可以清理")

# 重置模型到默认值的命令
reset_model = on_command("重置模型", priority=10, block=True)

@reset_model.handle()
async def handle_reset_model(bot: Bot, event: Event):
    """重置模型到默认值"""
    global current_model
    current_model = DEFAULT_MODEL
    logger.info(f"模型已重置为默认值: {current_model}")
    await bot.send(event, f"✅ 模型已重置为默认值: 千问 (qwen3-coder:480b-cloud)")