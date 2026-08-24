# 安全说明（Security Policy）

## 数据隐私承诺

本项目是**本地优先**应用，设计上保证你的数据不出本机：

| 数据 | 存储位置 | 是否离开本机 |
| --- | --- | --- |
| API Key 与模型配置 | 项目根目录 `config.json` | ❌ 从不 |
| 简历内容 | 项目根目录 `resumes/` | ❌ 从不 |
| 导出的简历 | `output/` 目录 | ❌ 从不 |

唯一的外部网络连接是**由你主动发起**的、发往你配置的大模型接口（如 DeepSeek / OpenAI）的请求，用于 AI 生成。请求内容仅包含你的简历文本与你自己的 API Key（作为鉴权头），且仅在点击"生成/润色/分析/评分"按钮时发送。

## 上报漏洞

如果你发现安全漏洞（如信息泄露、路径穿越、XSS 等），**请不要公开提交 Issue**。

请通过 GitHub 的 [Private vulnerability reporting](https://github.com/ALEG-1/ai-resume-generator/security/advisories) 功能上报，或在 [Issue](https://github.com/ALEG-1/ai-resume-generator/issues) 中联系维护者。

请提供：
- 漏洞描述与影响
- 复现步骤（含运行环境：系统 / Python 版本）
- 修复建议（如有）

## 使用建议

- **不要**把你的 `config.json` 提交到任何 Git 仓库（本项目的 `.gitignore` 已排除，网页上传不遵守 .gitignore，请勿用网页拖拽上传整个项目文件夹）
- 定期检查 `resumes/` 目录权限，避免在多用户机器上被他人读取
- 如怀疑 API Key 泄露，请立即到模型服务商后台吊销并重新生成

## 支持版本

| 版本 | 支持状态 |
| --- | --- |
| 1.1.x | ✅ 受支持 |
| 1.0.x | ⚠️ 仅安全修复 |
