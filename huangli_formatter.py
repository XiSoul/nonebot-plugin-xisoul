from typing import Dict, List, Any
from datetime import datetime
import os
from nonebot import logger

class HuangLiFormatter:
    """
    黄历数据格式化器，用于将抓取的黄历数据格式化为不同输出格式
    """
    
    @staticmethod
    def format_text(huangli_data: Dict[str, Any]) -> str:
        """
        将黄历数据格式化为文本输出
        
        Args:
            huangli_data: 黄历数据字典
            
        Returns:
            格式化后的文本字符串
        """
        messages = HuangLiFormatter._get_formatted_message_list(huangli_data)
        return '\n'.join(messages)
    
    @staticmethod
    def _get_formatted_message_list(huangli_data: Dict[str, Any]) -> List[str]:
        """
        生成格式化的消息列表
        
        Args:
            huangli_data: 黄历数据字典
            
        Returns:
            格式化后的消息列表
        """
        messages = []
        
        # 添加标题
        date = huangli_data.get('date', '未知日期')
        messages.append(f"📅 {date} 黄历信息")
        messages.append("=" * 30)
        
        # 1. 基础信息
        if huangli_data.get('basic_info'):
            basic_info = huangli_data['basic_info']
            if basic_info.get('star'):
                messages.append(f"⭐ 今日星宿：{basic_info['star']}")
        
        # 2. 五行信息
        if huangli_data.get('wu_xing'):
            wu_xing = huangli_data['wu_xing']
            if wu_xing:
                messages.append("\n🔥 五行信息")
                if wu_xing.get('year'):
                    messages.append(f"年五行：{wu_xing['year']}")
                if wu_xing.get('month'):
                    messages.append(f"月五行：{wu_xing['month']}")
                if wu_xing.get('day'):
                    messages.append(f"日五行：{wu_xing['day']}")
        
        # 3. 冲合信息
        if huangli_data.get('chong_he'):
            chong_he = huangli_data['chong_he']
            if chong_he.get('info'):
                messages.append("\n⚖️ 冲合信息")
                messages.append(chong_he['info'])
        
        # 4. 三煞方
        if huangli_data.get('san_sha'):
            san_sha = huangli_data['san_sha']
            if san_sha:
                messages.append("\n⚠️ 三煞方位")
                if san_sha.get('year'):
                    messages.append(f"年三煞：{san_sha['year']}")
                if san_sha.get('month'):
                    messages.append(f"月三煞：{san_sha['month']}")
                if san_sha.get('day'):
                    messages.append(f"日三煞：{san_sha['day']}")
        
        # 5. 七煞方
        if huangli_data.get('qi_sha'):
            qi_sha = huangli_data['qi_sha']
            if qi_sha:
                messages.append("\n💀 七煞方位")
                if qi_sha.get('year'):
                    messages.append(f"年七煞：{qi_sha['year']}")
                if qi_sha.get('month'):
                    messages.append(f"月七煞：{qi_sha['month']}")
                if qi_sha.get('day'):
                    messages.append(f"日七煞：{qi_sha['day']}")
        
        # 6. 九星吉凶
        if huangli_data.get('ji_xiong'):
            ji_xiong = huangli_data['ji_xiong']
            if ji_xiong.get('nine_star'):
                messages.append("\n🔮 九星吉凶")
                # 将长文本按行分割，避免消息过长
                nine_star_text = ji_xiong['nine_star']
                for line in nine_star_text.split('。'):
                    if line.strip():
                        messages.append(line.strip() + '。')
        
        # 7. 卦象信息
        if huangli_data.get('gua_xiang'):
            gua_xiang = huangli_data['gua_xiang']
            if gua_xiang.get('info'):
                messages.append("\n🧩 今日卦象")
                messages.append(gua_xiang['info'])
                if gua_xiang.get('description'):
                    messages.append("\n卦象详解：")
                    # 分段显示卦象详解
                    desc_lines = gua_xiang['description'].split('\n')
                    for line in desc_lines:
                        if line.strip():
                            messages.append(line.strip())
        
        # 8. 月令、物候等信息
        if huangli_data.get('yue_ling'):
            yue_ling = huangli_data['yue_ling']
            if yue_ling:
                messages.append("\n🌿 时节信息")
                if yue_ling.get('month'):
                    messages.append(f"月令：{yue_ling['month']}")
                if yue_ling.get('phenology'):
                    messages.append(f"物候：{yue_ling['phenology']}")
                if yue_ling.get('moon_phase'):
                    messages.append(f"月相：{yue_ling['moon_phase']}")
                if yue_ling.get('liu_yao'):
                    messages.append(f"六耀：{yue_ling['liu_yao']}")
                if yue_ling.get('day_lu'):
                    messages.append(f"日禄：{yue_ling['day_lu']}")
        
        # 9. 十二神吉凶
        if huangli_data.get('tian_shen'):
            tian_shen = huangli_data['tian_shen']
            if tian_shen.get('twelve_gods'):
                messages.append("\n👼 十二神吉凶")
                messages.append(tian_shen['twelve_gods'])
        
        # 10. 二十八星宿吉凶
        if huangli_data.get('er_shi_ba_xiu'):
            er_shi_ba_xiu = huangli_data['er_shi_ba_xiu']
            if er_shi_ba_xiu.get('info'):
                messages.append("\n✨ 二十八星宿吉凶")
                messages.append(er_shi_ba_xiu['info'])
        
        # 11. 地母经信息
        if huangli_data.get('di_mu_jing'):
            di_mu_jing = huangli_data['di_mu_jing']
            if di_mu_jing:
                messages.append("\n📜 地母经")
                if di_mu_jing.get('divination'):
                    messages.append("卜曰：")
                    messages.append(di_mu_jing['divination'])
                if di_mu_jing.get('poem'):
                    messages.append("\n诗曰：")
                    # 按行显示诗歌内容
                    poem_lines = di_mu_jing['poem'].split('\n')
                    for line in poem_lines:
                        if line.strip():
                            messages.append(line.strip())
        
        # 检查是否有数据
        if len(messages) <= 2:  # 只有标题和分隔线
            messages.append("\n❌ 未能获取到有效黄历数据")
        
        return messages
    
    @staticmethod
    def create_html_for_image(huangli_data: Dict[str, Any]) -> str:
        """
        创建用于生成图片的HTML内容
        
        Args:
            huangli_data: 黄历数据字典
            
        Returns:
            HTML内容字符串
        """
        date = huangli_data.get('date', '未知日期')
        
        html = f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{date} 黄历信息</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    background-color: #f9f9f9;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    padding: 20px;
                }}
                h1 {{
                    color: #8B4513;
                    text-align: center;
                    border-bottom: 2px solid #8B4513;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                h2 {{
                    color: #8B4513;
                    margin-top: 25px;
                    margin-bottom: 15px;
                    font-size: 1.2em;
                    border-left: 4px solid #8B4513;
                    padding-left: 10px;
                }}
                .section {{
                    margin-bottom: 25px;
                }}
                .info-item {{
                    margin-bottom: 8px;
                }}
                .divider {{
                    border: none;
                    border-top: 1px dashed #ddd;
                    margin: 15px 0;
                }}
                .poem {{
                    font-style: italic;
                    text-align: center;
                    margin: 15px 0;
                    color: #666;
                }}
                .warning {{
                    color: #e74c3c;
                }}
                .success {{
                    color: #27ae60;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{date} 黄历信息</h1>
        '''
        
        # 基础信息
        if huangli_data.get('basic_info') and huangli_data['basic_info'].get('star'):
            html += f'''
                <div class="section">
                    <div class="info-item"><strong>今日星宿：</strong>{huangli_data['basic_info']['star']}</div>
                </div>
            '''
        
        # 五行信息
        if huangli_data.get('wu_xing') and huangli_data['wu_xing']:
            html += '<div class="section"><h2>五行信息</h2>'
            wu_xing = huangli_data['wu_xing']
            if wu_xing.get('year'):
                html += f'<div class="info-item"><strong>年五行：</strong>{wu_xing["year"]}</div>'
            if wu_xing.get('month'):
                html += f'<div class="info-item"><strong>月五行：</strong>{wu_xing["month"]}</div>'
            if wu_xing.get('day'):
                html += f'<div class="info-item"><strong>日五行：</strong>{wu_xing["day"]}</div>'
            html += '</div>'
        
        # 冲合信息
        if huangli_data.get('chong_he') and huangli_data['chong_he'].get('info'):
            html += f'''
                <div class="section">
                    <h2>冲合信息</h2>
                    <div class="info-item">{huangli_data['chong_he']['info']}</div>
                </div>
            '''
        
        # 三煞方
        if huangli_data.get('san_sha') and huangli_data['san_sha']:
            html += '<div class="section"><h2>三煞方位</h2>'
            san_sha = huangli_data['san_sha']
            if san_sha.get('year'):
                html += f'<div class="info-item"><strong>年三煞：</strong>{san_sha["year"]}</div>'
            if san_sha.get('month'):
                html += f'<div class="info-item"><strong>月三煞：</strong>{san_sha["month"]}</div>'
            if san_sha.get('day'):
                html += f'<div class="info-item"><strong>日三煞：</strong>{san_sha["day"]}</div>'
            html += '</div>'
        
        # 卦象信息
        if huangli_data.get('gua_xiang') and huangli_data['gua_xiang'].get('info'):
            html += '<div class="section"><h2>今日卦象</h2>'
            html += f'<div class="info-item">{huangli_data["gua_xiang"]["info"]}</div>'
            if huangli_data['gua_xiang'].get('description'):
                html += '<div class="info-item"><strong>卦象详解：</strong></div>'
                desc_lines = huangli_data['gua_xiang']['description'].split('\n')
                for line in desc_lines:
                    if line.strip():
                        html += f'<div class="info-item">{line.strip()}</div>'
            html += '</div>'
        
        # 地母经信息
        if huangli_data.get('di_mu_jing') and huangli_data['di_mu_jing']:
            html += '<div class="section"><h2>地母经</h2>'
            di_mu_jing = huangli_data['di_mu_jing']
            if di_mu_jing.get('divination'):
                html += '<div class="info-item"><strong>卜曰：</strong></div>'
                html += f'<div class="poem">{di_mu_jing["divination"]}</div>'
            if di_mu_jing.get('poem'):
                html += '<div class="info-item"><strong>诗曰：</strong></div>'
                poem_lines = di_mu_jing['poem'].split('\n')
                for line in poem_lines:
                    if line.strip():
                        html += f'<div class="poem">{line.strip()}</div>'
            html += '</div>'
        
        # 结束HTML
        html += '''
            </div>
        </body>
        </html>
        '''
        
        return html
    
    @staticmethod
    def validate_and_format_data(huangli_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和格式化数据，确保数据结构完整性
        
        Args:
            huangli_data: 原始黄历数据
            
        Returns:
            验证和格式化后的数据
        """
        # 确保所有必需的键存在
        required_keys = ['date', 'basic_info', 'wu_xing', 'chong_he', 
                        'san_sha', 'qi_sha', 'ji_xiong', 'gua_xiang', 
                        'yue_ling', 'tian_shen', 'er_shi_ba_xiu', 'di_mu_jing']
        
        for key in required_keys:
            if key not in huangli_data:
                huangli_data[key] = {}
        
        # 确保date字段有值
        if not huangli_data.get('date'):
            huangli_data['date'] = datetime.now().strftime('%Y-%m-%d')
        
        return huangli_data
