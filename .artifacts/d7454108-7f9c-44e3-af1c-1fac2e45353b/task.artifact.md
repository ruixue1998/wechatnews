# 任务列表 - 迁移至 Gemini 官方 API 协议

- [x] 重构 `main_json.py` 中的 AI 调用逻辑
    - [x] 更新 URL 构造方式（拼接 `v1beta/models/...`）
    - [x] 重构请求体 Payload 为官方 `contents` 结构
    - [x] 将鉴权从 Header 移至 URL 参数 `key`
    - [x] 更新响应解析逻辑，适配 `candidates` 嵌套结构
- [x] 同步代码至 GitHub 仓库
- [x] 验证生成的 `DailyNews.json` 是否符合预期
- [x] 编写 Walkthrough 总结
