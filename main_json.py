import requests
import sys
import os
import json
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone

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

# --- AI 精炼翻译函数 ---
def call_ai_for_json_refinement(items_batch):
    """
    分批发送新闻条目给 AI，要求返回精炼后的英文标题和 Markdown 正文。
    """
    API_URL = "https://genai.thisisray.workers.dev/"
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！")
        return None

    system_prompt = """You are an expert news editor and translator. You will receive a list of news items (title and content).
Your task:
1. Understand the core message of each item.
2. Write a catchy, refined English title.
3. Write a concise, refined English body text using your own words. Do not just translate word-for-word. Summarize and re-paragraph as needed to make it professional and clear.
4. Format the English body text in Markdown.
5. Return the results ONLY as a valid JSON array of objects.
Each object MUST have these keys:
   - "title_zh": The original Chinese title (as provided).
   - "title_en": The refined English title.
   - "content_en": The refined English body text in Markdown.
Do not include any markdown code blocks, explanations, or extra text. Only the raw JSON string."""

    # 只发送 AI 需要处理的字段 (title_zh, content_zh)
    input_data = json.dumps([{"title_zh": item["title_zh"], "content_zh": item["content_zh"]} for item in items_batch], ensure_ascii=False)
    payload = { "input": input_data, "system": system_prompt, "temperature": 0.3, "model": "gemini-2.5-flash" }
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}" }

    try:
        # 拼接完整路径以避免 404，类似于 AnkiPal 的处理方式
        full_url = f"{API_URL.rstrip('/')}/api/v1/completion"
        response = requests.post(full_url, json=payload, headers=headers, timeout=300)
        response.raise_for_status()

        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()

        return json.loads(raw_text)
    except Exception as e:
        print(f"AI 翻译或解析 JSON 失败: {e}")
        return None

# --- 主处理逻辑 ---
def generate_json_directly(url, output_filename):
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
        for section in soup.find_all('section', attrs={'data-ifanr-layout': 'morning-section'}):
            section.decompose()

        # 2. 提取新闻条目
        content_area = soup.find('div', class_='entry-content') or soup.body
        if not content_area:
            print("找不到内容区域。")
            return

        headings = content_area.find_all('h3')
        extracted_items = []

        for h3 in headings:
            title_zh = h3.get_text(strip=True)
            if not title_zh or any(k in title_zh for k in ["周末也值得一看", "是周末啊"]):
                continue

            # 提取正文文本和图片
            body_texts = []
            image_url = ""
            for sibling in h3.find_next_siblings():
                if sibling.name == 'h3':
                    break

                # 寻找第一张图片
                if not image_url:
                    img_tag = sibling.find('img') if hasattr(sibling, 'find') else None
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']

                # 提取纯文本
                if sibling.name == 'p':
                    txt = sibling.get_text(strip=True)
                    if txt:
                        body_texts.append(txt)

            extracted_items.append({
                "title_zh": title_zh,
                "content_zh": "\n\n".join(body_texts),
                "image_url": image_url
            })

        print(f"共提取到 {len(extracted_items)} 条新闻。")

        # 3. 分批 AI 翻译 (每 3 条一组)
        final_data = []
        batch_size = 3
        for i in range(0, len(extracted_items), batch_size):
            batch = extracted_items[i:i+batch_size]
            print(f"正在处理第 {i//batch_size + 1} 批 (共 {len(batch)} 条)...")
            res_list = call_ai_for_json_refinement(batch)

            if res_list and isinstance(res_list, list):
                # 将 AI 返回的结果与原始数据（含图片）合并
                for original, ai_res in zip(batch, res_list):
                    final_data.append({
                        "title_zh": original["title_zh"],
                        "content_zh": original["content_zh"],
                        "image_url": original["image_url"],
                        "title_en": ai_res.get("title_en", ""),
                        "content_en": ai_res.get("content_en", "")
                    })
            else:
                print("本批次 AI 处理失败。")

        # 4. 保存 JSON
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        print(f"JSON 已成功保存至: {output_filename}")

    except Exception as e:
        print(f"生成过程出错: {e}")

if __name__ == '__main__':
    feed_url = "https://www.ifanr.com/feed"
    target_url = get_latest_morning_post_link(feed_url)
    if target_url:
        generate_json_directly(target_url, "DailyNews.json")
    else:
        sys.exit(1)
