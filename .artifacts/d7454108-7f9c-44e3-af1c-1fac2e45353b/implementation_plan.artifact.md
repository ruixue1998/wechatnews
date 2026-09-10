# 实施计划 - 转向 JSON 结构化数据 (精简版)

该计划将修改新闻处理流程，从生成 RSS XML 转向生成一个结构化的 JSON 文件。该文件将包含中文原文、精炼后的英文翻译以及配图链接。

## 用户审核事项
> [!IMPORTANT]
> **数据格式**：最终生成的 `DailyNews_Bilingual.json` 将包含以下字段：
> - `title_zh`: 原始中文标题
> - `content_zh`: 原始中文正文（纯文本）
> - `image_url`: 文章的第一张图片链接（若无则为空）
> - `title_en`: AI 重新理解并精炼后的英文标题
> - `content_en`: AI 重新分段排版、精炼后的英文正文（Markdown 格式）

> [!NOTE]
> **AI 提示词策略**：我们将明确要求 AI 不要字对字翻译，而是根据理解进行“精炼”和“重排”。

## 拟议更改

### [NEW] [main_json.py](file:///C:/Users/Ray/AndroidStudioProjects/wechatnews/main_json.py)

#### 1. 数据提取升级
- **标题**：提取 `<h3>`。
- **正文**：提取段落中的纯文本。
- **图片**：在当前新闻块中寻找第一个 `<img>` 标签，并提取其 `src` 地址。

#### 2. AI 交互逻辑 (分批处理)
- **输入**：发送 `title_zh` 和 `content_zh`。
- **Prompt 修改**：
    - 要求 AI 使用自己的语言精炼回复。
    - 要求 AI 重新分段。
    - 标题要吸引人（Refined Title）。
    - 格式要求：Markdown。
- **输出**：返回 `title_en` 和 `content_en`。

#### 3. JSON 持久化
- 使用 `json.dump` 将结果保存为 `DailyNews_Bilingual.json`。

---

### [MODIFY] [rss_update.yml](file:///C:/Users/Ray/AndroidStudioProjects/wechatnews/.github/workflows/rss_update.yml)
- **同步重命名**：将工作流中的脚本调用指向 `main_json.py`。
- **监控文件**：修改 `file_pattern` 为 `DailyNews_Bilingual.json`。

## 验证计划

### 自动化测试
- **脚本运行**：在本地执行 `python main_json.py`，验证 JSON 是否生成。
- **内容校验**：
    - 检查 `image_url` 是否为有效的 URL 或空字符串。
    - 检查 `content_en` 是否为 Markdown 格式。
    - 检查 JSON 语法。

### 手动验证
- 抽查几条新闻，对比原文和 AI 精炼后的内容。
