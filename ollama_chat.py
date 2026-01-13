"""Ollama云模型聊天核心功能 - 仅提供功能函数，命令已移至__init__.py"""

import json
import asyncio
from nonebot import get_driver, logger

# 导入Ollama的Python客户端库
try:
    from ollama import Client
except ImportError:
    logger.error("未安装ollama Python库，请运行: pip install ollama")
    # 创建一个模拟的Client类
    class Client:
        def __init__(self, host=None, headers=None):
            self.host = host
            self.headers = headers
        def chat(self, model, messages, stream=False):
            raise ImportError("未安装ollama Python库")

# 导入必要的NoneBot类型
try:
    from nonebot.adapters.onebot.v11 import Bot, Event
except ImportError:
    logger.warning("未导入Bot和Event类型，将使用动态类型")
    Bot = None
    Event = None

# 从环境变量获取配置
config = get_driver().config
ollama_api_key = getattr(config, "ollama_api_key", "")

# Ollama API主机地址
OLLAMA_HOST = "https://ollama.com"

# 初始化必要的全局变量
conversation_histories = {}
DEFAULT_MODEL = "qwen3-coder:480b-cloud"
current_model = DEFAULT_MODEL

# 可用模型列表
available_models = [
    {"name": "qwen3-coder:480b-cloud", "chinese_name": "千问", "description": "高性能中文编码模型"},
    {"name": "gpt-oss:120b-cloud", "chinese_name": "GPT", "description": "通用语言模型"},
    {"name": "deepseek-v3.1:671b-cloud", "chinese_name": "DeepSeek", "description": "专业编程模型"}
]

def is_ai_prefix(message: str) -> bool:
    """检查消息是否以"ai+空格"开头"""
    return message.strip().lower().startswith("ai ")

# 这个函数已被下面的新版本替代，保留注释

logger.info("[Ollama] 核心功能加载完成，命令已移至__init__.py")

# 注意：命令处理函数已移至__init__.py
# 以下为功能函数，供__init__.py中的命令处理器调用
async def handle_model_list(bot, event):
    """显示可用的模型列表"""
    response = "📋 **可用模型列表**\n\n"
    for i, model in enumerate(available_models, 1):
        is_current = " ✅" if model["name"] == current_model else ""
        response += f"{i}. {model['chinese_name']} ({model['name']}){is_current}\n"
        response += f"   简介: {model['description']}\n\n"
    await bot.send(event, response)

async def handle_ollama_help(bot, event):
    """显示Ollama聊天插件的帮助菜单"""
    response = [
        "🤖 **AI聊天功能详细帮助**",
        "",
        "📝 **基础聊天**",
        "• ai + 问题内容 - 智能问答（自动识别，不需要@机器人）",
        "• 示例：ai 你好，今天天气怎么样？",
        "",
        "🔄 **模型管理**",
        "• 切换千问 - 切换到千问模型（高性能中文编码模型）",
        "• 切换gpt - 切换到GPT模型（通用语言模型）",
        "• 切换deepseek - 切换到DeepSeek模型（专业编程模型）",
        "• 当前模型 - 查看当前使用的模型",
        "• 模型列表 - 查看所有可用模型",
        "• 重置模型 - 重置到默认模型（千问）",
        "",
        "🧹 **对话管理**",
        "• 清理历史 - 清理您的对话历史（重置当前会话）",
        "",
        "💡 **使用提示**",
        "• 所有命令支持直接发送或带/前缀发送",
        "• 例如：'切换千问' 或 '/切换千问' 均可触发",
        "• 模型切换后会自动应用于后续的所有对话",
        "",
        "🔧 **故障排除**",
        "• 如果无法获取回复，请检查网络连接",
        "• 输入错误或不支持的命令将不会触发响应"
    ]
    
    await bot.send(event, "\n".join(response))

async def handle_switch_qwen(bot, event):
    """切换到千问模型"""
    global current_model
    current_model = "qwen3-coder:480b-cloud"
    logger.info(f"模型已切换为: {current_model}")
    await bot.send(event, f"✅ 模型已切换为: 千问 (qwen3-coder:480b-cloud)")

async def handle_switch_gpt(bot, event):
    """切换到GPT模型"""
    global current_model
    current_model = "gpt-oss:120b-cloud"
    logger.info(f"模型已切换为: {current_model}")
    await bot.send(event, f"✅ 模型已切换为: GPT (gpt-oss:120b-cloud)")

async def handle_switch_deepseek(bot, event):
    """切换到DeepSeek模型"""
    global current_model
    current_model = "deepseek-v3.1:671b-cloud"
    logger.info(f"模型已切换为: {current_model}")
    await bot.send(event, f"✅ 模型已切换为: DeepSeek (deepseek-v3.1:671b-cloud)")

async def handle_show_current_model(bot, event):
    """显示当前使用的模型"""
    model_name = {
        "qwen3-coder:480b-cloud": "千问",
        "gpt-oss:120b-cloud": "GPT",
        "deepseek-v3.1:671b-cloud": "DeepSeek"
    }.get(current_model, current_model)
    await bot.send(event, f"当前使用的模型: {model_name} ({current_model})")

async def handle_ollama_chat(bot, event):
    """处理聊天消息"""
    # 获取用户发送的消息
    message = str(event.message)
    message_text = message.strip()
    
    # 定义所有需要排除的命令关键词列表
    COMMAND_KEYWORDS = [
        "sjbs", "sjhs", "sjmt", "sjecy", "sjsk",  # 随机图片命令
        "切换千问", "切换gpt", "切换deepseek",    # 模型切换命令
        "当前模型", "模型列表", "ollama帮助",      # 模型信息命令
        "清理历史", "重置模型",                    # 对话管理命令
        "帮助", "测试黄历"                          # 其他命令
    ]
    
    # 检查消息是否为任何已注册的命令，如果是则不处理，让命令处理器处理
    if message_text in COMMAND_KEYWORDS:
        logger.info(f"消息'{message_text}'被识别为命令，跳过处理，交给命令处理器")
        return
    
    # 检查消息是否以"ai+空格"开头
    if not is_ai_prefix(message_text):
        logger.info(f"消息'{message_text}'不以'ai '开头，跳过处理")
        return
    
    # 提取实际问题（移除"ai "前缀，注意包含空格）
    question = message_text[3:].strip()
    # 如果移除前缀后消息为空，不处理
    if not question:
        return
    
    logger.info(f"收到AI问题: {question}")
    
    # 获取用户ID
    user_id = event.get_user_id()
    
    # 初始化用户的对话历史
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
        logger.info(f"初始化用户 {user_id} 的对话历史")
    
    try:
        logger.info(f"收到用户 {user_id} 的AI问题: {question}")
        
        # 调用Ollama API获取回复
        response_text = await get_ollama_response(question, user_id)
        
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

# 清理对话历史命令已在上方定义

async def handle_clear_history(bot, event):
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

# 重置模型命令已在上方定义

async def handle_reset_model(bot, event):
    """重置模型到默认值"""
    global current_model
    current_model = DEFAULT_MODEL
    logger.info(f"模型已重置为默认值: {current_model}")
    await bot.send(event, f"✅ 模型已重置为默认值: 千问 (qwen3-coder:480b-cloud)")