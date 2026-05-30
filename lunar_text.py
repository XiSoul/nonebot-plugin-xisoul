import httpx
import json
from datetime import datetime
from nonebot import on_command, on_message, get_driver, logger
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule, CommandRule

# 定义文本黄历规则
async def is_text_lunar_command(event: Event) -> bool:
    message = str(event.message).strip()
    return message == "文字黄历" or message == "文本黄历"

__plugin_meta__ = PluginMetadata(
    name="文本黄历",
    description="获取当天的农历黄历文本信息，包含详细的传统命理和民俗数据",
    usage="文字黄历 或 文本黄历 获取文本版",
)

# 从环境变量获取配置
config = get_driver().config
# 修改为使用网站名称命名的API密钥
get_lunar_key = getattr(config, "shwgij_api_key", "")

# 命令定义
# 保留原有的命令以便兼容
lunar_calendar = on_command("文字黄历", priority=10, block=True)
# 添加新的不需要/的命令
lunar_calendar_direct = on_message(rule=is_text_lunar_command, priority=10, block=True)

def get_current_date():
    """获取当前日期的格式化字符串"""
    return datetime.now().strftime("%Y-%m-%d")

@lunar_calendar.handle()
@lunar_calendar_direct.handle()
async def handle_lunar_calendar(bot: Bot, event: Event):
    """处理文本黄历命令"""
    logger.info("收到文本黄历命令请求")
    
    # 获取当天日期
    today = get_current_date()
    logger.info(f"请求日期: {today}")
    
    # 调用API获取黄历数据
    url = f"https://api.shwgij.com/api/lunars/lunarpro"
    params = {
        "key": get_lunar_key,
        "date": today
    }
    
    logger.info(f"请求URL: {url}")
    logger.info(f"请求参数: {params}")
    
    # 构造消息
    message = []
    try:
        # 执行API请求并处理响应
        message = await fetch_and_parse_lunar_data(url, params)
    except Exception as e:
        logger.error(f"获取黄历信息失败: {str(e)}")
        message.append(f"❌ 获取黄历信息失败: {str(e)}")
    
    # 使用bot.send发送消息
    await bot.send(event, "\n".join(message))

async def fetch_and_parse_lunar_data(url: str, params: dict) -> list:
    """获取并解析黄历API数据"""
    message = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            logger.info(f"JSON解析成功，数据结构: {list(data.keys())}")
            
            # 检查响应状态
            if data.get('code') == 200:
                # 提取并翻译主要信息
                lunar_data = data.get('data', {})
                message.append(f"📅 农历黄历信息 ({params['date']})")
                message.append("=" * 30)
                
                # 调用各个辅助函数处理不同类别的信息
                message.extend(process_basic_info(lunar_data))
                message.extend(process_ganzhi_info(lunar_data))
                message.extend(process_fortune_info(lunar_data))
                message.extend(process_seasonal_info(lunar_data))
                message.extend(process_direction_info(lunar_data))
                message.extend(process_luck_info(lunar_data))
                message.extend(process_folk_info(lunar_data))
                message.extend(process_nine_star_info(lunar_data))
                message.extend(process_extra_info(lunar_data, data))
            else:
                message.append(f"❌ API返回错误: {data.get('msg', '未知错误')}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP请求错误: {str(e)}")
        message.append(f"❌ HTTP请求错误: {str(e)}")
    except httpx.RequestError as e:
        logger.error(f"网络请求异常: {str(e)}")
        message.append(f"❌ 网络请求异常: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        message.append(f"❌ JSON解析错误: {str(e)}")
    
    return message

def process_basic_info(lunar_data: dict) -> list:
    """处理基础日期时间信息"""
    message = []
    basic_info = []
    if 'Solar' in lunar_data:
        basic_info.append(f"🌞 公历日期: {lunar_data['Solar']}")
    if 'Week' in lunar_data:
        basic_info.append(f"📆 星期: {lunar_data['Week']}")
    if 'Constellation' in lunar_data:
        basic_info.append(f"⭐ 星座: {lunar_data['Constellation']}")
    if 'LunarYear' in lunar_data:
        basic_info.append(f"📜 农历年份: {lunar_data['LunarYear']}")
    if 'Lunar' in lunar_data:
        basic_info.append(f"🌙 农历日期: {lunar_data['Lunar']}")
    if 'ThisYear' in lunar_data:
        basic_info.append(f"🐉 生肖年份: {lunar_data['ThisYear']}")
    if 'FoDate' in lunar_data:
        basic_info.append(f"🙏 佛历日期: {lunar_data['FoDate']}")
    if 'DaoDate' in lunar_data:
        basic_info.append(f"☯️ 道历日期: {lunar_data['DaoDate']}")
    if 'JulianDay' in lunar_data:
        basic_info.append(f"🔢 儒略日: {lunar_data['JulianDay']}")
    
    if basic_info:
        message.extend(basic_info)
        message.append("=" * 30)
    
    return message

def process_ganzhi_info(lunar_data: dict) -> list:
    """处理干支与五行相关信息"""
    message = []
    ganzhi_info = []
    if 'GanZhiYear' in lunar_data:
        ganzhi_info.append(f"📅 年干支: {lunar_data['GanZhiYear']}")
    if 'GanZhiMonth' in lunar_data:
        ganzhi_info.append(f"📅 月干支: {lunar_data['GanZhiMonth']}")
    if 'GanZhiDay' in lunar_data:
        ganzhi_info.append(f"📅 日干支: {lunar_data['GanZhiDay']}")
    if 'GanZhiHour' in lunar_data:
        ganzhi_info.append(f"📅 时干支: {lunar_data['GanZhiHour']}")
    
    if 'WuXingYear' in lunar_data:
        ganzhi_info.append(f"🔥 年五行: {lunar_data['WuXingYear']}")
    if 'WuXingMonth' in lunar_data:
        ganzhi_info.append(f"🔥 月五行: {lunar_data['WuXingMonth']}")
    if 'WuXingDay' in lunar_data:
        ganzhi_info.append(f"🔥 日五行: {lunar_data['WuXingDay']}")
    if 'WuXingHour' in lunar_data:
        ganzhi_info.append(f"🔥 时五行: {lunar_data['WuXingHour']}")
    
    if 'NaYinYear' in lunar_data:
        ganzhi_info.append(f"🌌 年纳音: {lunar_data['NaYinYear']}")
    if 'NaYinMonth' in lunar_data:
        ganzhi_info.append(f"🌌 月纳音: {lunar_data['NaYinMonth']}")
    if 'NaYinDay' in lunar_data:
        ganzhi_info.append(f"🌌 日纳音: {lunar_data['NaYinDay']}")
    if 'NaYinHour' in lunar_data:
        ganzhi_info.append(f"🌌 时纳音: {lunar_data['NaYinHour']}")
    
    if ganzhi_info:
        message.extend(ganzhi_info)
        message.append("=" * 30)
    
    return message

def process_fortune_info(lunar_data: dict) -> list:
    """处理命理与运势相关信息"""
    message = []
    fortune_info = []
    if 'ShiShenYear' in lunar_data:
        fortune_info.append(f"👤 年十神: {lunar_data['ShiShenYear']}")
    if 'ShiShenMonth' in lunar_data:
        fortune_info.append(f"👤 月十神: {lunar_data['ShiShenMonth']}")
    if 'ShiShenDay' in lunar_data:
        fortune_info.append(f"👤 日十神: {lunar_data['ShiShenDay']}")
    if 'ShiShenHour' in lunar_data:
        fortune_info.append(f"👤 时十神: {lunar_data['ShiShenHour']}")
    if 'QiYunMan' in lunar_data:
        fortune_info.append(f"👨‍🦱 男命起运: {lunar_data['QiYunMan']}")
    if 'QiYunWoman' in lunar_data:
        fortune_info.append(f"👩‍🦱 女命起运: {lunar_data['QiYunWoman']}")
    
    if fortune_info:
        message.append("命理与运势信息")
        message.extend(fortune_info)
        message.append("=" * 30)
    
    return message

def process_seasonal_info(lunar_data: dict) -> list:
    """处理节气与时节信息"""
    message = []
    seasonal_info = []
    if 'JieQi1' in lunar_data:
        seasonal_info.append(f"🍂 当前节气: {lunar_data['JieQi1']}")
    if 'JieQi2' in lunar_data:
        seasonal_info.append(f"🍃 下一节气: {lunar_data['JieQi2']}")
    if 'PrevJieQi' in lunar_data:
        seasonal_info.append(f"⏮️ 上一节气: {lunar_data['PrevJieQi']}")
    if 'NextJieQi' in lunar_data:
        seasonal_info.append(f"⏭️ 下一节气: {lunar_data['NextJieQi']}")
    if 'YueXiang' in lunar_data:
        seasonal_info.append(f"🌔 月相: {lunar_data['YueXiang']}")
    if 'SanFu' in lunar_data:
        seasonal_info.append(f"☀️ 三伏: {lunar_data['SanFu']}")
    if 'Lunar_Festivals' in lunar_data:
        seasonal_info.append(f"🎉 农历节日: {lunar_data['Lunar_Festivals']}")
    if 'WuHou' in lunar_data:
        seasonal_info.append(f"🌿 物候: {lunar_data['WuHou']}")
    
    if seasonal_info:
        message.append("节气与时节信息")
        message.extend(seasonal_info)
        message.append("=" * 30)
    
    return message

def process_direction_info(lunar_data: dict) -> list:
    """处理方位与吉神信息"""
    message = []
    direction_info = []
    if 'XiShen' in lunar_data:
        direction_info.append(f"❤️ 喜神方位: {lunar_data['XiShen']}")
    if 'CaiShen' in lunar_data:
        direction_info.append(f"💰 财神方位: {lunar_data['CaiShen']}")
    if 'FuShen' in lunar_data:
        direction_info.append(f"🍀 福神方位: {lunar_data['FuShen']}")
    if 'YangGuiShen' in lunar_data:
        direction_info.append(f"👼 阳贵神: {lunar_data['YangGuiShen']}")
    if 'YinGuiShen' in lunar_data:
        direction_info.append(f"🌙 阴贵神: {lunar_data['YinGuiShen']}")
    if 'TaiShenDay' in lunar_data:
        direction_info.append(f"👶 当日胎神: {lunar_data['TaiShenDay']}")
    if 'TaiShenMonth' in lunar_data:
        direction_info.append(f"👶 当月胎神: {lunar_data['TaiShenMonth']}")
    if 'TaiSuiYear' in lunar_data:
        direction_info.append(f"🐯 当年太岁: {lunar_data['TaiSuiYear']}")
    if 'TaiSuiMonth' in lunar_data:
        direction_info.append(f"🐯 当月太岁: {lunar_data['TaiSuiMonth']}")
    if 'TaiSuiDay' in lunar_data:
        direction_info.append(f"🐯 当日太岁: {lunar_data['TaiSuiDay']}")
    
    if direction_info:
        message.append("方位吉神信息")
        message.extend(direction_info)
        message.append("=" * 30)
    
    return message

def process_luck_info(lunar_data: dict) -> list:
    """处理宜忌信息"""
    message = []
    luck_info = []
    if 'ChongDay' in lunar_data:
        luck_info.append(f"⚠️ 当日冲煞: {lunar_data['ChongDay']}")
    if 'ShaDay' in lunar_data:
        luck_info.append(f"⚠️ 当日煞方: {lunar_data['ShaDay']}")
    if 'JiShenDay' in lunar_data:
        luck_info.append(f"✨ 当日吉神: {lunar_data['JiShenDay']}")
    if 'XiongShaDay' in lunar_data:
        luck_info.append(f"👹 当日凶煞: {lunar_data['XiongShaDay']}")
    if 'YiDay' in lunar_data:
        luck_info.append(f"✅ 今日宜: {lunar_data['YiDay']}")
    if 'JiDay' in lunar_data:
        luck_info.append(f"❌ 今日忌: {lunar_data['JiDay']}")
    if 'LuDay' in lunar_data:
        luck_info.append(f"🎁 当日禄神: {lunar_data['LuDay']}")
    
    if luck_info:
        message.append("宜忌信息")
        message.extend(luck_info)
        message.append("=" * 30)
    
    return message

def process_folk_info(lunar_data: dict) -> list:
    """处理传统民俗与星宿相关信息"""
    message = []
    folk_info = []
    if 'PengZuBaiJi' in lunar_data:
        folk_info.append(f"📜 彭祖百忌: {lunar_data['PengZuBaiJi']}")
    if 'LiuYao' in lunar_data:
        folk_info.append(f"🔮 六曜: {lunar_data['LiuYao']}")
    if 'QiZheng' in lunar_data:
        folk_info.append(f"🌌 七政: {lunar_data['QiZheng']}")
    if 'SiShou' in lunar_data:
        folk_info.append(f"🐉 四兽: {lunar_data['SiShou']}")
    if 'XiuLuck' in lunar_data:
        folk_info.append(f"⭐ 星宿运势: {lunar_data['XiuLuck']}")
    if 'XiuSong' in lunar_data:
        folk_info.append(f"🎵 星宿歌诀: {lunar_data['XiuSong']}")
    if 'ZaoMaTou' in lunar_data:
        folk_info.append(f"🏠 灶马头: {lunar_data['ZaoMaTou']}")
    if 'ZhiXing' in lunar_data:
        folk_info.append(f"🗓️ 建除十二值星: {lunar_data['ZhiXing']}")
    if 'TianShen' in lunar_data:
        folk_info.append(f"👼 十二天神: {lunar_data['TianShen']}")
    
    if folk_info:
        message.append("传统民俗与星宿信息")
        message.extend(folk_info)
        message.append("=" * 30)
    
    return message

def process_nine_star_info(lunar_data: dict) -> list:
    """处理九星信息"""
    message = []
    nine_star_info = []
    if 'JiuXingYear' in lunar_data:
        nine_star_info.append(f"🔮 当年九星: {lunar_data['JiuXingYear']}")
    if 'JiuXingMonth' in lunar_data:
        nine_star_info.append(f"🔮 当月九星: {lunar_data['JiuXingMonth']}")
    if 'JiuXingDay' in lunar_data:
        nine_star_info.append(f"🔮 当日九星: {lunar_data['JiuXingDay']}")
    if 'JiuXingHour' in lunar_data:
        nine_star_info.append(f"🔮 当时辰九星: {lunar_data['JiuXingHour']}")
    
    if nine_star_info:
        message.append("九星信息")
        message.extend(nine_star_info)
        message.append("=" * 30)
    
    return message

# 修改process_extra_info函数，移除链接信息
def process_extra_info(lunar_data: dict, raw_data: dict) -> list:
    """处理附加信息"""
    message = []
    extra_info = []
    if 'DayYiYan' in lunar_data:
        extra_info.append(f"💡 每日一言: {lunar_data['DayYiYan']}")
    if 'WeiYu_s' in lunar_data:
        extra_info.append(f"💭 简短寄语: {lunar_data['WeiYu_s']}")
    if 'WeiYu_l' in lunar_data:
        extra_info.append(f"📝 详细寄语: {lunar_data['WeiYu_l']}")
    
    # 移除微信和相关链接信息
    # if 'WeiXin' in raw_data:
    #     extra_info.append(f"📱 {raw_data['WeiXin']}")
    # if 'url' in raw_data:
    #     extra_info.append(f"🌐 相关链接: {raw_data['url']}")
    
    if extra_info:
        message.append("附加信息")
        message.extend(extra_info)
    
    return message