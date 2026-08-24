# 贡献指南

感谢你考虑为本项目贡献代码！在提交 PR 之前，请先阅读以下约定。

## 项目定位（红线）

本项目是一个**零依赖、本地运行**的简历生成工具。以下约束不可破坏：

- **运行时零第三方依赖**：后端只能使用 Python 标准库（`http.server`、`urllib`、`zipfile` 等）。
  新功能应优先用标准库实现；确需第三方库时，必须先开 Issue 讨论，且只能作为**可选增强**（如 `python-docx`），缺失时自动降级。
- **前端零构建**：原生 HTML/CSS/JS，不引入打包器、框架或 npm 依赖。
- **隐私优先**：所有用户数据（API Key、简历内容）只存本机，不得上传任何第三方服务。

## 开发环境

- Python 3.9+（无需安装任何包）
- 启动：`python -m backend.main`
- 测试：`python -m unittest discover -s tests -v`（必须全绿才能提交）

## 代码规范

- **Python**：遵循 [PEP 8](https://peps.python.org/pep-0008/)，行宽不超过 119 字符；缩进 4 空格。
- **前端**：HTML/CSS/JS 缩进 2 空格；JS 使用 `"use strict"` 与分号风格。
- **编码**：全部文件 UTF-8，行尾 LF（见 `.editorconfig` / `.gitattributes`）。
- **注释**：中文注释，说明"为什么"而不是"是什么"。
- **提示词**：新增 AI 功能时，提示词放在 `backend/prompts.py`，遵循既有风格（系统提示词 + 消息构建函数分离）。

## 测试要求

- 任何后端改动都必须补充/更新 `tests/test_core.py` 中的用例。
- 测试只能使用标准库（unittest），不得引入 pytest 等依赖。
- 提交前运行完整测试套件并确保通过。

## 提交规范

- 提交信息使用 Conventional Commits 风格：
  - `feat: 新功能`
  - `fix: 修复`
  - `docs: 文档`
  - `style: 格式（不影响逻辑）`
  - `test: 测试`
  - `refactor: 重构`
- 一个提交只做一件事，保持 diff 聚焦。

## 提交流程

1. Fork 本仓库并创建特性分支：`git checkout -b feat/xxx`
2. 完成改动，补测试，跑通全部测试
3. 提交并推送：`git push origin feat/xxx`
4. 发起 Pull Request，在描述中说明改动动机与验证方式

## 问题反馈

遇到 Bug 或有功能建议，欢迎开 [Issue](https://github.com/ALEG-1/ai-resume-generator/issues)，请尽量包含：
- 复现步骤
- 期望行为与实际行为
- 运行环境（系统 / Python 版本）
