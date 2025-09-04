import requests
import sys
import os # <--- 1. 导入 os 库
from bs4 import BeautifulSoup
import copy
import feedparser

# --- 【新增】从 RSS Feed 获取最新链接的函数 ---
def get_latest_morning_post_link(feed_url):
    # ... 函数内容保持不变 ...
    print(f"正在从 RSS feed 获取最新的早报链接: {feed_url}")
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if "早报" in entry.title:
                print(f"成功找到最新早报: '{entry.title}'")
                return entry.link
        print("错误: 在 RSS feed 中未找到标题包含“早报”的文章。")
        return None
    except Exception as e:
        print(f"错误: 解析 RSS feed 时发生异常: {e}")
        return None

# --- AI 翻译函数 ---
def call_ai_for_html_translation(html_content_snippet):
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    # <--- 2. 从环境变量安全地读取密钥 ---
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！请在 GitHub Secrets 中配置。")
        sys.exit(1) # 如果没有密钥，则直接退出

    # ... 函数其余部分保持不变 ...
    print("正在准备调用 AI API 以进行 P 标签内容翻译...")
    system_prompt = """You are an expert HTML translator. You will receive an HTML snippet containing several <p> tags. 
    Your task is to translate ONLY the Chinese text content within each <p> tag to English.
    Crucially, you MUST preserve the original HTML structure and ALL attributes (like class, data-pair-id, style, etc.) of every tag exactly as they were.
    Do not add any new tags, attributes, or explanations. Only return the modified HTML snippet.
    """
    payload = { "input": html_content_snippet, "system": system_prompt, "temperature": 0.3, "model": "gemini-1.5-flash" }
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}" }
    try:
        print("正在向 AI API 发送翻译请求 (超时设置为 300 秒)...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        ai_response_html = response.text.strip()
        print("AI API 成功返回了翻译后的 HTML 片段。")
        return ai_response_html
    except requests.exceptions.Timeout:
        print("错误: AI API 请求超时（超过300秒）。")
        return None
    except requests.exceptions.RequestException as e:
        print(f"错误: AI API 请求失败。详情: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print("服务器响应:", e.response.text)
        return None


# --- 交互式 AI 翻译函数 ---
def call_ai_for_interactive_translation(html_content_snippet):
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    # <--- 2. 从环境变量安全地读取密钥 ---
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！请在 GitHub Secrets 中配置。")
        sys.exit(1)
        
    # ... 函数其余部分保持不变 ...
    print("正在准备调用 AI API 以进行交互式翻译 (支持双击和嵌套标签)...")
    system_prompt = """You are an expert HTML translator who creates interactive, bilingual text.
You will receive an HTML snippet containing <p> and <li> tags with Chinese text.
Your task is to perform the following transformation for EACH tag:
1.  Translate the Chinese text content into English, ensuring that any nested HTML tags (like <strong>, <em>, <a>) are preserved in their correct positions within the translated text.
2.  Wrap the original Chinese content (including its nested tags) in a span: `<span class="lang-zh" style="display:none;">...</span>`.
3.  Wrap the newly translated English content (including its preserved nested tags) in another span: `<span class="lang-en" style="display:inline;">...</span>`.
4.  Place BOTH of these spans inside the original parent tag (e.g., <p> or <li>).
5.  Add an `ondblclick="toggleLang(this)"` attribute to the parent tag (<p> or <li>) to enable language switching on double-click.
6.  You MUST preserve all original attributes of the parent tag (like class, style, etc.) and merge them with the new `ondblclick` attribute.
7.  Do not add any other explanations, comments, or script tags. Only return the modified HTML snippet.

Example Input:
<p style="font-size: 80%;">这是一段<strong>非常重要</strong>的文本。</p>

Example Output:
<p style="font-size: 80%;" ondblclick="toggleLang(this)"><span class="lang-en" style="display:inline;">This is a piece of <strong>very important</strong> text.</span><span class="lang-zh" style="display:none;">这是一段<strong>非常重要</strong>的文本。</span></p>
"""
    payload = { "input": html_content_snippet, "system": system_prompt, "temperature": 0.3, "model": "gemini-1.5-flash" }
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}" }
    try:
        print("正在向 AI API 发送交互式翻译请求 (超时设置为 300 秒)...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        ai_response_html = response.text.strip()
        print("AI API 成功返回了交互式翻译的 HTML 片段。")
        return ai_response_html
    except requests.exceptions.Timeout:
        print("错误: AI API 请求超时（超过300秒）。")
        return None
    except requests.exceptions.RequestException as e:
        print(f"错误: AI API 请求失败。详情: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print("服务器响应:", e.response.text)
        return None

# --- process_and_style_tags 函数保持不变 ---
def process_and_style_tags(soup):
    # ... 函数内容保持不变 ...
    exclusion_zones = set()
    trigger_tags = soup.find_all('p', class_='h3-p-pair')
    for tag in trigger_tags:
        if tag.parent and tag.parent.parent and tag.parent.parent.parent:
            ggparent = tag.parent.parent.parent
            exclusion_zones.add(ggparent)
    print(f"识别到 {len(exclusion_zones)} 个豁免区（基于 p.h3-p-pair 的曾祖父标签）。")
    tags_to_process = soup.find_all(['p', 'li'])
    count = 0
    for tag in tags_to_process:
        if tag.name == 'p' and tag.has_attr('class') and 'h3-p-pair' in tag['class']:
            continue
        is_in_exclusion_zone = False
        for parent in tag.parents:
            if parent in exclusion_zones:
                is_in_exclusion_zone = True
                break
        if is_in_exclusion_zone:
            continue
        for content in tag.contents[:]:
            if isinstance(content, str) and content.strip():
                span_tag = soup.new_tag('span')
                content.replace_with(span_tag)
                span_tag.string = content
        style_parts = []
        if not (tag.has_attr('style') and 'font-size' in tag['style']):
            style_parts.append('font-size: 80%;letter-spacing: 0rem;    line-height: 1.5rem;')
        if tag.name == 'p' and not (tag.has_attr('style') and 'margin-bottom' in tag['style']):
             style_parts.append('margin-bottom: 5%;')
        if style_parts:
            final_style = ' '.join(style_parts)
            if tag.has_attr('style'):
                tag['style'] += ' ' + final_style
            else:
                tag['style'] = final_style
        count += 1
    return count

# --- Main Function ---
# <--- 3. 修改函数，使其接受文件名作为参数 ---
def get_full_page_and_save(url, output_filename):
    # ... 函数内容大部分不变，只修改文件保存部分 ...
    headers = { 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1' }
    
    # 删除了创建目录的逻辑，因为我们将直接保存在根目录
    full_save_path = output_filename
    
    print(f"正在尝试从 URL 获取内容: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        html_content = response.text
        
        # ... [此处省略所有 soup 处理逻辑，它们保持不变] ...
        
        # --- 省略的 soup 处理逻辑，从 print("正在解析 HTML...") 到 print("--- 交互式翻译流程结束 ---\n") ---
        print("正在解析 HTML...")
        soup = BeautifulSoup(html_content, 'html.parser')
        # ...
        # (所有对 soup 的操作都和原脚本一样)
        # ...
        print("--- 交互式翻译流程结束 ---\n")
        
        # 13. Save Final HTML
        cleaned_html = soup.prettify()
        with open(full_save_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_html)
        print(f"成功！已将最终的网页内容保存到文件: '{full_save_path}'")
    except Exception as e:
        print(f"错误：在处理过程中发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# --- 主执行块 ---
if __name__ == '__main__':
    ifanr_feed_url = "https://www.ifanr.com/feed"
    target_url = get_latest_morning_post_link(ifanr_feed_url)

    if target_url:
        print(f"获取到的最新文章 URL 为: {target_url}")
        
        # <--- 4. 定义输出文件名 ---
        output_file = "DailyNews.html"
        
        # 调用主处理函数
        get_full_page_and_save(target_url, output_file)
    else:
        print("由于未能从 RSS feed 获取到有效的文章链接，脚本将退出。")
        sys.exit(1)
