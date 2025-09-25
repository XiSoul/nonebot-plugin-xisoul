import httpx
import json
import os
import asyncio
import time
# 修复导入部分，移除重复的httpx导入
# import httpx  # 这行应该被删除
from nonebot import on_command, get_driver, logger, get_bot  # 新增get_bot导入
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
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
# 缓存文件目录
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
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

# 解析群聊ID字符串为列表
def parse_group_ids(group_ids_str) -> list:
    if not group_ids_str:
        return []
    # 确保是字符串类型，解决'int' object has no attribute 'replace'错误
    group_ids_str = str(group_ids_str)
    # 支持逗号、空格、分号分隔的群聊ID字符串
    return [int(gid.strip()) for gid in group_ids_str.replace(';', ',').split(',') if gid.strip().isdigit()]

async def clear_news_cache(clear_files=False):
    """清空新闻图片缓存
    
    Args:
        clear_files: 是否同时清空缓存文件，默认为False
    """
    global cached_image_data, cached_image_date
    
    # 清空内存缓存
    cached_image_data = None
    cached_image_date = None
    logger.info("已清空新闻图片内存缓存")
    
    # 如果需要同时清空缓存文件
    if clear_files:
        try:
            if not os.path.exists(CACHE_DIR):
                logger.info("缓存目录不存在")
                return
            
            # 遍历并删除所有新闻图片缓存文件
            files_removed = 0
            total_size_freed = 0
            
            for filename in os.listdir(CACHE_DIR):
                # 只删除新闻图片缓存文件（根据文件名模式判断）
                if filename.startswith("news_") or filename.startswith("news_image_") and filename.endswith(".jpg"):
                    file_path = os.path.join(CACHE_DIR, filename)
                    if os.path.isfile(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            files_removed += 1
                            total_size_freed += file_size
                            log_debug(f"已删除缓存文件: {filename}, 大小: {file_size/1024:.2f}KB")
                        except Exception as e:
                            logger.warning(f"删除缓存文件 {filename} 失败: {str(e)}")
            
            if files_removed > 0:
                logger.info(f"已删除 {files_removed} 个缓存文件，释放 {total_size_freed/1024:.2f}KB 空间")
            else:
                logger.info("没有可删除的缓存文件")
        except Exception as e:
            logger.error(f"清理缓存文件时发生错误: {str(e)}")

# 获取当天的缓存文件路径
def get_today_cache_file():
    """获取当天的缓存文件路径"""
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(CACHE_DIR, f"news_{today}.jpg")

# 查找最新的缓存文件
def find_latest_cache_file():
    """查找最新的缓存文件"""
    if not os.path.exists(CACHE_DIR):
        return None
    
    # 获取所有缓存文件
    files = []
    for filename in os.listdir(CACHE_DIR):
        if filename.startswith("news_") and filename.endswith(".jpg"):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                files.append((file_path, os.path.getmtime(file_path)))
    
    # 按修改时间排序，取最新的文件
    if files:
        files.sort(key=lambda x: x[1], reverse=True)
        return files[0][0]
    
    return None

# 保存图片到缓存
async def save_image_to_cache(image_data):
    """保存图片到缓存"""
    try:
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        # 保存当天的缓存文件
        today_cache_file = get_today_cache_file()
        with open(today_cache_file, "wb") as f:
            f.write(image_data)
        
        log_debug(f"已保存新闻图片到缓存: {today_cache_file}")
        
        # 清理过期缓存
        await cleanup_cache_files()
    except Exception as e:
        logger.warning(f"保存图片到缓存失败: {str(e)}")

# 保存临时图片文件
async def save_temp_image(image_data):
    """保存临时图片文件"""
    try:
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        with open(TEMP_IMAGE_FILE, "wb") as f:
            f.write(image_data)
        
        log_debug(f"已保存临时图片: {TEMP_IMAGE_FILE}")
        return TEMP_IMAGE_FILE
    except Exception as e:
        logger.warning(f"保存临时图片失败: {str(e)}")
        return None

# 清理过期的缓存文件
async def cleanup_cache_files():
    """清理过期的缓存文件"""
    try:
        if not os.path.exists(CACHE_DIR):
            return
        
        current_time = time.time()
        expire_seconds = SHWGIJ_CACHE_EXPIRE_DAYS * 24 * 60 * 60  # 转换为秒
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

# 获取新闻图片的核心函数
async def get_news_image():
    global cached_image_data, cached_image_date
    current_date = datetime.now().date()
    today_cache_file = get_today_cache_file()
    
    # 检查是否有当天缓存的图片
    if cached_image_data and cached_image_date == current_date:
        log_debug("使用内存缓存的新闻图片")
        return cached_image_data
    
    # 修改缓存检查逻辑，添加删除过期缓存的功能
    # 检查是否有当天的本地缓存文件
    if os.path.exists(today_cache_file):
        try:
            # 获取文件的修改日期
            file_modify_time = datetime.fromtimestamp(os.path.getmtime(today_cache_file)).date()
            if file_modify_time == current_date:
                # 如果是今天的缓存，读取文件
                with open(today_cache_file, "rb") as f:
                    cached_image_data = f.read()
                    cached_image_date = current_date
                    log_debug("从本地缓存文件加载新闻图片")
                    return cached_image_data
            else:
                # 如果不是今天的缓存，删除文件
                os.remove(today_cache_file)
                logger.info(f"删除过期缓存文件: {today_cache_file}")
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
    
    # 修复API调用部分的异常处理结构
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
                        # API返回错误时的缓存使用逻辑
                        error_msg = data.get('msg', '未知错误')
                        logger.error(f"API返回错误: {error_msg}")
                        # 尝试使用最新的缓存（如果有）
                        latest_cache_file = find_latest_cache_file()
                        if latest_cache_file:
                            try:
                                logger.info("尝试使用缓存的图片")
                                with open(latest_cache_file, "rb") as f:
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
        # 尝试使用最新的缓存
        latest_cache_file = find_latest_cache_file()
        if latest_cache_file:
            try:
                logger.info("HTTP错误，尝试使用缓存的图片")
                with open(latest_cache_file, "rb") as f:
                    return f.read()
            except Exception as cache_e:
                logger.warning(f"读取缓存图片失败: {str(cache_e)}")
    except httpx.RequestError as e:
        logger.error(f"网络请求异常: {str(e)}")
        # 尝试使用最新的缓存
        latest_cache_file = find_latest_cache_file()
        if latest_cache_file:
            try:
                logger.info("网络错误，尝试使用缓存的图片")
                with open(latest_cache_file, "rb") as f:
                    return f.read()
            except Exception as cache_e:
                logger.warning(f"读取缓存图片失败: {str(cache_e)}")
    except Exception as e:
        logger.error(f"获取新闻图片失败: {str(e)}", exc_info=True)
        
        # API调用失败时，查找最新的缓存文件（不一定是今天的）
        latest_cache_file = find_latest_cache_file()
        if latest_cache_file:
            try:
                with open(latest_cache_file, "rb") as f:
                    logger.info(f"使用最近的缓存图片: {latest_cache_file}")
                    return f.read()
            except Exception as cache_e:
                logger.warning(f"读取最新缓存图片失败: {str(cache_e)}")
    
    return None

# 延时删除图片文件
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

# 发送新闻图片到多个群聊
async def send_news_image_to_groups():
    logger.info("===== 新闻图片定时任务开始执行 =====")
    try:
        # 检查是否需要发送（仅在工作日发送）
        today = datetime.now()
        current_time = today.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"当前时间: {current_time}")
        
        if today.weekday() >= 5:  # 0=周一, 1=周二, ..., 5=周六, 6=周日
            logger.info(f"今天是{today.strftime('%Y-%m-%d')}，休息日，不发送新闻")
            return

        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        logger.info(f"开始获取新闻图片")

        # 定义最大重试次数（从8点到18点，每5分钟重试一次，最多约120次）
        max_retries = 120
        retry_count = 0
        image_data = None
        
        # 重试获取图片直到成功或达到最大重试次数
        while retry_count < max_retries:
            # 获取新闻图片
            image_data = await get_news_image()
            
            if image_data:
                # 成功获取到图片，退出循环
                logger.info(f"获取新闻图片成功，共尝试{retry_count + 1}次")
                break
            
            # 获取失败，等待5分钟后重试
            retry_count += 1
            logger.warning(f"获取新闻图片失败，将在5分钟后进行第{retry_count + 1}次重试")
            
            # 等待5分钟
            await asyncio.sleep(300)  # 300秒 = 5分钟
            
            # 检查是否超过当天重试时间（例如18:00）
            current_hour = datetime.now().hour
            if current_hour >= 18:
                logger.warning(f"已超过18:00，今日不再重试获取新闻图片")
                return
        
        # 检查是否获取到图片
        if not image_data:
            logger.error(f"达到最大重试次数({max_retries})，今日未能获取到新闻图片，取消发送")
            return

        # 解析配置中的群聊ID
        groups = parse_group_ids(SHWGIJ_SEND_GROUPS)
        if not groups:
            logger.error("未配置有效的群聊ID")
            return

        logger.info(f"准备发送新闻图片到 {len(groups)} 个群聊")
        success_count = await send_image_to_groups_with_retry(image_data, groups)
        logger.info(f"新闻图片发送完成，成功发送到 {success_count} 个群聊")
    except Exception as e:
        logger.error(f"发送新闻图片时发生错误: {str(e)}")
    finally:
        # 清空内存缓存
        await clear_news_cache()
        logger.info("===== 新闻图片定时任务执行结束 =====")

# 发送图片到多个群聊，并添加重试机制
async def send_image_to_groups_with_retry(image_data, groups, max_retries=3):
    """发送图片到多个群聊，并添加重试机制"""
    try:
        # 获取bot实例
        bot = get_bot()
        
        logger.info(f"准备发送新闻图片到 {len(groups)} 个群聊")
        success_count = 0
        
        # 发送图片到每个群聊，添加重试机制
        for group_id in groups:
            retries = 0
            sent = False
            
            # 确保group_id是整数类型，直接跳过类型检查外的处理
            try:
                # 无论输入是什么，都尝试转换为整数
                target_group_id = int(group_id)
            except (ValueError, TypeError):
                logger.warning(f"无效的群聊ID: {group_id}")
                continue
            
            while retries < max_retries and not sent:
                try:
                    logger.info(f"尝试发送新闻图片到群聊 {target_group_id} (第{retries+1}次尝试)")
                    
                    # 使用内存数据发送
                    await asyncio.wait_for(
                        bot.send_group_msg(
                            group_id=target_group_id,  # 使用转换后的整数
                            message=MessageSegment.image(image_data)
                        ),
                        timeout=20  # 增加超时时间到20秒
                    )
                    
                    logger.info(f"已成功发送新闻图片到群聊: {target_group_id}")
                    success_count += 1
                    sent = True
                    # 发送成功后，短暂延迟避免请求过于密集
                    await asyncio.sleep(1)
                except Exception as e:
                    retries += 1
                    error_msg = str(e)
                    logger.warning(f"发送新闻图片到群聊 {target_group_id} 失败 (尝试 {retries}/{max_retries}): {error_msg}")
                    
                    # 检查是否是超时错误或retcode=1200
                    is_timeout_error = 'timeout' in error_msg.lower() or '1200' in error_msg
                    if is_timeout_error and retries < max_retries:
                        logger.info(f"等待3秒后重试发送到群聊 {target_group_id}")
                        await asyncio.sleep(3)  # 等待3秒后重试
                    else:
                        # 其他错误不重试
                        break
        
        if success_count == 0:
            logger.error(f"新闻图片定时发送失败，所有 {len(groups)} 个群聊都发送失败")
        
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
                misfire_grace_time=60,  # 允许任务在错过执行时间后60秒内仍能执行
                timezone="Asia/Shanghai",  # 设置时区为上海时区
                **cron_params  # 展开具体的时间参数
            )
            logger.info("新闻图片定时任务注册成功")
        except Exception as e:
            logger.error(f"注册新闻图片定时任务失败: {str(e)}")
    else:
        logger.info("新闻图片定时任务未启用")
async def test_news_image_sending():
    """测试新闻图片发送的辅助函数"""
    try:
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        logger.info(f"开始获取新闻图片")

        # 获取新闻图片
        image_data = await get_news_image()
        if not image_data:
            logger.error("获取新闻图片失败，跳过发送")
            return False

        # 解析配置中的群聊ID
        groups = parse_group_ids(SHWGIJ_SEND_GROUPS)
        if not groups:
            logger.error("未配置有效的群聊ID")
            return False

        logger.info(f"准备发送新闻图片到 {len(groups)} 个群聊")
        success_count = await send_image_to_groups_with_retry(image_data, groups)
        return success_count > 0
    except Exception as e:
        logger.error(f"发送新闻图片时发生错误: {str(e)}")
        return False
    finally:
        # 清空内存缓存
        await clear_news_cache()



# 测试定时任务的命令
test_cron = on_command("测试定时任务", aliases={"测试新闻定时"}, block=True)

@test_cron.handle()
async def handle_test_cron(bot: Bot):
    """处理测试定时任务命令"""
    logger.info("收到测试定时任务命令")
    
    # 临时禁用日期检查，强制发送
    global cached_image_data, cached_image_date
    cached_image_data = None
    cached_image_date = None
    
    try:
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        logger.info(f"开始获取新闻图片")

        # 获取新闻图片
        image_data = await get_news_image()
        if not image_data:
            logger.error("获取新闻图片失败，跳过发送")
            return False

        # 解析配置中的群聊ID
        groups = parse_group_ids(SHWGIJ_SEND_GROUPS)
        if not groups:
            logger.error("未配置有效的群聊ID")
            return False

        logger.info(f"准备发送新闻图片到 {len(groups)} 个群聊")
        success_count = await send_image_to_groups_with_retry(image_data, groups)
        return success_count > 0
    except Exception as e:
        logger.error(f"发送新闻图片时发生错误: {str(e)}")
        return False
    finally:
        # 清空内存缓存
        await clear_news_cache()
    
    try:
        # 调用内部执行函数
        success = await execute_test()
        
        if success:
            await test_cron.finish("测试定时任务执行完成")
        else:
            await test_cron.finish("测试定时任务执行失败")
    except Exception as e:
        logger.error(f"测试定时任务执行失败: {str(e)}")
        # 即使出错，也尝试发送一条完成消息给用户
        try:
            await test_cron.finish(f"测试定时任务执行失败: {str(e)}")
        except:
            pass  # 如果已经无法发送消息，就忽略这个错误