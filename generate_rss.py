import sys
from bs4 import BeautifulSoup, CData
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timezone, timedelta

def create_rss_en_only(html_filepath, output_filepath):
    """
    解析爱范儿早报的HTML文件，生成一个RSS文件。
    RSS条目标题为中文，正文内容只保留英文。

    Args:
        html_filepath (str): 输入的HTML文件路径。
        output_filepath (str): 输出的RSS XML文件路径。
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

    # --- 2. 提取并填充 Channel 全局信息 ---
    channel_title = soup.find('title').get_text(strip=True) if soup.find('title') else "爱范儿早报"
    channel_link = soup.find('link', rel='canonical')['href'] if soup.find('link', rel='canonical') else "https://www.ifanr.com"
    channel_description = soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "每日科技早报"
    
    # 解析相对时间 "昨天 HH:MM" 为 RFC 822 格式的绝对日期
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
                pass # 时间格式不对，则忽略
    
    if not pub_date_str: # 如果解析失败，使用当前时间作为备用
        pub_date_str = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')

    SubElement(channel, 'title').text = channel_title
    SubElement(channel, 'link').text = channel_link
    SubElement(channel, 'description').text = channel_description
    SubElement(channel, 'language').text = 'zh-CN'
    SubElement(channel, 'lastBuildDate').text = pub_date_str

    # --- 3. 查找所有新闻条目并处理 ---
    content_div = soup.find('div', id='entry-content')
    if not content_div:
        print("错误：在HTML中找不到 'entry-content' 容器。")
        return

    headings = content_div.find_all('h3')

    for h3 in headings:
        item_title = h3.get_text(strip=True)
        
        # 过滤掉非新闻标题
        if not item_title or "周末也值得一看的新闻" in item_title or "是周末啊" in item_title:
            continue
            
        item = SubElement(channel, 'item')
        # 标题使用原文中文标题
        SubElement(item, 'title').text = item_title
        SubElement(item, 'link').text = channel_link
        SubElement(item, 'pubDate').text = pub_date_str
        SubElement(item, 'guid', isPermaLink="false").text = f"{channel_link}#{item_title.replace(' ', '-')}"

        # 提取从当前 h3 到下一个 h3 之间的所有内容作为正文
        content_html = []
        for sibling in h3.find_next_siblings():
            if sibling.name == 'h3':
                break  # 到达下一个条目，停止

            # 核心修改：查找双语标签，并只保留英文内容
            if hasattr(sibling, 'find_all'):
                lang_tags = sibling.find_all(attrs={'ondblclick': True})
                for tag in lang_tags:
                    en_span = tag.find('span', class_='lang-en')
                    if en_span:
                        en_text = en_span.get_text(" ", strip=True)
                        # 创建一个新的p标签，只包含英文文本
                        new_p = soup.new_tag('p')
                        if tag.has_attr('style'):
                            new_p['style'] = tag['style'] # 保留原有样式
                        new_p.string = en_text
                        # 用新的英文p标签替换掉原来的双语标签
                        tag.replace_with(new_p)

            content_html.append(str(sibling))
        
        description_text = "".join(content_html)
        description = SubElement(item, 'description')
        # 使用 CDATA 来包裹 HTML 内容
        description.text = CData(description_text)

    # --- 4. 格式化并写入文件 ---
    xml_str = tostring(rss, 'utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)
        
    print(f"🎉 成功生成 RSS 文件 (仅英文正文): '{output_filepath}'")

# --- 脚本执行入口 ---
if __name__ == "__main__":
    # 定义输入和输出文件名
    # 将你的HTML文件命名为 "ifanr_zaobao.html"
    input_html_file = "ifanr_zaobao.html" 
    output_rss_file = "ifanr_zaobao_rss.xml"
    
    # 执行转换
    create_rss_en_only(input_html_file, output_rss_file)
