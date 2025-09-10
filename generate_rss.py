import sys
import os
import requests
from bs4 import BeautifulSoup, CData
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone, timedelta

# --- 新增: AI 翻译函数 (为纯文本标题优化) ---
def translate_titles_with_ai(titles_list):
    """
    调用 AI API，将一个中文标题列表批量翻译成英文标题列表。
    """
    # API 和认证信息与您提供的示例保持一致
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！")
        sys.exit(1)

    # 使用特殊分隔符连接所有标题，以便 AI 一次性处理
    # 这样比为每个标题单独请求一次 API 更高效
    separator = "|||"
    combined_titles = separator.join(titles_list)

    print(f"正在准备调用 AI API 翻译 {len(titles_list)} 个标题...")
    
    system_prompt = f"""You are an expert translator. You will receive a list of news headlines in Chinese, joined by a specific separator ('{separator}').
Your task is to:
1. Translate each headline accurately into English.
2. Return the translated headlines, also joined by the exact same separator ('{separator}').
3. Do NOT add any numbering, explanations, or any text other than the translated headlines and the separator.
4. The number of headlines you return must exactly match the number of headlines you receive.

Example Input:
苹果发布新款 MacBook Pro|||特斯拉宣布下调 Model 3 价格

Example Output:
Apple Releases New MacBook Pro|||Tesla Announces Price Cut for Model 3
"""
    
    payload = {
        "input": combined_titles,
        "system": system_prompt,
        "temperature": 0.5,
        "model": "gemini-pro" # 使用一个能力更强的模型以保证翻译质量
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    try:
        print("正在向 AI API 发送标题翻译请求...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        
        ai_response_text = response.text.strip()
        translated_titles = ai_response_text.split(separator)
        
        # 校验返回的标题数量是否与发送的一致
        if len(translated_titles) != len(titles_list):
            print("错误: AI 返回的翻译标题数量与原文不匹配！")
            print(f"原文数量: {len(titles_list)}, 翻译后数量: {len(translated_titles)}")
            print("AI 返回内容:", ai_response_text)
            return None

        print("✅ AI 成功返回了翻译后的标题。")
        return translated_titles
        
    except requests.exceptions.Timeout:
        print("错误: AI API 请求超时（超过300秒）。")
        return None
    except requests.exceptions.RequestException as e:
        print(f"错误: AI API 请求失败。详情: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print("服务器响应:", e.response.text)
        return None

def create_rss_en_only(html_filepath, output_filepath):
    """
    解析爱范儿早报的HTML文件，生成一个RSS文件。
    RSS条目标题由 AI 翻译成英文，正文内容只保留英文。
    """
    try:
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{html_filepath}'")
        sys.exit(1)

    soup = BeautifulSoup(html_content, 'lxml')
    content_div = soup.find('div', id='entry-content')
    if not content_div:
        print("错误：在HTML中找不到 'entry-content' 容器。")
        return

    # --- 1. 提取所有中文标题 ---
    headings = content_div.find_all('h3')
    chinese_titles = []
    valid_headings = []
    for h3 in headings:
        title_text = h3.get_text(strip=True)
        # 过滤掉无效或推广性质的标题
        if title_text and "周末也值得一看的新闻" not in title_text and "是周末啊" not in title_text:
            chinese_titles.append(title_text)
            valid_headings.append(h3)

    if not chinese_titles:
        print("警告：在 HTML 中没有找到有效的新闻标题。")
        return

    # --- 2. 调用 AI 翻译所有标题 ---
    english_titles = translate_titles_with_ai(chinese_titles)
    if not english_titles:
        print("由于 AI 翻译失败，无法继续生成 RSS 文件。")
        return
        
    # 创建一个从中文标题到英文标题的映射，方便后续查找
    title_translation_map = dict(zip(chinese_titles, english_titles))

    # --- 3. 创建RSS基础结构 ---
    rss = Element('rss', version='2.0', attrib={'xmlns:content': 'http://purl.org/rss/1.0/modules/content/'})
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = "Daily News (AI Translated)"
    
    # 解析发布日期
    pub_date_str = ""
    time_tag = soup.select_one('.article-info__category time')
    if time_tag and "昨天" in time_tag.get_text(strip=True):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        time_parts = time_tag.get_text(strip=True).split()
        if len(time_parts) == 2:
            try:
                hour, minute = map(int, time_parts[1].split(':'))
                pub_date_obj = yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
                pub_date_str = pub_date_obj.strftime('%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                pass
    
    if not pub_date_str:
        pub_date_str = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')

    SubElement(channel, 'lastBuildDate').text = pub_date_str

    # --- 4. 遍历有效标题并生成 RSS Item ---
    for h3 in valid_headings:
        original_title = h3.get_text(strip=True)
        translated_title = title_translation_map.get(original_title)
        
        if not translated_title:
            print(f"警告: 找不到标题 '{original_title}' 对应的翻译，跳过此条目。")
            continue
            
        item = SubElement(channel, 'item')
        
        # 使用翻译后的英文标题
        SubElement(item, 'title').text = translated_title
        SubElement(item, 'pubDate').text = pub_date_str
        
        # 使用英文标题生成 GUID
        SubElement(item, 'guid', isPermaLink="false").text = translated_title.replace(' ', '-')

        # 提取从当前 h3 到下一个 h3 之间的所有内容作为正文
        content_html = []
        for sibling in h3.find_next_siblings():
            if sibling.name == 'h3':
                break

            # 这部分逻辑保持不变，依然是提取双语内容中的英文部分
            if hasattr(sibling, 'find_all'):
                lang_tags = sibling.find_all(attrs={'ondblclick': True})
                for tag in lang_tags:
                    en_span = tag.find('span', class_='lang-en')
                    if en_span:
                        en_text = en_span.get_text(" ", strip=True)
                        new_p = soup.new_tag('p')
                        if tag.has_attr('style'):
                            new_p['style'] = tag['style']
                        new_p.string = en_text
                        tag.replace_with(new_p)

            content_html.append(str(sibling))
        
        description_text = "".join(content_html)
        description = SubElement(item, 'description')
        description.text = CData(description_text)

    # --- 5. 格式化并写入文件 ---
    xml_str = tostring(rss, 'utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)
        
    print(f"🎉 成功生成 RSS 文件 (AI 翻译标题 + 仅英文正文): '{output_filepath}'")

# --- 脚本执行入口 ---
if __name__ == "__main__":
    # 在运行前，请确保您已经设置了环境变量 AI_AUTH_TOKEN
    # 例如: export AI_AUTH_TOKEN="your_secret_token"
    if not os.getenv('AI_AUTH_TOKEN'):
         print("重要提示：请先设置环境变量 'AI_AUTH_TOKEN' 再运行此脚本。")
    else:
        input_html_file = "DailyNews.html" 
        output_rss_file = "DailyNews_AI_Translated.xml" # 使用新文件名以避免覆盖旧文件
        
        create_rss_en_only(input_html_file, output_rss_file)
