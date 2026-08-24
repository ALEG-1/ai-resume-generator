# 架构说明

本项目是「零第三方依赖」的本地 Web 应用：后端仅用 Python 标准库，前端为原生 HTML/CSS/JS。

## 总体结构

```
浏览器 (frontend/)         后端 (backend/)                 外部服务
┌──────────────┐  HTTP    ┌──────────────────┐  HTTPS   ┌─────────────┐
│  index.html  │ ───────▶ │  main.py         │ ───────▶ │  大模型 API  │
│  app.js      │  静态+API │  http.server     │  SSE/JSON│ (OpenAI兼容) │
│  style.css   │ ◀─────── │  ThreadingHTTPServer │ ◀───── │  DeepSeek等  │
└──────────────┘          │  + llm.py/prompts │          └─────────────┘
                          │  + export.py      │
                          │  + resumes.json   │ 本地数据（config.json）
                          └──────────────────┘
```

## 目录职责

| 文件 | 职责 |
| --- | --- |
| `backend/main.py` | HTTP 路由、SSE 流式生成编排、简历库/设置/导出的 REST 接口 |
| `backend/llm.py` | OpenAI 兼容接口调用（`urllib`）、SSE 流解析、JSON 提取与失败重试 |
| `backend/prompts.py` | 所有提示词模板：角色设定、分步生成、模块润色、STAR 整合、JD 分析、评分 |
| `backend/export.py` | 导出调度：Markdown 生成、Word 导出的双实现选择 |
| `backend/docx_py.py` | Word 导出（使用 python-docx，若已安装，排版更规范） |
| `backend/docx_min.py` | Word 导出兜底（纯标准库 `zipfile` 手写 OOXML） |
| `frontend/js/app.js` | 前端全部逻辑：状态管理、简历库、AI 流式调用、预览渲染、导出 |
| `frontend/index.html` | 页面结构（表单、预览、弹窗） |
| `tests/test_core.py` | 22 项 unittest（含真实 HTTP 端到端测试） |

## 请求流

### 1. AI 生成（SSE 流式）

```
前端 fetch POST /api/generate {mode, ...}
        │
        ▼
main._generate_events() 根据 mode 分发：
  ├─ full   → 分步生成：summary → experiences[] → projects[] → skills → self_assessment
  │          每步独立调用 LLM，产出 status/delta/result 三类 SSE 事件
  ├─ module → 单模块润色（简介/技能/评价/单条经历）
  ├─ star   → 把 STAR 四要素素材整合为要点
  ├─ jd     → JD 关键词分析（JSON，失败自动重试一次，温度 0.3）
  └─ score  → 简历评分（JSON，失败自动重试一次，温度 0.3）
        │
        ▼
SSE 事件流：event: status / delta / result / error
前端 callAI() 逐事件处理，result 后写回表单并自动保存
```

### 2. 简历库（REST JSON）

| 接口 | 说明 |
| --- | --- |
| `POST /api/resumes/save` | 新建或更新（无 id 则生成） |
| `GET /api/resumes` | 列表（按更新时间倒序） |
| `GET /api/resumes/{id}` | 单份详情 |
| `DELETE /api/resumes/{id}` | 删除 |

数据落盘为 `resumes/resumes.json`。

### 3. 导出

前端把当前简历（剥离 STAR 素材）POST 到 `/api/export`，后端生成 Markdown 或 .docx 返回并同时写入 `output/`。

## 关键设计

- **零依赖红线**：运行时只用标准库。`urllib` 直接调大模型（流式读取 SSE）；`http.server` 提供并发（ThreadingHTTPServer）；`zipfile` + 手写 XML 生成合规 .docx。
- **SSE 不缓冲**：`/api/generate` 以 `Connection: close` 逐块 flush，前端用 `fetch` + `ReadableStream` 边读边渲染。
- **JSON 可靠性**：所有要求 JSON 输出的模式（jd/score）都带「解析失败 → 携带错误反馈重试一次」；解析器容忍 Markdown 围栏与前后杂质。
- **分步生成**：整篇生成拆成多次独立短调用，避免单次超长输出截断或解析失败，各模块间互不影响。
- **可选增强**：`python-docx` 存在时自动使用（Word 排版更规范），缺失时降级到内置生成器——不破坏零依赖。
- **隐私**：API Key 存 `config.json`、简历存 `resumes/`，均已在 `.gitignore` 排除，数据不出本机。
