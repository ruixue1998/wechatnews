# Walkthrough - 迁移至 Gemini 官方 API 协议

我已经成功将 `main_json.py` 的 AI 调用逻辑重构，使其与 `AnkiPal` App 保持高度一致。

## 核心变更

### 1. 协议标准化 (AnkiPal 风格)
- **URL 格式**：现在使用标准的 Gemini 路径：`{API_URL}/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}`。
- **Payload 结构**：弃用了自定义 JSON，转而使用 Google 官方的 `contents` 嵌套结构。
- **鉴权移位**：API Key 不再放在 Header，而是按照官方规范作为 URL 参数传递。

### 2. 提示词合并
- **逻辑优化**：模仿 `AnkiPal` 的 `buildPrompt` 逻辑，将 `system_prompt` 和输入数据合并为一个整体文本块发送给模型。这有助于模型在统一的上下文中理解任务要求。

### 3. 响应解析适配
- **解析层级**：更新了解析逻辑，从官方返回的 `candidates[0].content.parts[0].text` 中精准提取 AI 精炼后的 JSON 字符串。

## 最终效果
- **一致性**：你的 Python 脚本现在像 App 一样在“说话”。
- **兼容性**：只要你的 Worker 能够正确转发/模拟官方 Gemini 路径，脚本就能完美运行。

> [!TIP]
> 以后如果你想更换模型（例如换成 `gemini-2.0-flash`），只需修改脚本中的 `MODEL` 变量即可。
