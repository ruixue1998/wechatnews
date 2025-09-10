import sys
from bs4 import BeautifulSoup, CData
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone, timedelta
from deep_translator import GoogleTranslator # <-- 新增：导入翻译器

def create_rss_with_live_translation(html_filepath, output_filepath):
    """
    解析任何爱范儿早报的HTML文件，动态翻译H3标题后，生成一个RSS文件。
    正文内容只保留英文。
    """
    try:
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{html_filepath}'")
        sys.exit(1)

    soup = BeautifulSoup(html_content, 'lxml')

    # --- 新增：初始化翻译器和缓存 ---
    # 为了效率，我们只创建一次翻译器实例
    # 并创建一个缓存字典来存储已经翻译过的标题
    translator = GoogleTranslator(source='zh-CN', target='en')
    translation_cache = {}

    # --- 1. 创建RSS基础结构 ---
    rss = Element('rss', version='2.0', attrib={'xmlns:content': 'http://purl.org/rss/1.0/modules/content/'})
    channel = SubElement(rss, 'channel')

    # --- 2. Channel 全局信息 ---
    SubElement(channel, 'title').text = "Daily News"
    
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

    # --- 3. 查找所有新闻条目并处理 ---
    content_div = soup.find('div', id='entry-content')
    if not content_div:
        print("错误：在HTML中找不到 'entry-content' 容器。")
        return

    headings = content_div.find_all('h3')

    for h3 in headings:
        original_title = h3.get_text(strip=True)
        
        if not original_title or "周末也值得一看的新闻" in original_title or "是周末啊" in original_title:
            continue
        
        # --- 修改：动态翻译标题 ---
        item_title = ""
        # 检查缓存中是否已有翻译
        if original_title in translation_cache:
            item_title = translation_cache[original_title]
        else:
            try:
                # 如果不在缓存中，则调用API进行翻译
                translated_text = translator.translate(original_title)
                item_title = translated_text
                # 将新翻译的结果存入缓存
                translation_cache[original_title] = item_title
                print(f"翻译: '{original_title}' -> '{item_title}'")
            except Exception as e:
                # 如果翻译失败（例如网络问题），则使用原标题并打印警告
                print(f"警告：翻译标题 '{original_title}' 失败。错误: {e}. 将使用原标题。")
                item_title = original_title

        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = item_title
        SubElement(item, 'pubDate').text = pub_date_str
        SubElement(item, 'guid', isPermaLink="false").text = item_title.replace(' ', '-')

        # 提取正文的逻辑保持不变
        content_html = []
        for sibling in h3.find_next_siblings():
            if sibling.name == 'h3':
                break

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

    # --- 4. 格式化并写入文件 ---
    xml_str = tostring(rss, 'utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)
        
    print(f"\n🎉 成功生成通用的 RSS 文件 (标题已自动翻译): '{output_filepath}'")

# --- 脚本执行入口 ---
if __name__ == "__main__":
    # 您可以每天将新的HTML文件命名为 "DailyNews.html"
    input_html_file = "DailyNews.html" 
    output_rss_file = "DailyNews_Auto_Translated.xml"
    
    create_rss_with_live_translation(input_html_file, output_rss_file)
