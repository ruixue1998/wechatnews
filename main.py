import requests
import sys
import os
from bs4 import BeautifulSoup
import copy
import feedparser

# --- 从 RSS Feed 获取最新链接的函数 ---
def get_latest_morning_post_link(feed_url):
    # ... (此函数保持不变) ...
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


# --- AI Translation Function (Original) ---
def call_ai_for_html_translation(html_content_snippet):
    # ... (此函数保持不变) ...
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！请在 GitHub Secrets 中配置。")
        sys.exit(1)
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

# --- AI 翻译函数 (交互式) ---
def call_ai_for_interactive_translation(html_content_snippet):
    # ... (此函数保持不变) ...
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    AUTH_TOKEN = os.getenv('AI_AUTH_TOKEN')
    if not AUTH_TOKEN:
        print("错误: 环境变量 AI_AUTH_TOKEN 未设置！请在 GitHub Secrets 中配置。")
        sys.exit(1)
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

# --- 样式处理函数 ---
def process_and_style_tags(soup):
    # ... (此函数保持不变) ...
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

# --- 主处理函数 ---
def get_full_page_and_save(url, output_filename):
    """
    Full workflow: Fetch, clean, match content, translate, and inject interactivity.
    """
    headers = { 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1' }
    full_save_path = output_filename
    print(f"正在尝试从 URL 获取内容: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        html_content = response.text
        print("正在解析 HTML...")
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Standard Cleanup
        print("正在移除 JavaScript, 样式和指定元素...")
        for s in soup(['script', 'style']): s.decompose()
        for tag in soup.find_all(True):
            for attr in list(tag.attrs):
                if attr.lower().startswith('on'): del tag[attr]
        elements_to_remove = {"class": ["global-navigator", "weixin-share-tip hide", "simple header clearfix", "jiong__article--small", "article-sns-tool", "popup-download-wrapper", "article-info__author", "article-footer"], "id": ["stick-header"]}
        for class_name in elements_to_remove["class"]:
            for element in soup.find_all(class_=class_name): element.decompose()
        for id_name in elements_to_remove["id"]:
            element = soup.find(id=id_name)
            if element: element.decompose()
        for h1_tag in soup.find_all('h1'): h1_tag.decompose()
        print("清理完成。")
        
        # 【新增】修复 CDN 懒加载图片的步骤
        print("正在检查并修复 CDN 懒加载（lazy-loaded）的图片...")
        for noscript_tag in soup.find_all('noscript'):
            noscript_tag.decompose()
        lazy_images = soup.find_all('img', attrs={'data-cfsrc': True})
        if lazy_images:
            print(f"找到 {len(lazy_images)} 个懒加载图片，正在进行修复...")
            for img in lazy_images:
                real_src = img['data-cfsrc']
                img['src'] = real_src
                if 'style' in img.attrs:
                    del img['style']
                del img['data-cfsrc']
            print("所有懒加载图片修复完成。")
        else:
            print("未在本页面找到 CDN 懒加载的图片。")

        # 2. Content Matching and Marking
        # ... (后续所有处理逻辑保持不变) ...
        print("正在使用内容匹配逻辑为 p 和 h3 标签添加标志...")
        main_content_area = soup.find('h3').parent if soup.find('h3') else soup.body
        if main_content_area:
            p_list = main_content_area.find_all('p')
            h3_list = list(main_content_area.find_all('h3'))
            pair_counter = 0
            for p_tag in p_list:
                p_text = p_tag.get_text(strip=True)
                if not p_text or len(p_text) < 4: continue
                for h3_tag in h3_list:
                    h3_text = h3_tag.get_text(strip=True)
                    if p_text.lower() in h3_text.lower():
                        pair_counter += 1
                        common_class_name = 'h3-p-pair'
                        unique_identifier = f'pair-{pair_counter}'
                        for tag in [p_tag, h3_tag]:
                            if 'class' not in tag.attrs: tag['class'] = []
                            tag['class'].append(common_class_name)
                            tag['data-pair-id'] = unique_identifier
                        h3_list.remove(h3_tag)
                        break
            print(f"内容匹配完成，共成功标记了 {pair_counter} 对 p/h3 元素。")

        # ... [此处省略所有其他未变的处理步骤 3 到 13，以保持简洁] ...
        
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
    # ... (此部分保持不变) ...
    ifanr_feed_url = "https://www.ifanr.com/feed"
    target_url = get_latest_morning_post_link(ifanr_feed_url)
    if target_url:
        print(f"获取到的最新文章 URL 为: {target_url}")
        output_file = "DailyNews.html"
        get_full_page_and_save(target_url, output_file)
    else:
        print("由于未能从 RSS feed 获取到有效的文章链接，脚本将退出。")
        sys.exit(1)
