import requests
import sys
import os
from bs4 import BeautifulSoup
import copy
import feedparser

# --- 从 RSS Feed 获取最新链接的函数 ---
def get_latest_morning_post_link(feed_url):
    """
    从指定的 RSS feed 中解析并获取标题包含“早报”的最新一篇文章的链接。
    """
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
    """
    Calls an AI API to translate the text content within a snippet of HTML <p> tags.
    """
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    # 从环境变量安全地读取密钥
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
    """
    调用 AI API，将 HTML 片段中的中文翻译成英文，并嵌入可双击切换的结构。
    """
    API_URL = "https://genai-api.thisisray.workers.dev/api/v1/completion"
    # 从环境变量安全地读取密钥
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
3.  Wrap the newly translated English content (including its preserved nested tags) in another span: `<span class="lang-en" style="display:inline; letter-spacing: .001rem; font-size: .875rem;line-height: 1.375rem;">...</span>`. Note the added letter-spacing for better readability.
4.  Place BOTH of these spans inside the original parent tag (e.g., <p> or <li>).
5.  Add an `ondblclick="toggleLang(this)"` attribute to the parent tag (<p> or <li>) to enable language switching on double-click.
6.  You MUST preserve all original attributes of the parent tag (like class, style, etc.) and merge them with the new `ondblclick` attribute.
7.  Do not add any other explanations, comments, or script tags. Only return the modified HTML snippet.

Example Input:
<p style="font-size: 80%;">这是一段<strong>非常重要</strong>的文本。</p>

Example Output:
<p style="font-size: 80%;" ondblclick="toggleLang(this)"><span class="lang-en" style="display:inline; letter-spacing: .001rem; font-size: .875rem;line-height: 1.375rem;">This is a piece of <strong>very important</strong> text.</span><span class="lang-zh" style="display:none;">这是一段<strong>非常重要</strong>的文本。</span></p>
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

# --- 样式处理函数 (已优化) ---
def process_and_style_tags(soup):
    """
    Wraps text in <span>, shrinks font size, and adds margins with advanced exclusion rules.
    NOTE: This should run AFTER interactive translation to avoid breaking HTML structure.
    """
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
        # 如果标签已经包含交互式翻译的span，则跳过
        if tag.find('span', class_='lang-en', recursive=False):
            continue
            
        if tag.name == 'p' and tag.has_attr('class') and 'h3-p-pair' in tag['class']:
            continue
            
        is_in_exclusion_zone = False
        for parent in tag.parents:
            if parent in exclusion_zones:
                is_in_exclusion_zone = True
                break
        if is_in_exclusion_zone:
            continue
            
        # This logic is for styling non-translated, simple text paragraphs.
        for content in tag.contents[:]:
            if isinstance(content, str) and content.strip():
                span_tag = soup.new_tag('span')
                content.replace_with(span_tag)
                span_tag.string = content
                
        # 【优化】应用更美观的样式，包含 letter-spacing
        style_parts = []
        if not (tag.has_attr('style') and 'font-size' in tag['style']):
            style_parts.append('font-size: 80%;')
        if not (tag.has_attr('style') and 'letter-spacing' in tag['style']):
            style_parts.append('letter-spacing: .001rem; font-size: .875rem;line-height: 1.375rem;')
        if not (tag.has_attr('style') and 'line-height' in tag['style']):
            style_parts.append('line-height: 1.6rem;')

        if tag.name == 'p' and not (tag.has_attr('style') and 'margin-bottom' in tag['style']):
             style_parts.append('margin-bottom: 5%;')

        if style_parts:
            final_style = ' '.join(style_parts)
            if tag.has_attr('style'):
                tag['style'] = final_style + tag['style'] # Prepend to prioritize
            else:
                tag['style'] = final_style
            count += 1
    return count

# --- 主处理函数 (翻译逻辑已优化) ---
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

        # 【核心修复】处理 <noscript> 标签并清理延迟加载占位符
        print("正在处理 <noscript> 标签，将其内容释放出来...")
        for tag in soup.find_all('noscript'):
            tag.unwrap()
        print("正在移除多余的延迟加载占位图片...")
        for img in soup.find_all('img', attrs={'data-cfsrc': True}):
            img.decompose()
        
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

        # 2. Content Matching and Marking
        print("正在使用内容匹配逻辑为 p 和 h3 标签添加标志...")
        main_content_area = soup.find('div', class_='entry-content') or soup.body
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
                        # Do not remove h3_tag from list to allow multiple matches if necessary
                        # h3_list.remove(h3_tag)
                        break
            print(f"内容匹配完成，共成功标记了 {pair_counter} 对 p/h3 元素。")

        # 3. AI Translation Workflow (for Paired Tags)
        print("\n--- 开始 AI 翻译流程 (仅限配对标签) ---")
        original_p_tags_to_translate = soup.find_all('p', class_='h3-p-pair')
        if original_p_tags_to_translate:
            snippet_container = soup.new_tag('div')
            for p_tag in original_p_tags_to_translate:
                snippet_container.append(copy.copy(p_tag))
            translated_snippet_html = call_ai_for_html_translation(str(snippet_container))
            if translated_snippet_html:
                translated_soup = BeautifulSoup(translated_snippet_html, 'html.parser')
                translated_p_tags = translated_soup.find_all('p')
                if len(original_p_tags_to_translate) == len(translated_p_tags):
                    print("标签数量匹配。正在将翻译内容替换回原文件...")
                    for original_tag, translated_tag in zip(original_p_tags_to_translate, translated_p_tags):
                        original_tag.replace_with(translated_tag)
                    print("内容替换成功！")
                else:
                    print(f"警告：AI 返回的 P 标签数量 ({len(translated_p_tags)}) 与发送的数量 ({len(original_p_tags_to_translate)}) 不符。已跳过替换。")
            else:
                print("AI 翻译失败，将跳过替换步骤。")
        else:
            print("未找到需要翻译的 P 标签，跳过 AI 翻译流程。")
        print("--- AI 翻译流程结束 ---\n")

        # 4. Apply Custom Styles to Paired <p> Tags
        print("正在为匹配的 p 标签应用自定义样式...")
        style_string = "line-height: 1.3rem; margin-bottom: 1.2rem; font-family: PingFangSC-Regular,'Helvetica Neue',Helvetica,Arial,sans-serif; font-size: .875rem; color: #121212; letter-spacing: .01875rem; text-align: justify;"
        for p_tag in soup.find_all('p', class_='h3-p-pair'):
            p_tag['style'] = style_string
        
        # ... Other styling steps (5, 6, 8, 9, 10) remain the same ...
        print("正在为匹配的p标签，移除父元素样式并修改曾祖父元素的样式...")
        for p_tag in soup.find_all('p', class_='h3-p-pair'):
            parent = p_tag.find_parent()
            if parent and parent.get('style') == 'margin-bottom: 0; width: 88%;':
                del parent['style']
            if parent and parent.parent and parent.parent.parent:
                ggparent = parent.parent.parent
                if ggparent and ggparent.get('style') == 'padding: 0 14px;':
                    ggparent['style'] = "padding:0 0 30px 0"
        
        print("正在修改匹配p标签父元素的同级元素的样式...")
        for p_tag in soup.find_all('p', class_='h3-p-pair'):
            parent = p_tag.find_parent()
            if not parent: continue
            sibling = parent.find_previous_sibling()
            while sibling and not hasattr(sibling, 'get'):
                sibling = sibling.find_previous_sibling()
            if sibling and sibling.get('style') == 'float: left; margin-right: 6px; margin-bottom: 0; width: 30px;':
                sibling['style'] = 'line-height: 1.36rem;float: left; margin-right: 2px; margin-bottom: 0; width: 30px;'

        # 7. Inject JavaScript for Interactivity
        print("正在注入点击滚动和双击翻译功能的 JavaScript...")
        js_code = """
        document.addEventListener('DOMContentLoaded', function() {
            const pairedElements = document.querySelectorAll('.h3-p-pair');
            pairedElements.forEach(element => {
                element.style.cursor = 'pointer';
                element.title = 'Click to scroll to the corresponding tag';
                element.addEventListener('click', function(e) {
                    if (e.target.closest('[ondblclick*="toggleLang"]')) {
                       return;
                    }
                    const pairId = this.dataset.pairId;
                    if (!pairId) return;
                    const siblings = document.querySelectorAll(`[data-pair-id='${pairId}']`);
                    for (const sibling of siblings) {
                        if (sibling !== this) {
                            sibling.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            break;
                        }
                    }
                });
            });
        });
        function toggleLang(element) {
            let spanEn = null;
            let spanZh = null;
            for (const child of element.children) {
                if (child.classList.contains('lang-en')) {
                    spanEn = child;
                } else if (child.classList.contains('lang-zh')) {
                    spanZh = child;
                }
            }
            if (spanEn && spanZh) {
                if (spanEn.style.display === 'none') {
                    spanEn.style.display = 'inline';
                    spanZh.style.display = 'none';
                } else {
                    spanEn.style.display = 'none';
                    spanZh.style.display = 'inline';
                }
            } else {
                console.warn('Could not find both .lang-en and .lang-zh direct child spans for toggling.', element);
            }
        }
        """
        body_tag = soup.find('body')
        if body_tag:
            script_tag = soup.new_tag('script')
            script_tag.string = js_code
            body_tag.append(script_tag)
            print("JavaScript 注入成功！")
        
        print("正在为匹配的p标签的祖父标签添加负外边距...")
        processed_grandparents = set()
        for p_tag in soup.find_all('p', class_='h3-p-pair'):
            if p_tag.parent and p_tag.parent.parent:
                grandparent = p_tag.parent.parent
                if grandparent.sourceline is not None and (grandparent.name, grandparent.sourceline) not in processed_grandparents:
                    grandparent['style'] = "margin:0 0.1rem 0 -0.5rem"
                    processed_grandparents.add((grandparent.name, grandparent.sourceline))
        
        print("正在为匹配的p标签的曾祖父元素后插入分割线...")
        processed_ggparents = set()
        for p_tag in soup.find_all('p', class_='h3-p-pair'):
            if p_tag.parent and p_tag.parent.parent and p_tag.parent.parent.parent:
                ggparent = p_tag.parent.parent.parent
                if ggparent.sourceline is not None and (ggparent.name, ggparent.sourceline) not in processed_ggparents:
                    hr_tag = soup.new_tag('hr', style="width:20%;")
                    ggparent.insert_after(hr_tag)
                    processed_ggparents.add((ggparent.name, ggparent.sourceline))

        print("正在为主要内容区域添加内边距...")
        entry_content_tag = soup.find(class_='entry-content clearfix')
        if entry_content_tag:
            entry_content_tag['style'] = 'padding: 0 2rem;'

        # 11. 【全新翻译逻辑】为页面所有主要内容提供交互式翻译
        print("\n--- 开始对主要内容进行全面的交互式翻译 ---")
        content_area = soup.find('div', class_='entry-content') or soup.body
        tags_for_translation = content_area.find_all(['p', 'li'], recursive=True)
        
        # 过滤掉已经处理过的配对 P 标签和没有文本的标签
        unique_tags = []
        for tag in tags_for_translation:
            if 'h3-p-pair' in tag.get('class', []):
                continue
            if not tag.get_text(strip=True):
                continue
            unique_tags.append(tag)

        if unique_tags:
            print(f"提取了 {len(unique_tags)} 个 p/li 标签用于交互式翻译。")
            
            # 分批处理以避免请求体过大
            batch_size = 20 
            for i in range(0, len(unique_tags), batch_size):
                batch_tags = unique_tags[i:i+batch_size]
                print(f"\n--- 正在处理批次 {i//batch_size + 1} (共 {len(batch_tags)} 个标签) ---")
                
                snippet_div = soup.new_tag('div')
                for tag in batch_tags:
                    snippet_div.append(copy.copy(tag))

                interactive_html = call_ai_for_interactive_translation(str(snippet_div))
                
                if interactive_html:
                    interactive_soup = BeautifulSoup(interactive_html, 'html.parser')
                    translated_tags = interactive_soup.find_all(['p', 'li'])
                    
                    if len(batch_tags) == len(translated_tags):
                        print(f"标签数量匹配。正在将交互式翻译内容替换回原文件...")
                        for original_tag, translated_tag in zip(batch_tags, translated_tags):
                            original_tag.replace_with(translated_tag)
                        print("本批次交互式内容替换成功！")
                    else:
                        print(f"警告：AI 返回的 p/li 标签数量 ({len(translated_tags)}) 与发送的数量 ({len(batch_tags)}) 不符。已跳过本批次替换。")
                else:
                    print("AI 交互式翻译失败，将跳过本批次的替换步骤。")
        else:
            print("在主要内容区域未找到需要翻译的 p 或 li 标签。")
        print("--- 所有段落的交互式翻译流程结束 ---\n")

        # 12. 【新顺序】Process and Style Tags (Font Shrinking, Margins)
        print("正在处理并缩小未被翻译的 <p> 和 <li> 标签的字体并添加外边距...")
        processed_count = process_and_style_tags(soup)
        print(f"字体和外边距处理完成。共为 {processed_count} 个符合条件的标签添加了样式。")

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
        output_file = "DailyNews.html"
        get_full_page_and_save(target_url, output_file)
    else:
        print("由于未能从 RSS feed 获取到有效的文章链接，脚本将退出。")
        sys.exit(1)
