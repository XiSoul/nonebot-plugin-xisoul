import httpx
import json
import os
import asyncio
import time
from nonebot import on_command, get_driver, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from datetime import datetime

__plugin_meta__ = PluginMetadata(
    name="XiSoul 新闻图片",
    description="获取实时热榜新闻图片",
    usage="/新闻图片 获取今日热榜新闻图片",
    type="application",
    homepage="https://github.com/xisoul/nonebot-plugin-xisoul",  # 更新为连字符版本
)

# 修复：修正配置获取语句，移除错误的反斜杠
# 从环境变量获取配置
driver = get_driver()
config = driver.config

# 按照网站名称(shwgij)命名的环境变量 - 新闻API配置
SHWGIJ_API_KEY = getattr(config, "shwgij_api_key", "")

# 其他新闻API参数也按照网站名称前缀命名
SHWGIJ_WIDTH = getattr(config, "shwgij_width", 800)
SHWGIJ_TOP_MARGIN = getattr(config, "shwgij_top_margin", 100)
SHWGIJ_BOTTOM_MARGIN = getattr(config, "shwgij_bottom_margin", 50)
SHWGIJ_SIDE_MARGIN = getattr(config, "shwgij_side_margin", 50)
SHWGIJ_SHOW_TITLE = getattr(config, "shwgij_show_title", 1)
SHWGIJ_TITLE_FONT_SIZE = getattr(config, "shwgij_title_font_size", 30)
SHWGIJ_TITLE_TEXT_COLOR = getattr(config, "shwgij_title_text_color", "000000")
SHWGIJ_TITLE_FONT_INDEX = getattr(config, "shwgij_title_font_index", 5)
SHWGIJ_TITLE_BOTTOM_SPACING = getattr(config, "shwgij_title_bottom_spacing", 10)
SHWGIJ_SHOW_CALENDAR = getattr(config, "shwgij_show_calendar", 1)
SHWGIJ_CALENDAR_BOTTOM_SPACING = getattr(config, "shwgij_calendar_bottom_spacing", 30)
SHWGIJ_SHOW_LUNAR_DATE = getattr(config, "shwgij_show_lunar_date", 0)
SHWGIJ_LUNAR_DATE_FONT_SIZE = getattr(config, "shwgij_lunar_date_font_size", 20)
SHWGIJ_LUNAR_DATE_TEXT_COLOR = getattr(config, "shwgij_lunar_date_text_color", "000000")
SHWGIJ_LUNAR_DATE_FONT_INDEX = getattr(config, "shwgij_lunar_date_font_index", 3)
SHWGIJ_LUNAR_DATE_BOTTOM_SPACING = getattr(config, "shwgij_lunar_date_bottom_spacing", 30)
# 修正news_count参数，设置为合理值
SHWGIJ_NEWS_COUNT = getattr(config, "shwgij_news_count", 20)
SHWGIJ_NEWS_ITEM_SPACING = getattr(config, "shwgij_news_item_spacing", 20)
SHWGIJ_NEWS_LINE_SPACING = getattr(config, "shwgij_news_line_spacing", 3)
SHWGIJ_NEWS_BOTTOM_SPACING = getattr(config, "shwgij_news_bottom_spacing", 20)
SHWGIJ_FONT_INDEX = getattr(config, "shwgij_font_index", 3)
SHWGIJ_IS_NUMBERED = getattr(config, "shwgij_is_numbered", 1)
SHWGIJ_FIRST_NEWS_NUMBERED = getattr(config, "shwgij_first_news_numbered", 1)
SHWGIJ_START_NUMBERING_FROM = getattr(config, "shwgij_start_numbering_from", 1)
SHWGIJ_NUMBERING_STYLE = getattr(config, "shwgij_numbering_style", 1)
SHWGIJ_SHOW_WEIYU = getattr(config, "shwgij_show_weiyu", 0)
SHWGIJ_WEIYU_FONT_SIZE = getattr(config, "shwgij_weiyu_font_size", 20)
SHWGIJ_WEIYU_TEXT_COLOR = getattr(config, "shwgij_weiyu_text_color", "000000")
SHWGIJ_WEIYU_FONT_INDEX = getattr(config, "shwgij_weiyu_font_index", 3)
SHWGIJ_WEIYU_BOTTOM_SPACING = getattr(config, "shwgij_weiyu_bottom_spacing", 0)
SHWGIJ_SHOW_SMALL_TEXT = getattr(config, "shwgij_show_small_text", 1)
SHWGIJ_SMALL_TEXT_FONT_SIZE = getattr(config, "shwgij_small_text_font_size", 15)
SHWGIJ_SMALL_TEXT_TEXT_COLOR = getattr(config, "shwgij_small_text_text_color", "808080")
SHWGIJ_SMALL_TEXT_FONT_INDEX = getattr(config, "shwgij_small_text_font_index", 2)
SHWGIJ_IMAGE_QUALITY = getattr(config, "shwgij_image_quality", 6)

# 定时任务配置
SHWGIJ_CRON_EXPRESSION = getattr(config, "shwgij_cron_expression", "0 8 * * *")
SHWGIJ_SEND_GROUPS = getattr(config, "shwgij_send_groups", "")
SHWGIJ_CRON_ENABLE = getattr(config, "shwgij_cron_enable", 1)

# 新增：日志级别控制配置
SHWGIJ_LOG_LEVEL = getattr(config, "shwgij_log_level", "INFO")  # 可选：DEBUG, INFO, WARNING, ERROR
# 新增：自定义图片删除延时配置(秒)
SHWGIJ_IMAGE_DELETE_DELAY = getattr(config, "shwgij_image_delete_delay", 120)
# 新增：缓存文件保留天数配置
SHWGIJ_CACHE_EXPIRE_DAYS = getattr(config, "shwgij_cache_expire_days", 7)

# 缓存上次发送时间，避免频繁调用API
last_send_time = None
# 缓存新闻图片，避免频繁调用API
cached_image_data = None
cached_image_date = None
# 缓存文件路径
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "news_image_cache.jpg")
# 临时文件路径（用于多群发送）
TEMP_IMAGE_FILE = os.path.join(CACHE_DIR, "temp_news_image.jpg")
# 图片删除延时（秒） - 使用配置值
IMAGE_DELETE_DELAY = SHWGIJ_IMAGE_DELETE_DELAY

# 新增：根据日志级别配置logger
class LogLevelController:
    """日志级别控制器"""
    def __init__(self, level):
        self.level = level.upper()
        # 定义日志级别优先级
        self.level_priority = {
            "DEBUG": 0,
            "INFO": 1,
            "WARNING": 2,
            "ERROR": 3
        }
        # 确保日志级别有效
        if self.level not in self.level_priority:
            self.level = "INFO"
        
    def should_log(self, log_level):
        """检查指定级别是否应该记录"""
        log_level = log_level.upper()
        if log_level not in self.level_priority:
            return False
        return self.level_priority[log_level] >= self.level_priority[self.level]

# 创建日志控制器实例
log_controller = LogLevelController(SHWGIJ_LOG_LEVEL)

# 新增：扩展logger，添加日志级别控制
def log_debug(message):
    if log_controller.should_log("DEBUG"):
        logger.debug(message)

# 保持原有日志函数但添加更详细的信息
original_info = logger.info

def enhanced_log_info(message):
    # 添加更多上下文信息，如模块名、时间等
    context = "[LunarNews]"
    original_info(f"{context} {message}")

# 替换原有的logger.info
logger.info = enhanced_log_info

# 获取新闻图片的核心函数
async def get_news_image():
    """获取新闻图片"""
    global cached_image_data, cached_image_date
    current_date = datetime.now().date()
    
    # 检查是否有当天缓存的图片
    if cached_image_data and cached_image_date == current_date:
        log_debug("使用内存缓存的新闻图片")
        return cached_image_data
    
    # 检查是否有本地缓存文件
    if os.path.exists(CACHE_FILE):
        try:
            # 获取文件的修改日期
            file_modify_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).date()
            if file_modify_time == current_date:
                # 如果是今天的缓存，读取文件
                with open(CACHE_FILE, "rb") as f:
                    cached_image_data = f.read()
                    cached_image_date = current_date
                    log_debug("从本地缓存文件加载新闻图片")
                    return cached_image_data
        except Exception as e:
            logger.warning(f"读取本地缓存失败: {str(e)}")
    
    # 获取API密钥
    api_key = SHWGIJ_API_KEY
    
    if not api_key:
        logger.error("新闻图片API密钥未配置")
        return None
    
    # 调用API获取新闻图片
    url = "https://api.shwgij.com/api/today/newspic"
    params = {
        "key": api_key,
        "width": SHWGIJ_WIDTH,
        "top_margin": SHWGIJ_TOP_MARGIN,
        "bottom_margin": SHWGIJ_BOTTOM_MARGIN,
        "side_margin": SHWGIJ_SIDE_MARGIN,
        "show_title": SHWGIJ_SHOW_TITLE,
        "title_font_size": SHWGIJ_TITLE_FONT_SIZE,
        "title_text_color": SHWGIJ_TITLE_TEXT_COLOR,
        "title_font_index": SHWGIJ_TITLE_FONT_INDEX,
        "title_bottom_spacing": SHWGIJ_TITLE_BOTTOM_SPACING,
        "show_calendar": SHWGIJ_SHOW_CALENDAR,
        "calendar_bottom_spacing": SHWGIJ_CALENDAR_BOTTOM_SPACING,
        "show_lunar_date": SHWGIJ_SHOW_LUNAR_DATE,
        "lunar_date_font_size": SHWGIJ_LUNAR_DATE_FONT_SIZE,
        "lunar_date_text_color": SHWGIJ_LUNAR_DATE_TEXT_COLOR,
        "lunar_date_font_index": SHWGIJ_LUNAR_DATE_FONT_INDEX,
        "lunar_date_bottom_spacing": SHWGIJ_LUNAR_DATE_BOTTOM_SPACING,
        "news_count": SHWGIJ_NEWS_COUNT,
        "news_item_spacing": SHWGIJ_NEWS_ITEM_SPACING,
        "news_line_spacing": SHWGIJ_NEWS_LINE_SPACING,
        "news_bottom_spacing": SHWGIJ_NEWS_BOTTOM_SPACING,
        "font_index": SHWGIJ_FONT_INDEX,
        "is_numbered": SHWGIJ_IS_NUMBERED,
        "first_news_numbered": SHWGIJ_FIRST_NEWS_NUMBERED,
        "start_numbering_from": SHWGIJ_START_NUMBERING_FROM,
        "numbering_style": SHWGIJ_NUMBERING_STYLE,
        "show_weiyu": SHWGIJ_SHOW_WEIYU,
        "weiyu_font_size": SHWGIJ_WEIYU_FONT_SIZE,
        "weiyu_text_color": SHWGIJ_WEIYU_TEXT_COLOR,
        "weiyu_font_index": SHWGIJ_WEIYU_FONT_INDEX,
        "weiyu_bottom_spacing": SHWGIJ_WEIYU_BOTTOM_SPACING,
        "show_small_text": SHWGIJ_SHOW_SMALL_TEXT,
        "small_text_font_size": SHWGIJ_SMALL_TEXT_FONT_SIZE,
        "small_text_text_color": SHWGIJ_SMALL_TEXT_TEXT_COLOR,
        "small_text_font_index": SHWGIJ_SMALL_TEXT_FONT_INDEX,
        "image_quality": SHWGIJ_IMAGE_QUALITY
    }
    
    logger.info("正在获取新闻图片...")
    
    try:
        # 执行API请求
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15)  # 增加超时时间
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get('content-type', '')
            
            # 判断响应是JSON还是直接的图片
            if 'image' in content_type:
                # 响应是直接的图片数据
                logger.info("获取新闻图片成功")
                # 缓存图片数据
                cached_image_data = response.content
                cached_image_date = current_date
                # 保存到本地文件
                await save_image_to_cache(cached_image_data)
                return cached_image_data
            elif 'application/json' in content_type:
                # 响应是JSON格式
                try:
                    data = response.json()
                    # 检查响应状态
                    if data.get('code') == 200:
                        if isinstance(data.get('data'), dict):
                            # data是字典，可能包含image字段
                            image_url = data.get('data', {}).get('image', '')
                            if image_url:
                                # 从URL获取图片
                                image_response = await client.get(image_url, timeout=15)
                                image_response.raise_for_status()
                                logger.info("获取新闻图片成功")
                                # 缓存图片数据
                                cached_image_data = image_response.content
                                cached_image_date = current_date
                                # 保存到本地文件
                                await save_image_to_cache(cached_image_data)
                                return cached_image_data
                        else:
                            # data不是字典，可能直接包含图片URL
                            data_content = str(data.get('data', ''))
                            if data_content.startswith('http'):
                                # 从URL获取图片
                                image_response = await client.get(data_content, timeout=15)
                                image_response.raise_for_status()
                                logger.info("获取新闻图片成功")
                                # 缓存图片数据
                                cached_image_data = image_response.content
                                cached_image_date = current_date
                                # 保存到本地文件
                                await save_image_to_cache(cached_image_data)
                                return cached_image_data
                    else:
                        error_msg = data.get('msg', '未知错误')
                        logger.error(f"API返回错误: {error_msg}")
                        # 尝试使用昨天的缓存（如果有）
                        if os.path.exists(CACHE_FILE):
                            try:
                                logger.info("尝试使用缓存的图片")
                                with open(CACHE_FILE, "rb") as f:
                                    return f.read()
                            except Exception as e:
                                logger.warning(f"读取缓存图片失败: {str(e)}")
                except json.JSONDecodeError:
                    logger.warning("JSON解析失败")
            else:
                # 其他类型响应，尝试作为图片处理
                logger.warning(f"未知内容类型: {content_type}")
                # 如果有内容，尝试作为图片返回
                if response.content:
                    # 缓存图片数据
                    cached_image_data = response.content
                    cached_image_date = current_date
                    # 保存到本地文件
                    await save_image_to_cache(cached_image_data)
                    return cached_image_data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP请求错误: {str(e)}")
        # 尝试使用缓存
        if os.path.exists(CACHE_FILE):
            try:
                logger.info("HTTP错误，尝试使用缓存的图片")
                with open(CACHE_FILE, "rb") as f:
                    return f.read()
            except Exception as cache_e:
                logger.warning(f"读取缓存图片失败: {str(cache_e)}")
    except httpx.RequestError as e:
        logger.error(f"网络请求异常: {str(e)}")
        # 尝试使用缓存
        if os.path.exists(CACHE_FILE):
            try:
                logger.info("网络错误，尝试使用缓存的图片")
                with open(CACHE_FILE, "rb") as f:
                    return f.read()
            except Exception as cache_e:
                logger.warning(f"读取缓存图片失败: {str(cache_e)}")
    except Exception as e:
        logger.error(f"获取新闻图片失败: {str(e)}", exc_info=True)
    
    return None

async def save_image_to_cache(image_data):
    """保存图片到本地缓存"""
    try:
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        # 异步写入文件（使用线程池执行阻塞操作）
        await asyncio.to_thread(lambda: open(CACHE_FILE, "wb").write(image_data))
        logger.info(f"新闻图片已保存到本地缓存: {CACHE_FILE}")
    except Exception as e:
        logger.warning(f"保存图片到本地缓存失败: {str(e)}")

async def save_temp_image(image_data):
    """保存临时图片文件用于发送"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        await asyncio.to_thread(lambda: open(TEMP_IMAGE_FILE, "wb").write(image_data))
        logger.info(f"新闻图片已保存到临时文件: {TEMP_IMAGE_FILE}")
        return TEMP_IMAGE_FILE
    except Exception as e:
        logger.warning(f"保存临时图片失败: {str(e)}")
        return None

# 修改：更新schedule_image_deletion函数使用配置的延时
async def schedule_image_deletion(file_path):
    """延时删除图片文件"""
    try:
        logger.info(f"将在{IMAGE_DELETE_DELAY}秒后删除临时图片: {file_path}")
        await asyncio.sleep(IMAGE_DELETE_DELAY)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"已删除临时图片: {file_path}")
    except Exception as e:
        logger.warning(f"删除临时图片失败: {str(e)}")

# 发送新闻图片到指定群聊
async def send_news_image_to_groups():
    """发送新闻图片到配置的群聊"""
    global last_send_time
    
    # 检查是否启用定时任务
    if not SHWGIJ_CRON_ENABLE:
        logger.info("定时任务已禁用")
        return
    
    # 检查是否配置了发送的群聊
    if not SHWGIJ_SEND_GROUPS:
        logger.warning("未配置定时发送的群聊")
        return
    
    # 获取当前日期，避免同一天重复发送
    current_date = datetime.now().date()
    if last_send_time and last_send_time.date() == current_date:
        logger.info("今日已发送过新闻图片，跳过本次发送")
        return
    
    # 获取bot实例
    bots = get_driver().bots
    if not bots:
        logger.error("未找到可用的bot实例")
        return
    
    # 使用第一个可用的bot
    bot = next(iter(bots.values()))
    bot_id = list(bots.keys())[0]
    logger.info(f"使用bot实例: {bot_id}")
    
    # 获取新闻图片
    image_data = await get_news_image()
    if not image_data:
        logger.error("无法获取新闻图片，定时发送失败")
        return
    
    # 保存临时图片文件用于发送
    temp_file_path = await save_temp_image(image_data)
    if not temp_file_path:
        logger.error("保存临时图片失败，使用内存数据发送")
        # 如果保存临时文件失败，使用内存数据发送
        success_count = await send_image_to_groups_with_retry(bot, image_data)
    else:
        # 使用临时文件发送
        success_count = await send_image_to_groups_with_retry(bot, image_data, use_file_path=True)
        # 安排延时删除临时文件
        asyncio.create_task(schedule_image_deletion(temp_file_path))
    
    # 更新上次发送时间（即使部分群发送失败）
    if success_count > 0:
        last_send_time = datetime.now()
        logger.info(f"新闻图片定时发送完成，成功发送到 {success_count} 个群聊")

async def send_image_to_groups_with_retry(bot, image_data, use_file_path=False):
    """发送图片到群聊，带重试机制"""
    try:
        # 确保SHWGIJ_SEND_GROUPS是字符串
        groups_str = str(SHWGIJ_SEND_GROUPS)
        # 分割群ID并过滤空字符串
        group_ids = [gid.strip() for gid in groups_str.split(',') if gid.strip()]
        
        logger.info(f"准备发送新闻图片到 {len(group_ids)} 个群聊")
        success_count = 0
        
        # 发送图片到每个群聊，添加重试机制
        for group_id in group_ids:
            retries = 0
            max_retries = 3
            sent = False
            
            while retries < max_retries and not sent:
                try:
                    logger.info(f"尝试发送新闻图片到群聊 {group_id} (第{retries+1}次尝试)")
                    
                    # 根据是否使用文件路径选择发送方式
                    if use_file_path and os.path.exists(TEMP_IMAGE_FILE):
                        # 使用文件路径发送
                        await asyncio.wait_for(
                            bot.send_group_msg(
                                group_id=int(group_id),
                                message=MessageSegment.image(TEMP_IMAGE_FILE)
                            ),
                            timeout=20  # 增加超时时间到20秒
                        )
                    else:
                        # 使用内存数据发送
                        await asyncio.wait_for(
                            bot.send_group_msg(
                                group_id=int(group_id),
                                message=MessageSegment.image(image_data)
                            ),
                            timeout=20  # 增加超时时间到20秒
                        )
                    
                    logger.info(f"已成功发送新闻图片到群聊: {group_id}")
                    success_count += 1
                    sent = True
                    # 发送成功后，短暂延迟避免请求过于密集
                    await asyncio.sleep(1)
                except Exception as e:
                    retries += 1
                    error_msg = str(e)
                    logger.warning(f"发送新闻图片到群聊 {group_id} 失败 (尝试 {retries}/{max_retries}): {error_msg}")
                    
                    # 检查是否是超时错误或retcode=1200
                    is_timeout_error = 'timeout' in error_msg.lower() or '1200' in error_msg
                    if is_timeout_error and retries < max_retries:
                        logger.info(f"等待3秒后重试发送到群聊 {group_id}")
                        await asyncio.sleep(3)  # 等待3秒后重试
                    else:
                        # 其他错误不重试
                        break
        
        if success_count == 0:
            logger.error(f"新闻图片定时发送失败，所有 {len(group_ids)} 个群聊都发送失败")
        
        return success_count
    except Exception as e:
        logger.error(f"解析或发送群聊ID失败: {str(e)}")
        return 0

# 解析cron表达式的辅助函数
def parse_cron_expression(expr):
    """解析cron表达式为APScheduler的参数格式"""
    parts = expr.split()
    if len(parts) == 5:
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4]
        }
    return {}

# 注册定时任务
@driver.on_startup
async def setup_scheduler():
    """启动定时任务"""
    if SHWGIJ_CRON_ENABLE:
        logger.info(f"设置新闻图片定时任务，表达式: {SHWGIJ_CRON_EXPRESSION}")
        try:
            # 解析cron表达式
            cron_params = parse_cron_expression(SHWGIJ_CRON_EXPRESSION)
            if not cron_params:
                logger.error(f"无效的cron表达式: {SHWGIJ_CRON_EXPRESSION}")
                return
            
            # 添加定时任务，使用NoneBot的scheduler
            scheduler.add_job(
                send_news_image_to_groups,
                "cron",
                id="news_image_cron",
                replace_existing=True,
                **cron_params  # 展开具体的时间参数
            )
            logger.info("新闻图片定时任务注册成功")
        except Exception as e:
            logger.error(f"注册新闻图片定时任务失败: {str(e)}")
    else:
        logger.info("新闻图片定时任务未启用")

# 测试定时任务命令
test_cron = on_command("测试定时任务", priority=10, block=True)

@test_cron.handle()
async def handle_test_cron(bot: Bot, event: Event):
    """手动触发测试定时任务"""
    logger.info("手动触发测试定时任务")
    
    # 临时禁用日期检查，强制发送
    global last_send_time
    original_last_send = last_send_time
    last_send_time = None
    
    try:
        # 直接调用发送函数
        await send_news_image_to_groups()
        # 命令成功完成，不抛出异常
        await test_cron.finish("测试定时任务执行完成，查看日志了解详情")
    except Exception as e:
        # 排除 FinishedException，它是正常的命令结束信号
        from nonebot.exception import FinishedException
        if isinstance(e, FinishedException):
            # 这是正常的命令结束，不需要处理
            raise
        
        # 处理真正的错误
        logger.error(f"测试定时任务执行失败: {str(e)}")
        await test_cron.finish(f"测试定时任务执行失败: {str(e)}")
    finally:
        # 恢复原始的last_send_time
        last_send_time = original_last_send

# 修改：缓存清理功能
async def cleanup_cache_files():
    """定期清理过期的缓存文件"""
    try:
        if not os.path.exists(CACHE_DIR):
            log_debug("缓存目录不存在，无需清理")
            return
        
        # 获取当前时间
        current_time = time.time()
        # 计算过期时间（秒）
        expire_seconds = SHWGIJ_CACHE_EXPIRE_DAYS * 24 * 60 * 60
        
        files_removed = 0
        total_size_freed = 0
        
        # 遍历缓存目录中的所有文件
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            # 跳过子目录
            if not os.path.isfile(file_path):
                continue
            
            # 获取文件的修改时间
            file_modified_time = os.path.getmtime(file_path)
            # 检查文件是否过期
            if current_time - file_modified_time > expire_seconds:
                try:
                    # 记录文件大小
                    file_size = os.path.getsize(file_path)
                    # 删除文件
                    os.remove(file_path)
                    files_removed += 1
                    total_size_freed += file_size
                    log_debug(f"已删除过期缓存文件: {filename}, 大小: {file_size/1024:.2f}KB")
                except Exception as e:
                    logger.warning(f"删除缓存文件 {filename} 失败: {str(e)}")
        
        if files_removed > 0:
            logger.info(f"缓存清理完成: 删除了 {files_removed} 个过期文件，释放空间 {total_size_freed/1024/1024:.2f}MB")
        else:
            log_debug("缓存清理完成: 没有过期文件需要删除")
    except Exception as e:
        logger.error(f"执行缓存清理任务失败: {str(e)}")