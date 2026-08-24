<div align="center">

# 📄 AI 求职简历生成器

**零依赖 · 纯 Python 标准库 · 本地运行 · 隐私安全**

一个本地运行的 AI 简历生成网页应用：结构化录入经历 → 粘贴目标岗位 JD → AI 按 JD 关键词重构/润色 → 实时预览 → 一键导出 PDF / Word / Markdown。

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![依赖](https://img.shields.io/badge/依赖-零依赖%20(仅标准库)-green)
![License](https://img.shields.io/badge/License-MIT-blue)
[![CI](https://github.com/ALEG-1/ai-resume-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/ALEG-1/ai-resume-generator/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/ALEG-1/ai-resume-generator?style=social)](https://github.com/ALEG-1/ai-resume-generator)

</div>

## 📌 项目简介

求职季利器：把你的经历结构化录入后，粘贴目标岗位 JD，AI 自动完成「关键词对齐 → 整篇重构 → 模块润色」，实时预览、一键导出——让简历更贴合岗位、更有说服力。

> 📖 文档：🌏 [English](README.en.md) · 📘 [使用教程](docs/usage.md) · 🏗 [架构说明](docs/architecture.md) · 🔌 [API 文档](docs/api.md)

**适合谁**
- 正在求职，想针对不同岗位快速定制简历的人
- 简历写不好、不知道如何量化成果的职场人
- 想用本地免费 AI（Ollama）处理简历、不想把个人信息交给第三方网站的人

**核心理念**
- 🔒 **数据不出本机**：API Key 与简历内容全部本地存储，隐私安全
- ⚡ **零依赖开箱即用**：无需 `pip install`、无需构建前端，双击即跑
- 🎯 **以 JD 为中心**：不是"写一份简历"，而是"为每个目标岗位生成一版"

## ✨ 功能特性

| 功能 | 说明 |
| --- | --- |
| 📚 多份简历管理 | 简历库：按目标岗位保存多份，新建/切换/重命名/复制/删除，自动保存 |
| 📝 结构化录入 | 基本信息、教育、工作、项目、技能、自我评价，条目可增删 |
| ⭐ STAR 引导填写 | 经历按 情境/任务/行动/结果 四格填写素材，AI 一键整合为量化要点 |
| 🔍 JD 关键词分析 | 粘贴岗位描述，AI 提取关键词、给出简历修改建议、估算匹配度 |
| ✨ AI 分步生成整篇 | 按「简介→经历→项目→技能→评价」分步生成（含 few-shot 示例、失败自动重试），**流式输出** |
| 🪄 模块级 AI 润色 | 每个模块/条目单独润色，不满意可反复生成 |
| 📊 AI 简历评分 | 生成后 AI 从招聘方视角打分（完整性/量化/JD 匹配/表达）+ 改进建议 |
| 👀 实时预览 | 左侧编辑右侧即时预览，2 套模板（经典单栏 / 现代双栏） |
| 💾 本地持久化 | 简历保存到本地 `resumes/`（JSON），刷新不丢失 |
| 📤 多格式导出 | Word (.docx) / Markdown，PDF 用浏览器打印 |
| 🔌 多模型支持 | DeepSeek / OpenAI / Kimi / 硅基流动 / Ollama 本地，任意 OpenAI 兼容接口 |
| 🔒 隐私安全 | 全部本地运行，API Key 与简历仅存本机，不上传任何地方 |

## 🖼 界面预览

> 截图占位：将应用启动后的界面截图保存为 `docs/screenshot.png` 即可在此展示。

```
┌─────────────────────────────────────────────────────┐
│ 表单（基本信息 / 经历 / JD）  │   简历实时预览 + 导出  │
│                             │                       │
│  [✨ AI 一键生成整篇]         │  模板切换 / PDF / Word │
└─────────────────────────────────────────────────────┘
```

## 🚀 快速开始

需要 **Python 3.9+**（[下载](https://www.python.org/downloads/)，Windows 安装时勾选 *Add to PATH*）。**无需安装任何第三方包。**

### Windows

双击 `run.bat`，或命令行：

```bash
python -m backend.main
```

### macOS / Linux

```bash
./run.sh
# 或
python3 -m backend.main
```

然后浏览器打开 **http://127.0.0.1:8010**

> 提示：端口被占用时可用 `python -m backend.main 9000` 指定其他端口。

## ⚙️ 配置模型（第一次使用）

点击右上角「⚙️ 设置」，填写 API Key / 接口地址 / 模型名，或点「快速填充」一键切换：

| 服务商 | 接口地址 (base_url) | 模型示例 | 申请 Key |
| --- | --- | --- | --- |
| DeepSeek（默认） | `https://api.deepseek.com/v1` | `deepseek-chat` | [platform.deepseek.com](https://platform.deepseek.com) |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | [platform.openai.com](https://platform.openai.com) |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` | [siliconflow.cn](https://siliconflow.cn) |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | [platform.moonshot.cn](https://platform.moonshot.cn) |
| Ollama（免费本地） | `http://localhost:11434/v1` | `qwen2.5:7b` | 无需 Key，`ollama pull qwen2.5:7b` 后选此项 |

配置保存在项目根目录 `config.json`（已加入 `.gitignore`，参考格式见 `config.example.json`）。

## 📝 使用流程

1. 左侧「📚 简历库」新建一份简历（建议按目标岗位命名，如"投字节-后端"），填写基本信息与各段经历
2. 粘贴目标岗位 JD → 点「🔍 AI 分析关键词」，查看匹配度与修改建议
3. 经历不会写？展开条目的「⭐ STAR 引导」，按 情境/任务/行动/结果 填素材 → 「✨ 整合为要点」
4. 点「✨ AI 一键生成整篇」，按 5 步流式生成并自动填入；不满意的模块点「✨ AI 润色」单独重写
5. 点「📊 AI 评分」从招聘方视角打分，按改进建议迭代
6. 右侧切换模板 → 「🖨 打印 / PDF」导出 PDF（对话框选"另存为 PDF"），或「⬇ Word / Markdown」
7. 针对下一个岗位：新建一份简历，重复 2~6（不同版本互不干扰，自动保存）

## 🧪 测试

自带 22 项单元测试（含自动启动 HTTP 服务的端到端测试），零依赖直接运行：

```bash
python -m unittest discover -s tests -v
```

GitHub Actions 已配置 CI（`.github/workflows/ci.yml`），推送后在 Python 3.9 ~ 3.13 全版本自动执行。

## 📁 项目结构

```
.
├── backend/                 # 本地 HTTP 服务（仅 Python 标准库）
│   ├── main.py              # 路由：静态页面 / 生成(SSE) / 简历库 / 设置 / 导出
│   ├── llm.py               # OpenAI 兼容流式调用（urllib，含 JSON 自动重试）
│   ├── prompts.py           # 简历专家提示词模板（few-shot 示例、分步生成、STAR、评分）
│   ├── export.py            # 导出调度：Markdown / Word
│   ├── docx_py.py           # Word 导出（python-docx，若已安装）
│   └── docx_min.py          # Word 导出兜底（纯标准库 zipfile）
├── frontend/                # 纯前端（无需构建）
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   └── test_core.py         # unittest 测试套件
├── docs/                    # 使用教程 / 架构说明 / API 文档
├── .github/workflows/ci.yml # GitHub Actions 持续集成
├── config.example.json      # 配置格式示例
├── output/                  # 导出文件目录（运行时自动创建，不入库）
├── resumes/                 # 简历库数据（运行时自动创建，含个人数据，不入库）
├── run.bat / run.sh         # 一键启动脚本
└── LICENSE                  # MIT 许可证
```

## 🛠 技术说明

- **零依赖设计**：后端全部使用 Python 标准库——`http.server` 提供服务、`urllib` 调用大模型、`zipfile` 手写 OOXML 文档生成，开箱即用、免安装。
- **SSE 流式输出**：AI 生成结果通过 Server-Sent Events 实时推送，前端边生成边展示。
- **分步生成 + 自动重试**：整篇生成按模块分步调用，每步独立更稳定；JSON 输出解析失败时带错误反馈自动重试一次。
- **few-shot 提示词**：系统提示词内置优秀要点示例，显著提升输出质量。
- **Word 导出双实现**：安装了 `python-docx` 用规范排版，未安装自动降级到内置轻量生成器，两种路径均产出合规 .docx。
- **前端零构建**：原生 HTML/CSS/JS，无打包步骤，浏览器直接运行。

## ❓ 常见问题

- **AI 按钮报"未配置 API Key"** → 点右上角「⚙️ 设置」填写并保存。
- **导出 PDF** → 点「🖨 打印 / PDF」，打印对话框选择"另存为 PDF"，会自动隐藏表单只打印简历。
- **换浏览器/清缓存数据还在吗** → 简历库数据存在本地 `resumes/` 目录（JSON），换浏览器依然在；浏览器仅记录当前打开哪份。
- **端口被占用** → `python -m backend.main 其他端口号`。
- **Word 排版想更规范** → `pip install python-docx` 后重启即可（不装也能导出）。

## 🤝 贡献

欢迎提交 [Issue](https://github.com/ALEG-1/ai-resume-generator/issues) 与 [Pull Request](https://github.com/ALEG-1/ai-resume-generator/pulls)！

计划中的方向：更多简历模板、按公司批量定制版本、ATS 友好导出、中英文简历、前端单元测试。

## 📄 License

[MIT](LICENSE) © 2025 ALEG-1
