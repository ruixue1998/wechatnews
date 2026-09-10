import requests
import sys
import os
import json
import feedparser
from bs4 import BeautifulSoup, CData
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone, timedelta

# --- 获取最新链接 ---
def get_latest_morning_post_link(feed_url):
    print(f"正在从 RSS feed 获取最新的早报链接: {feed_url}")
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if "早报" in entry.title:
                print(f"成功找到最新早报: '{entry.title}'")
                return entry.link
        print("未找到包含“早报”的文章。")
        return None
    except Exception as e:
        print(f"解析 RSS 失败: {e}")
        return None

# --- AI 批量翻译函数 ---
def call_ai_for_rss_translation(items_batch):
    """
    分批发送新闻条目给 AI，要求返回 JSON 格式的翻译结果。
    """
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！")
        return None

    system_prompt = """You are an expert news translator. You will receive a list of news items.
Your task:
1. Translate the Chinese title to English.
2. Translate the Chinese body text to English, while ABSOLUTELY PRESERVING all <img> tags and their attributes.
3. Return the results ONLY as a valid JSON array of objects.
Each object MUST have these keys:
   - "title_zh": The original Chinese title.
   - "title_en": The translated English title.
   - "content_en": The translated English body HTML (preserving <img> tags).
Do not include any markdown code blocks, explanations, or extra text. Only the raw JSON string."""

    # 将 items_batch 转换为字符串发送
    input_data = json.dumps(items_batch, ensure_ascii=False)
    payload = { "input": input_data, "system": system_prompt, "temperature": 0.2, "model": "gemini-2.5-flash" }
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}" }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=300)
        response.raise_for_status()

        # 尝试清理可能存在的 markdown 代码块包裹
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()

        return json.loads(raw_text)
    except Exception as e:
        print(f"AI 翻译或解析 JSON 失败: {e}")
        if 'response' in locals() and response is not None:
            print("AI 原始响应:", response.text)
        return None

# --- 主处理逻辑 ---
def generate_rss_directly(url, output_filename):
    headers = { 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1' }

    print(f"正在获取内容: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 深度清洗
        for s in soup(['script', 'style']): s.decompose()
        for tag in soup.find_all('noscript'): tag.unwrap()
        for img in soup.find_all('img', attrs={'data-cfsrc': True}): img.decompose()
        # 移除早报特定的分割栏 section (如：大公司、数字潮汐等图标栏)
        for section in soup.find_all('section', attrs={'data-ifanr-layout': 'morning-section'}):
            section.decompose()

        # 2. 提取新闻条目
        content_area = soup.find('div', class_='entry-content') or soup.body
        if not content_area:
            print("找不到内容区域。")
            return

        headings = content_area.find_all('h3')
        items_to_translate = []

        for h3 in headings:
            title_zh = h3.get_text(strip=True)
            if not title_zh or any(k in title_zh for k in ["周末也值得一看", "是周末啊"]):
                continue

            # 提取该 h3 到下一个 h3 之间的内容
            body_parts = []
            for sibling in h3.find_next_siblings():
                if sibling.name == 'h3':
                    break
                # 只保留 p 标签和包含图片的标签
                if sibling.name == 'p' or sibling.find('img'):
                    body_parts.append(str(sibling))

            items_to_translate.append({
                "title_zh": title_zh,
                "content_zh": "".join(body_parts)
            })

        print(f"共提取到 {len(items_to_translate)} 条新闻。")

        # 3. 分批 AI 翻译 (每 3 条一组)
        translated_items = []
        batch_size = 3
        for i in range(0, len(items_to_translate), batch_size):
            batch = items_to_translate[i:i+batch_size]
            print(f"正在翻译第 {i//batch_size + 1} 批 (共 {len(batch)} 条)...")
            res = call_ai_for_rss_translation(batch)
            if res and isinstance(res, list):
                translated_items.extend(res)
            else:
                print("本批次翻译失败，跳过。")

        # 4. 构造 RSS XML
        rss = Element('rss', version='2.0', attrib={'xmlns:content': 'http://purl.org/rss/1.0/modules/content/'})
        channel = SubElement(rss, 'channel')
        SubElement(channel, 'title').text = "APPSO News"

        pub_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')
        SubElement(channel, 'lastBuildDate').text = pub_date

        for item_data in translated_items:
            # 确保获取到所有必要的字段
            t_zh = item_data.get('title_zh', 'No Title')
            t_en = item_data.get('title_en', '')
            c_en = item_data.get('content_en', '')

            item_node = SubElement(channel, 'item')
            # 标题格式：[中文] English
            SubElement(item_node, 'title').text = f"[{t_zh}] {t_en}"
            SubElement(item_node, 'pubDate').text = pub_date
            SubElement(item_node, 'guid', isPermaLink="false").text = t_zh.replace(' ', '-')

            desc = SubElement(item_node, 'description')
            desc.text = CData(c_en)

        # 5. 保存文件
        xml_str = tostring(rss, 'utf-8')
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_str)

        print(f"RSS 已成功保存至: {output_filename}")

    except Exception as e:
        print(f"生成 RSS 过程中出错: {e}")

if __name__ == '__main__':
    feed_url = "https://www.ifanr.com/feed"
    target_url = get_latest_morning_post_link(feed_url)
    if target_url:
        generate_rss_directly(target_url, "DailyNews_Bilingual.xml")
    else:
        sys.exit(1)
