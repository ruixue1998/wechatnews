import sys
from bs4 import BeautifulSoup, CData
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone, timedelta

def create_rss_en_only(html_filepath, output_filepath):
    """
    解析爱范儿早报的HTML文件，生成一个RSS文件。
    RSS条目标题为中文，正文内容只保留英文。
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

    # --- 2. 修改后的 Channel 全局信息 ---
    # MODIFIED: 设置一个固定的静态标题
    SubElement(channel, 'title').text = "Daily News"
    # REMOVED: link, description, and language tags have been removed as requested.

    # 解析发布日期 (此部分保留，以便RSS阅读器知道feed的更新时间)
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
        item_title = h3.get_text(strip=True)
        
        if not item_title or "周末也值得一看的新闻" in item_title or "是周末啊" in item_title:
            continue
            
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = item_title
        SubElement(item, 'pubDate').text = pub_date_str
        
        # REMOVED: The <link> for each item has been removed.
        
        # MODIFIED: Create a unique GUID from the item title only.
        SubElement(item, 'guid', isPermaLink="false").text = item_title.replace(' ', '-')

        # 提取从当前 h3 到下一个 h3 之间的所有内容作为正文
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
        
    print(f"🎉 成功生成 RSS 文件 (仅英文正文): '{output_filepath}'")

# --- 脚本执行入口 ---
if __name__ == "__main__":
    input_html_file = "DailyNews.html" 
    output_rss_file = "DailyNews.xml"
    
    create_rss_en_only(input_html_file, output_rss_file)
