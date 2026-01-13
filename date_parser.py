import re
from datetime import datetime
from typing import Tuple, Optional

class DateParser:
    """
    日期解析器，支持多种日期格式的解析
    """
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[Tuple[int, int, int]]:
        """
        解析日期字符串，提取年月日信息
        
        支持的格式：
        - 2025-11-19（短横线分隔）
        - 2025.11.19（点分隔）
        - 2025/11/19（斜杠分隔）
        - 2025年11月19日（中文分隔）
        - 2025年11月19日
        
        Args:
            date_str: 日期字符串
            
        Returns:
            包含年、月、日的元组，如果解析失败则返回None
        """
        # 去除字符串中的空白字符
        date_str = date_str.strip()
        
        # 尝试匹配各种日期格式
        patterns = [
            # 匹配 2025-11-19, 2025.11.19, 2025/11/19 等格式
            r'^(\d{4})[\-\./](\d{1,2})[\-\./](\d{1,2})$',
            # 匹配 2025年11月19日 或 2025年11月19 格式
            r'^(\d{4})年(\d{1,2})月(\d{1,2})日?$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    # 提取年月日并转换为整数
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    
                    # 验证日期是否有效
                    if DateParser.is_valid_date(year, month, day):
                        return (year, month, day)
                except ValueError:
                    continue
        
        # 尝试匹配纯数字格式，如 20251119
        numeric_pattern = r'^(\d{8})$'
        match = re.match(numeric_pattern, date_str)
        if match:
            try:
                year = int(match.group(1)[:4])
                month = int(match.group(1)[4:6])
                day = int(match.group(1)[6:8])
                
                if DateParser.is_valid_date(year, month, day):
                    return (year, month, day)
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def is_valid_date(year: int, month: int, day: int) -> bool:
        """
        验证日期是否有效
        
        Args:
            year: 年份
            month: 月份
            day: 日期
            
        Returns:
            日期是否有效的布尔值
        """
        try:
            # 使用datetime构造函数验证日期
            datetime(year, month, day)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def format_date(year: int, month: int, day: int) -> str:
        """
        将年月日格式化为URL所需的格式 (YYYY-MM-DD)
        
        Args:
            year: 年份
            month: 月份
            day: 日期
            
        Returns:
            格式化后的日期字符串
        """
        # 月份和日期不足两位时自动补零
        return f"{year}-{month:02d}-{day:02d}"
    
    @staticmethod
    def parse_date_from_command(command: str) -> Optional[Tuple[int, int, int]]:
        """
        从命令字符串中解析日期
        
        Args:
            command: 包含日期的命令字符串
            
        Returns:
            包含年、月、日的元组，如果解析失败则返回None
        """
        # 处理空字符串或特殊关键词
        command = command.strip()
        
        # 处理特殊关键词
        if not command or command in ["今天", "今日"]:
            now = datetime.now()
            return (now.year, now.month, now.day)
        elif command in ["明天", "明日"]:
            tomorrow = datetime.now().replace(day=datetime.now().day + 1)
            return (tomorrow.year, tomorrow.month, tomorrow.day)
        elif command in ["昨天", "昨日"]:
            yesterday = datetime.now().replace(day=datetime.now().day - 1)
            return (yesterday.year, yesterday.month, yesterday.day)
        
        # 尝试直接解析命令字符串
        date_tuple = DateParser.parse_date(command)
        if date_tuple:
            return date_tuple
        
        # 尝试提取命令中的日期部分
        # 例如 "黄历 2025-11-19" 或 "2025-11-19黄历"
        parts = command.split(' ')
        for part in parts:
            date_tuple = DateParser.parse_date(part)
            if date_tuple:
                return date_tuple
        
        # 使用正则表达式尝试从任何位置提取日期
        # 匹配常见日期格式
        date_patterns = [
            r'(\d{4})[\-\./](\d{1,2})[\-\./](\d{1,2})',  # 2025-11-19, 2025.11.19, 2025/11/19
            r'(\d{4})年(\d{1,2})月(\d{1,2})日?',         # 2025年11月19日, 2025年11月19
            r'(\d{8})',                                   # 20251119
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, command)
            if match:
                if len(match.groups()) == 3:
                    try:
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                        if DateParser.is_valid_date(year, month, day):
                            return (year, month, day)
                    except ValueError:
                        continue
                elif len(match.groups()) == 1:  # 纯数字格式
                    try:
                        date_str = match.group(1)
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        if DateParser.is_valid_date(year, month, day):
                            return (year, month, day)
                    except ValueError:
                        continue
        
        return None
