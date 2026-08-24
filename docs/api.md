# API 文档

所有接口均为本地服务 `http://127.0.0.1:8010`，请求/响应使用 JSON（UTF-8）。

## 静态资源

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 应用主页（index.html） |
| GET | `/static/*` | 前端静态资源（css/js） |

## 模型设置

### GET `/api/settings`

返回当前模型配置。

```json
{
  "api_key": "sk-...",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "temperature": 0.7
}
```

### POST `/api/settings`

保存模型配置（写入 `config.json`）。请求体字段同上。

## AI 生成（SSE 流式）

### POST `/api/generate`

统一入口，按 `mode` 分发。响应为 Server-Sent Events，事件类型：

- `status`：进度提示（`{"label": "..."}`）
- `delta`：流式文本增量（`{"text": "..."}`）
- `result`：最终结果
- `error`：错误信息（`{"message": "...", "raw": "..."}`）

请求体（按 mode）：

| mode | 请求体 | result 说明 |
| --- | --- | --- |
| `full` | `{"mode": "full", "user_data": {...}}` | 分步生成。每步产出 `{"mode": "step", "section": "summary\|experiences\|projects\|skills\|self_assessment", "index": 可选, "text": "..."}` |
| `module` | `{"mode": "module", "module": "summary\|skills\|self_assessment\|education\|experience\|project", "entry": {...}, "context": {...}}` | `{"mode": "module", "module": "...", "text": "..."}` |
| `star` | `{"mode": "star", "entry": {"star": {"situation","task","action","result"}}, "context": {...}}` | `{"mode": "module", "module": "star", "text": "..."}` |
| `jd` | `{"mode": "jd", "jd": "...", "user_data": {...}}` | `{"mode": "jd", "data": {"keywords", "highlights", "suggestions", "match_score"}}` |
| `score` | `{"mode": "score", "resume": {...}, "jd": "..."}` | `{"mode": "score", "data": {"overall_score", "dimensions", "strengths", "suggestions"}}` |

> `user_data` 结构：`{basic, summary, educations[], experiences[], projects[], skills[], self_assessment, jd}`；
> 经历条目含可选 `star` 字段 `{situation, task, action, result}`。

## 简历库

### POST `/api/resumes/save`

新建或更新简历。无 `id` 时自动生成。

```json
{ "id": "可选", "name": "简历名称", "data": { "...简历字段..." } }
```

返回：`{"ok": true, "id": "...", "name": "...", "updated_at": "2026-08-24T10:00:00"}`

### GET `/api/resumes`

简历列表（按更新时间倒序）。

```json
{ "resumes": [ { "id": "...", "name": "...", "updated_at": "..." } ] }
```

### GET `/api/resumes/{id}`

单份简历详情。

```json
{ "id": "...", "name": "...", "updated_at": "...", "data": { "...简历字段..." } }
```

### DELETE `/api/resumes/{id}`

删除简历。返回 `{"ok": true}`。

## 导出

### POST `/api/export`

```json
{ "fmt": "md | docx", "resume": { "...简历字段..." } }
```

返回对应文件（`Content-Disposition: attachment`），同时写入 `output/` 目录。

## 数据文件

| 文件 | 内容 | 是否入库 |
| --- | --- | --- |
| `config.json` | API Key / 模型配置 | 否（.gitignore） |
| `resumes/resumes.json` | 简历库数据 | 否（.gitignore） |
| `output/` | 导出文件 | 否（.gitignore） |
