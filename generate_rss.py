import sys
import os
import requests # 新增：用于调用 AI API
from bs4 import BeautifulSoup, CData
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone, timedelta

# --- 【新增】AI 翻译函数，专门用于翻译标题 ---
def call_ai_for_title_translation(chinese_title):
    """
    调用 AI API 将中文标题（纯文本）翻译成英文。
    """
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    # 从环境变量安全地读取密钥
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！")
        return None # 翻译失败，返回 None

    print(f"正在为标题调用 AI 翻译: '{chinese_title}'")
    
    # 一个专门为翻译标题优化的提示
    system_prompt = """You are an expert translator. Translate the following Chinese headline into English.
    Return ONLY the translated English text, without any introductory phrases, explanations, or quotation marks.
    """
    
    payload = { "input": chinese_title, "system": system_prompt, "temperature": 0.3, "model": "gemini-2.5-flash" }
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}" }
    
    try:
        # 为 API 调用设置一个合理的超时时间，例如 60 秒
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status() # 如果请求失败 (例如 4xx 或 5xx 错误), 则会抛出异常
        translated_text = response.text.strip()
        print(f"  -> 翻译成功: '{translated_text}'")
        return translated_text
    except requests.exceptions.Timeout:
        print(f"  -> 错误: AI API 请求超时。")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  -> 错误: AI API 请求失败。详情: {e}")
        return None

# --- 主函数（已修改） ---
def create_rss_en_only(html_filepath, output_filepath):
    """
    解析爱范儿早报的HTML文件，生成一个RSS文件。
    【已修改】RSS条目标题会先通过AI翻译成英文，正文内容只保留英文。
    """
    try:
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{html_filepath}'")
        sys.exit(1)

    soup = BeautifulSoup(html_content, 'lxml')

    # --- 1. 创建RSS基础结构 ---
    rss = Element('rss', version='2.0', attrib={'xmlns:content': 'http://purl.org/rss/1.0/modules/content/'})
    channel = SubElement(rss, 'channel')

    # --- 2. Channel 全局信息 ---
    SubElement(channel, 'title').text = "Daily News" 
    
    pub_date_str = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')
    # 尝试从HTML中解析更精确的日期
    time_tag = soup.select_one('.article-info__category time')
    if time_tag:
        time_text = time_tag.get_text(strip=True)
        try:
            # 假设格式是 "昨天 HH:MM"
            if "昨天" in time_text:
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                time_parts = time_text.split()[-1].split(':')
                hour, minute = int(time_parts[0]), int(time_parts[1])
                pub_date_obj = yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
                pub_date_str = pub_date_obj.strftime('%a, %d %b %Y %H:%M:%S %z')
        except (ValueError, IndexError):
            pass # 如果解析失败，则使用默认的当前时间

    SubElement(channel, 'lastBuildDate').text = pub_date_str

    # --- 3. 查找所有新闻条目并处理 ---
    content_div = soup.find('div', class_='entry-content') # 使用 class 选择器可能更通用
    if not content_div:
        print("错误：在HTML中找不到 class='entry-content' 的容器。")
        return

    headings = content_div.find_all('h3')

    print("\n--- 开始处理新闻条目并翻译标题 ---")
    for h3 in headings:
        original_title_cn = h3.get_text(strip=True)
        
        if not original_title_cn or "周末也值得一看的新闻" in original_title_cn or "是周末啊" in original_title_cn:
            continue

        # 【核心修改】调用 AI 翻译标题
        item_title = call_ai_for_title_translation(original_title_cn)
        
        # 如果翻译失败，则回退到原始中文标题并打印警告
        if not item_title:
            print(f"  -> 警告: 标题翻译失败，将使用原始中文标题: '{original_title_cn}'")
            item_title = original_title_cn
            
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = item_title
        SubElement(item, 'pubDate').text = pub_date_str
        SubElement(item, 'guid', isPermaLink="false").text = item_title.replace(' ', '-')

        # 提取从当前 h3 到下一个 h3 之间的所有内容作为正文
        content_html = []
        for sibling in h3.find_next_siblings():
            if sibling.name == 'h3':
                break

            # 这部分逻辑保持不变，用于提取双语HTML中的英文部分
            if hasattr(sibling, 'find_all'):
                # 创建一个副本进行操作，避免修改原始的 soup 对象
                temp_sibling = BeautifulSoup(str(sibling), 'lxml').body.next
                
                lang_tags = temp_sibling.find_all(attrs={'ondblclick': True})
                for tag in lang_tags:
                    en_span = tag.find('span', class_='lang-en')
                    if en_span:
                        en_text = en_span.get_text(" ", strip=True)
                        new_p = soup.new_tag('p')
                        if tag.has_attr('style'):
                            new_p['style'] = tag['style']
                        new_p.string = en_text
                        tag.replace_with(new_p)
                
                content_html.append(str(temp_sibling))
            else:
                 content_html.append(str(sibling))
        
        description_text = "".join(content_html)
        description = SubElement(item, 'description')
        description.text = CData(description_text)

    # --- 4. 格式化并写入文件 ---
    xml_str = tostring(rss, 'utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)
        
    print(f"\n🎉 成功生成 RSS 文件 (标题已翻译，正文仅英文): '{output_filepath}'")

# --- 脚本执行入口 ---
if __name__ == "__main__":
    input_html_file = "DailyNews.html" 
    output_rss_file = "DailyNews.xml"
    
    # 确保 AI 认证令牌存在
    if not os.getenv('AI_AUTH_TOKEN'):
        print("致命错误: 环境变量 AI_AUTH_TOKEN 未设置。请先设置此变量再运行脚本。")
        sys.exit(1)

    create_rss_en_only(input_html_file, output_rss_file)
