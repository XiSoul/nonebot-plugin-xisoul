import httpx
import re
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any
from nonebot import logger

class HuangLiScraper:
    """
    黄历网页抓取器，用于从指定URL获取黄历数据
    """
    
    # 基础URL
    BASE_URL = "https://www.huangli123.net/huangli/{date}.html"
    
    @staticmethod
    async def fetch_huangli_data(date: str) -> Optional[Dict[str, Any]]:
        """
        从网页获取指定日期的黄历数据
        
        Args:
            date: 日期字符串，格式为 YYYY-MM-DD
            
        Returns:
            包含黄历数据的字典，如果获取失败则返回None
        """
        # 构建完整URL
        url = HuangLiScraper.BASE_URL.format(date=date)
        logger.info(f"正在请求黄历数据: {url}")
        
        try:
            # 发送HTTP请求
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # 解析HTML内容
                html_content = response.text
                return HuangLiScraper.parse_html_content(html_content, date)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP请求错误: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"网络请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"解析黄历数据失败: {str(e)}")
        
        return None
    
    @staticmethod
    def parse_html_content(html_content: str, date: str) -> Dict[str, Any]:
        """
        解析HTML内容，提取黄历数据
        
        Args:
            html_content: HTML内容字符串
            date: 请求的日期
            
        Returns:
            解析后的黄历数据字典
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {
            'date': date,
            'basic_info': {},
            'wu_xing': {},
            'chong_he': {},
            'san_sha': {},
            'qi_sha': {},
            'ji_xiong': {},
            'gua_xiang': {},
            'yue_ling': {},
            'tian_shen': {},
            'er_shi_ba_xiu': {},
            'di_mu_jing': {},
            'errors': []
        }
        
        try:
            # 提取基础信息 - 星宿
            xiu_element = soup.find(text=re.compile('今日星宿'))
            if xiu_element and xiu_element.parent:
                xiu_text = xiu_element.parent.get_text()
                xiu_match = re.search(r'今日星宿：\\s*([^的]+)', xiu_text)
                if xiu_match:
                    result['basic_info']['star'] = xiu_match.group(1).strip()
            
            # 提取五行信息
            wu_xing_elements = soup.find_all(text=re.compile('[年月日]五行'))
            for element in wu_xing_elements:
                if element.parent:
                    wu_xing_text = element.parent.get_text()
                    if '年五行' in wu_xing_text:
                        match = re.search(r'年五行：([^\s]+)', wu_xing_text)
                        if match:
                            result['wu_xing']['year'] = match.group(1).strip()
                    elif '月五行' in wu_xing_text:
                        match = re.search(r'月五行：([^\s]+)', wu_xing_text)
                        if match:
                            result['wu_xing']['month'] = match.group(1).strip()
                    elif '日五行' in wu_xing_text:
                        match = re.search(r'日五行：([^\s]+)', wu_xing_text)
                        if match:
                            result['wu_xing']['day'] = match.group(1).strip()
            
            # 提取冲合信息
            chong_he_element = soup.find(text=re.compile('今日冲合'))
            if chong_he_element and chong_he_element.parent:
                chong_he_text = chong_he_element.parent.get_text()
                result['chong_he']['info'] = chong_he_text.replace('今日冲合', '').strip()
            
            # 提取三煞方信息
            san_sha_elements = soup.find_all(text=re.compile('三煞'))
            for element in san_sha_elements:
                if element.parent:
                    san_sha_text = element.parent.get_text()
                    if '本年三煞' in san_sha_text:
                        match = re.search(r'本年三煞：([^;]+)', san_sha_text)
                        if match:
                            result['san_sha']['year'] = match.group(1).strip()
                    elif '本月三煞' in san_sha_text:
                        match = re.search(r'本月三煞：([^;]+)', san_sha_text)
                        if match:
                            result['san_sha']['month'] = match.group(1).strip()
                    elif '今日三煞' in san_sha_text:
                        match = re.search(r'今日三煞：([^;]+)', san_sha_text)
                        if match:
                            result['san_sha']['day'] = match.group(1).strip()
            
            # 提取七煞方信息
            qi_sha_elements = soup.find_all(text=re.compile('七煞'))
            for element in qi_sha_elements:
                if element.parent:
                    qi_sha_text = element.parent.get_text()
                    if '年七煞' in qi_sha_text:
                        match = re.search(r'年七煞：([^\s]+)', qi_sha_text)
                        if match:
                            result['qi_sha']['year'] = match.group(1).strip()
                    elif '月七煞' in qi_sha_text:
                        match = re.search(r'月七煞：([^\s]+)', qi_sha_text)
                        if match:
                            result['qi_sha']['month'] = match.group(1).strip()
                    elif '日七煞' in qi_sha_text:
                        match = re.search(r'日七煞：([^\s]+)', qi_sha_text)
                        if match:
                            result['qi_sha']['day'] = match.group(1).strip()
            
            # 提取九星吉凶信息
            jiu_xing_element = soup.find(text=re.compile('今日河图洛书九星吉凶'))
            if jiu_xing_element:
                jiu_xing_div = jiu_xing_element.find_parent(['div', 'p'])
                if jiu_xing_div:
                    result['ji_xiong']['nine_star'] = jiu_xing_div.get_text().replace('今日河图洛书九星吉凶', '').strip()
            
            # 提取卦象信息
            gua_xiang_element = soup.find(text=re.compile('今日卦象'))
            if gua_xiang_element and gua_xiang_element.parent:
                gua_xiang_div = gua_xiang_element.find_parent(['div', 'p'])
                if gua_xiang_div:
                    result['gua_xiang']['info'] = gua_xiang_div.get_text().replace('今日卦象：', '').strip()
                    
                    # 查找卦象详细描述
                    next_element = gua_xiang_div.find_next(['div', 'p'])
                    if next_element:
                        gua_desc = []
                        current = next_element
                        while current and not any(keyword in current.get_text() for keyword in ['月令', '物候', '今日十二神', '二十八星宿']):
                            gua_desc.append(current.get_text().strip())
                            current = current.find_next(['div', 'p'])
                        result['gua_xiang']['description'] = '\n'.join(gua_desc)
            
            # 提取月令、物候等信息
            yue_ling_element = soup.find(text=re.compile('月令'))
            if yue_ling_element and yue_ling_element.parent:
                yue_ling_text = yue_ling_element.parent.get_text()
                match = re.search(r'月令：\\s*([^\s]+)', yue_ling_text)
                if match:
                    result['yue_ling']['month'] = match.group(1).strip()
            
            wu_hou_element = soup.find(text=re.compile('物候'))
            if wu_hou_element and wu_hou_element.parent:
                wu_hou_text = wu_hou_element.parent.get_text()
                match = re.search(r'物候：\\s*([^\s]+)', wu_hou_text)
                if match:
                    result['yue_ling']['phenology'] = match.group(1).strip()
            
            # 提取十二神吉凶信息
            er_shi_shen_element = soup.find(text=re.compile('今日十二神吉凶所主'))
            if er_shi_shen_element and er_shi_shen_element.parent:
                er_shi_shen_div = er_shi_shen_element.find_parent(['div', 'p'])
                if er_shi_shen_div:
                    result['tian_shen']['twelve_gods'] = er_shi_shen_div.get_text().replace('今日十二神吉凶所主', '').strip()
            
            # 提取二十八星宿吉凶信息
            er_shi_ba_xiu_element = soup.find(text=re.compile('今日二十八星宿吉凶'))
            if er_shi_ba_xiu_element and er_shi_ba_xiu_element.parent:
                er_shi_ba_xiu_div = er_shi_ba_xiu_element.find_parent(['div', 'p'])
                if er_shi_ba_xiu_div:
                    result['er_shi_ba_xiu']['info'] = er_shi_ba_xiu_div.get_text().replace('今日二十八星宿吉凶', '').strip()
            
            # 提取地母经信息
            di_mu_jing_element = soup.find(text=re.compile('地母经卜曰'))
            if di_mu_jing_element:
                # 提取卜曰内容
                div_element = di_mu_jing_element.find_parent(['div', 'p'])
                if div_element:
                    result['di_mu_jing']['divination'] = div_element.get_text().replace('地母经卜曰', '').strip()
                    
                    # 提取诗曰内容
                    shi_yue_element = soup.find(text=re.compile('地母经诗曰'))
                    if shi_yue_element and shi_yue_element.parent:
                        result['di_mu_jing']['poem'] = shi_yue_element.parent.get_text().replace('地母经诗曰', '').strip()
            
        except Exception as e:
            logger.error(f"解析HTML内容时出错: {str(e)}")
            result['errors'].append(str(e))
        
        return result
    
    @staticmethod
    def format_huangli_data(huangli_data: Dict[str, Any]) -> List[str]:
        """
        格式化黄历数据为可读文本列表
        
        Args:
            huangli_data: 黄历数据字典
            
        Returns:
            格式化后的文本列表
        """
        messages = []
        
        # 添加标题
        messages.append(f"📅 {huangli_data['date']} 黄历信息")
        messages.append("=" * 30)
        
        # 基础信息
        if huangli_data['basic_info'].get('star'):
            messages.append(f"⭐ 今日星宿：{huangli_data['basic_info']['star']}")
        
        # 五行信息
        if huangli_data['wu_xing']:
            messages.append("\n🔥 五行信息")
            if huangli_data['wu_xing'].get('year'):
                messages.append(f"年五行：{huangli_data['wu_xing']['year']}")
            if huangli_data['wu_xing'].get('month'):
                messages.append(f"月五行：{huangli_data['wu_xing']['month']}")
            if huangli_data['wu_xing'].get('day'):
                messages.append(f"日五行：{huangli_data['wu_xing']['day']}")
        
        # 冲合信息
        if huangli_data['chong_he'].get('info'):
            messages.append("\n⚖️ 冲合信息")
            messages.append(huangli_data['chong_he']['info'])
        
        # 三煞方
        if huangli_data['san_sha']:
            messages.append("\n⚠️ 三煞方位")
            if huangli_data['san_sha'].get('year'):
                messages.append(f"年三煞：{huangli_data['san_sha']['year']}")
            if huangli_data['san_sha'].get('month'):
                messages.append(f"月三煞：{huangli_data['san_sha']['month']}")
            if huangli_data['san_sha'].get('day'):
                messages.append(f"日三煞：{huangli_data['san_sha']['day']}")
        
        # 七煞方
        if huangli_data['qi_sha']:
            messages.append("\n💀 七煞方位")
            if huangli_data['qi_sha'].get('year'):
                messages.append(f"年七煞：{huangli_data['qi_sha']['year']}")
            if huangli_data['qi_sha'].get('month'):
                messages.append(f"月七煞：{huangli_data['qi_sha']['month']}")
            if huangli_data['qi_sha'].get('day'):
                messages.append(f"日七煞：{huangli_data['qi_sha']['day']}")
        
        # 九星吉凶
        if huangli_data['ji_xiong'].get('nine_star'):
            messages.append("\n🔮 九星吉凶")
            messages.append(huangli_data['ji_xiong']['nine_star'])
        
        # 卦象信息
        if huangli_data['gua_xiang'].get('info'):
            messages.append("\n🧩 今日卦象")
            messages.append(huangli_data['gua_xiang']['info'])
            if huangli_data['gua_xiang'].get('description'):
                messages.append("\n" + huangli_data['gua_xiang']['description'])
        
        # 月令、物候等信息
        if huangli_data['yue_ling']:
            messages.append("\n🌿 时节信息")
            if huangli_data['yue_ling'].get('month'):
                messages.append(f"月令：{huangli_data['yue_ling']['month']}")
            if huangli_data['yue_ling'].get('phenology'):
                messages.append(f"物候：{huangli_data['yue_ling']['phenology']}")
        
        # 十二神吉凶
        if huangli_data['tian_shen'].get('twelve_gods'):
            messages.append("\n👼 十二神吉凶")
            messages.append(huangli_data['tian_shen']['twelve_gods'])
        
        # 二十八星宿吉凶
        if huangli_data['er_shi_ba_xiu'].get('info'):
            messages.append("\n✨ 二十八星宿吉凶")
            messages.append(huangli_data['er_shi_ba_xiu']['info'])
        
        # 地母经信息
        if huangli_data['di_mu_jing']:
            messages.append("\n📜 地母经")
            if huangli_data['di_mu_jing'].get('divination'):
                messages.append("卜曰：")
                messages.append(huangli_data['di_mu_jing']['divination'])
            if huangli_data['di_mu_jing'].get('poem'):
                messages.append("\n诗曰：")
                messages.append(huangli_data['di_mu_jing']['poem'])
        
        # 错误信息
        if huangli_data.get('errors'):
            messages.append("\n❌ 数据解析警告")
            for error in huangli_data['errors']:
                messages.append(f"- {error}")
        
        return messages
