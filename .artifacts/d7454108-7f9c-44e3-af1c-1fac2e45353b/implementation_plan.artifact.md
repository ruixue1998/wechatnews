# 实施计划 - 迁移至 Gemini 官方 API 协议 (AnkiPal 风格)

本计划将 `main_json.py` 的 AI 调用逻辑彻底重构，使其与 `AnkiPal` App 的 Gemini 调用方式完全保持一致。这意味着我们将弃用之前的自定义 Worker 协议，转而使用 Google Gemini 的官方标准格式。

## 用户审核事项
> [!IMPORTANT]
> **API 密钥位置**：按照官方协议，API Key 将作为 URL 参数 `?key=...` 传递，不再放在 Header 中。
> **模型名称**：我将模型设定为 `gemini-1.5-flash`（这是目前的主流稳定版本）。

## 拟议更改

### [MODIFY] [main_json.py](file:///C:/Users/Ray/AndroidStudioProjects/wechatnews/main_json.py)

#### 1. 变量与 URL 构造
- 将 `API_URL` 保留为基准域名 `https://genai.thisisray.workers.dev/`。
- 定义 `MODEL = "gemini-1.5-flash"`。
- 在请求时构造动态 URL：`f"{API_URL.rstrip('/')}/v1beta/models/{MODEL}:generateContent?key={AUTH_TOKEN}"`。

#### 2. 请求体 (Payload) 转换
- 模仿 `AnkiPal` 的做法，将 `system_prompt` 和 `input_data` 合并为一个大的文本块。
- 构造官方 JSON 结构：
  ```json
  {
    "contents": [{
      "parts": [{ "text": "SYSTEM_INSTRUCTION + INPUT_DATA" }]
    }]
  }
  ```

#### 3. 响应解析逻辑
- 响应解析从直接读取 `response.text` 改为逐级提取：`json_res['candidates'][0]['content']['parts'][0]['text']`。
- 保持原有的 JSON 提取与清洗逻辑（`extractJson` 和 `sanitizeJson`），以处理 AI 可能返回的 Markdown 标记。

---

### [MODIFY] [.github/workflows/rss_update.yml](file:///C:/Users/Ray/AndroidStudioProjects/wechatnews/.github/workflows/rss_update.yml)
- 无需结构性修改，只需确保环境变量 `AI_AUTH_TOKEN` 继续正常传递即可。

## 验证计划

### 自动化测试
- 在本地模拟官方响应格式进行单元测试。
- 运行脚本，验证是否能正确获取 200 成功状态码。

### 手动验证
- 检查 `DailyNews.json` 是否包含双语标题、图片 URL 和 Markdown 排版的正文。
