<div align="center">

# 📄 AI Resume Generator for Job Seekers

**Zero-dependency · Pure Python stdlib · Local-first · Privacy-safe**

A local web app that generates tailored resumes with AI: enter your experience → paste the target job description (JD) → AI rewrites/polishes your resume around the JD's keywords → live preview → one-click export to PDF / Word / Markdown.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Deps](https://img.shields.io/badge/Dependencies-Zero%20(stdlib%20only)-green)
![License](https://img.shields.io/badge/License-MIT-blue)
[![CI](https://github.com/ALEG-1/ai-resume-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/ALEG-1/ai-resume-generator/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/ALEG-1/ai-resume-generator?style=social)](https://github.com/ALEG-1/ai-resume-generator)

</div>

> 🇨🇳 中文文档：[README.md](README.md) · [使用教程](docs/usage.md) · [架构说明](docs/architecture.md) · [API 文档](docs/api.md)

## 📌 About

Structured input of your background → paste a target JD → AI does "keyword alignment → full rewrite → module polishing" automatically, with live preview and one-click export — so every resume is tailored to a specific job and far more convincing.

**Who it's for**
- Job seekers who want to quickly customize a resume for each application
- People who struggle to quantify their achievements
- People who want to process resumes with a local, free AI (Ollama) and never hand personal data to third-party websites

**Core principles**
- 🔒 **Data stays on your machine**: API key and resume content are stored locally only
- ⚡ **Zero setup**: no `pip install`, no frontend build — double-click and run
- 🎯 **JD-centered**: not "write one resume", but "generate a version for every target job"

## ✨ Features

| Feature | Description |
| --- | --- |
| 📚 Resume library | Save multiple resumes by target job; create / switch / rename / duplicate / delete with auto-save |
| 📝 Structured input | Basic info, education, work, projects, skills, self-assessment; add/remove entries |
| ⭐ STAR-guided writing | Fill in Situation / Task / Action / Result per entry, AI merges them into quantified bullets |
| 🔍 JD keyword analysis | Paste the JD; AI extracts keywords, gives editing suggestions and a match score |
| ✨ Step-by-step AI generation | Generates summary → experience → projects → skills → self-assessment (few-shot examples, auto-retry), **streamed live** |
| 🪄 Module-level polish | Re-polish any single module/entry until you're happy |
| 📊 AI resume scoring | Hiring-manager perspective: overall score + 4 dimensions + strengths + improvement tips |
| 👀 Live preview | Edit on the left, preview on the right; 2 templates (classic single-column / modern two-column) |
| 💾 Local persistence | Resumes saved to local `resumes/` (JSON), survive refresh |
| 📤 Multi-format export | Word (.docx) / Markdown; PDF via browser print |
| 🔌 Multiple models | DeepSeek / OpenAI / Kimi / SiliconFlow / local Ollama — any OpenAI-compatible API |
| 🔒 Privacy | Everything runs locally; API key and resumes never leave your machine |

## 🚀 Quick Start

Requires **Python 3.9+** ([download](https://www.python.org/downloads/)). **No third-party packages needed.**

### Windows

Double-click `run.bat`, or:

```bash
python -m backend.main
```

### macOS / Linux

```bash
./run.sh
# or
python3 -m backend.main
```

Then open **http://127.0.0.1:8010**

> Port in use? `python -m backend.main 9000` to pick another port.

## ⚙️ Configure a model (first run)

Click **⚙️ Settings** (top right) and fill in the API key / base URL / model, or use the quick-fill buttons:

| Provider | base_url | Example model | Get a key |
| --- | --- | --- | --- |
| DeepSeek (default) | `https://api.deepseek.com/v1` | `deepseek-chat` | [platform.deepseek.com](https://platform.deepseek.com) |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | [platform.openai.com](https://platform.openai.com) |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` | [siliconflow.cn](https://siliconflow.cn) |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | [platform.moonshot.cn](https://platform.moonshot.cn) |
| Ollama (free, local) | `http://localhost:11434/v1` | `qwen2.5:7b` | No key needed — `ollama pull qwen2.5:7b`, then pick this preset |

Settings are stored in `config.json` (git-ignored; see `config.example.json`).

## 📝 Workflow

1. Create a resume in the **📚 Resume library** (name it after the target job, e.g. "ByteDance-Backend") and fill in basic info and experience
2. Paste the target JD → click **🔍 AI 分析关键词** to see the match score and suggestions
3. Stuck on writing? Expand **⭐ STAR 引导** on an entry, fill the four boxes, click **✨ 整合为要点**
4. Click **✨ AI 一键生成整篇** — 5 steps stream in and fill the form; polish any module with **✨ AI 润色**
5. Click **📊 AI 评分** for a hiring-manager review, then iterate on the suggestions
6. Switch templates on the right → **🖨 打印 / PDF** (choose "Save as PDF") or **⬇ Word / Markdown**
7. For the next job: create a new resume and repeat (versions never interfere, auto-saved)

## 🧪 Tests

22 unit tests (including real HTTP end-to-end tests), zero dependencies:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions CI (`.github/workflows/ci.yml`) runs the suite on Python 3.9 – 3.13 on every push.

## 📁 Project Structure

```
.
├── backend/                 # Local HTTP server (Python stdlib only)
│   ├── main.py              # Routes: static / generate(SSE) / resumes / settings / export
│   ├── llm.py               # OpenAI-compatible streaming calls (urllib, JSON auto-retry)
│   ├── prompts.py           # Prompt templates (few-shot, stepwise, STAR, scoring)
│   ├── export.py            # Export dispatch: Markdown / Word
│   ├── docx_py.py           # Word export (python-docx if installed)
│   └── docx_min.py          # Word export fallback (pure stdlib zipfile)
├── frontend/                # Vanilla frontend (no build step)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   └── test_core.py         # unittest suite
├── docs/                    # usage / architecture / API docs
├── .github/workflows/ci.yml # GitHub Actions CI
├── config.example.json      # Example config format
├── output/                  # Exported files (auto-created at runtime, git-ignored)
├── resumes/                 # Resume library data (auto-created, personal data, git-ignored)
├── run.bat / run.sh         # One-click start scripts
└── LICENSE                  # MIT
```

## ❓ FAQ

- **AI button says "no API Key"** → click **⚙️ 设置**, fill in and save.
- **Export PDF** → click **🖨 打印 / PDF**, choose "Save as PDF" in the print dialog (the form is hidden automatically).
- **Data lost after switching browsers?** → No: resumes live in local `resumes/` (JSON); the browser only remembers which one was open.
- **Port in use** → `python -m backend.main <other-port>`.
- **Want nicer Word output** → `pip install python-docx` and restart (export works without it too).

## 🤝 Contributing

Issues and Pull Requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

Planned directions: more templates, batch generation for multiple companies, ATS-friendly export, bilingual resumes, frontend unit tests.

## 📄 License

[MIT](LICENSE) © 2025 ALEG-1
