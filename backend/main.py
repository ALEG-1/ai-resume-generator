"""求职简历生成器 - 本地 HTTP 服务（仅用 Python 标准库，无需安装任何包）。

启动：python -m backend.main [端口，默认 8010]
"""

import json
import mimetypes
import sys
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import export as export_mod
from . import llm, prompts

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_PATH = BASE_DIR / "config.json"
RESUMES_DIR = BASE_DIR / "resumes"
RESUMES_FILE = RESUMES_DIR / "resumes.json"

DEFAULT_PORT = 8010


# ---------------- 配置持久化 ----------------

def _load_config() -> dict:
    cfg = dict(llm.DEFAULT_SETTINGS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text("utf-8")))
        except Exception:
            pass
    return cfg


def _save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


# ---------------- 简历库持久化 ----------------

def _load_resumes() -> dict:
    """返回 {id: {"id", "name", "updated_at", "data": {...}}}。"""
    if RESUMES_FILE.exists():
        try:
            resumes = json.loads(RESUMES_FILE.read_text("utf-8"))
            if isinstance(resumes, dict):
                return resumes
        except Exception:
            pass
    return {}


def _save_resumes(resumes: dict):
    RESUMES_DIR.mkdir(exist_ok=True)
    RESUMES_FILE.write_text(json.dumps(resumes, ensure_ascii=False, indent=2), "utf-8")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------- AI 生成（SSE 流式） ----------------

def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_text_events(settings: dict, messages: list):
    """流式文本生成：产出 ("delta"|"error", data) 事件；结束时产出 (None, 文本|None)。

    text 为 None 表示已输出 error 事件（调用方应停止）。
    """
    parts = []
    try:
        for delta in llm.stream_chat(settings, messages, json_mode=False):
            parts.append(delta)
            yield ("delta", {"text": delta})
    except llm.LLMError as e:
        yield ("error", {"message": str(e)})
        yield (None, None)
        return
    except Exception as e:  # noqa: BLE001
        yield ("error", {"message": f"服务器错误：{e}"})
        yield (None, None)
        return
    yield (None, "".join(parts).strip())


def _generate_events(body: dict):
    """根据请求体产出 SSE 事件字符串（生成器）。"""
    settings = _load_config()
    mode = body.get("mode")
    try:
        if mode == "full":
            # 分步生成：简介 → 工作经历 → 项目经历 → 技能 → 自我评价，每步独立调用更稳定
            user_data = body.get("user_data", {})
            sys_msg = {"role": "system", "content": prompts.SYSTEM_RESUME_EXPERT}

            yield _sse("status", {"label": "第 1/5 步：撰写职业简介…"})
            for event, data in _stream_text_events(settings, [
                sys_msg, {"role": "user", "content": prompts.build_summary_message(user_data)}]):
                if event is None:
                    if data is None:
                        return
                    yield _sse("result", {"mode": "step", "section": "summary", "text": data})
                    break
                yield _sse(event, data)

            experiences = user_data.get("experiences") or []
            if experiences:
                yield _sse("status", {"label": f"第 2/5 步：打磨工作经历（共 {len(experiences)} 条）…"})
                for i, entry in enumerate(experiences):
                    yield _sse("status", {"label": f"打磨工作经历 {i + 1}/{len(experiences)}…"})
                    for event, data in _stream_text_events(settings, [
                        sys_msg, {"role": "user",
                                  "content": prompts.build_entry_bullets_message("experience", entry, user_data)}]):
                        if event is None:
                            if data is None:
                                return
                            yield _sse("result", {"mode": "step", "section": "experiences",
                                                  "index": i, "text": data})
                            break
                        yield _sse(event, data)

            projects = user_data.get("projects") or []
            if projects:
                yield _sse("status", {"label": f"第 3/5 步：打磨项目经历（共 {len(projects)} 条）…"})
                for i, entry in enumerate(projects):
                    yield _sse("status", {"label": f"打磨项目经历 {i + 1}/{len(projects)}…"})
                    for event, data in _stream_text_events(settings, [
                        sys_msg, {"role": "user",
                                  "content": prompts.build_entry_bullets_message("project", entry, user_data)}]):
                        if event is None:
                            if data is None:
                                return
                            yield _sse("result", {"mode": "step", "section": "projects",
                                                  "index": i, "text": data})
                            break
                        yield _sse(event, data)

            yield _sse("status", {"label": "第 4/5 步：提炼技能清单…"})
            for event, data in _stream_text_events(settings, [
                sys_msg, {"role": "user", "content": prompts.build_skills_message(user_data)}]):
                if event is None:
                    if data is None:
                        return
                    yield _sse("result", {"mode": "step", "section": "skills", "text": data})
                    break
                yield _sse(event, data)

            yield _sse("status", {"label": "第 5/5 步：撰写自我评价…"})
            for event, data in _stream_text_events(settings, [
                sys_msg, {"role": "user", "content": prompts.build_self_message(user_data)}]):
                if event is None:
                    if data is None:
                        return
                    yield _sse("result", {"mode": "step", "section": "self_assessment", "text": data})
                    break
                yield _sse(event, data)

        elif mode == "module":
            module = body.get("module")
            entry = body.get("entry", {})
            context = body.get("context", {})
            messages = [
                {"role": "system", "content": prompts.SYSTEM_MODULE_POLISH},
                {"role": "user", "content": prompts.build_module_polish_message(module, entry, context)},
            ]
            for event, data in _stream_text_events(settings, messages):
                if event is None:
                    if data is None:
                        return
                    yield _sse("result", {"mode": "module", "module": module, "text": data})
                    return
                yield _sse(event, data)

        elif mode == "star":
            entry = body.get("entry", {})
            context = body.get("context", {})
            messages = [
                {"role": "system", "content": prompts.SYSTEM_STAR_INTEGRATE},
                {"role": "user", "content": prompts.build_star_integrate_message(entry, context)},
            ]
            for event, data in _stream_text_events(settings, messages):
                if event is None:
                    if data is None:
                        return
                    yield _sse("result", {"mode": "module", "module": "star", "text": data})
                    return
                yield _sse(event, data)

        elif mode == "jd":
            jd = body.get("jd", "")
            user_data = body.get("user_data", {})
            messages = [
                {"role": "system", "content": prompts.SYSTEM_JD_ANALYSIS},
                {"role": "user", "content": prompts.build_jd_analysis_message(jd, user_data)},
            ]
            for attempt in range(2):
                parts = []
                for delta in llm.stream_chat(settings, messages, json_mode=True, temperature=0.3):
                    parts.append(delta)
                    yield _sse("delta", {"text": delta})
                raw = "".join(parts)
                parsed = llm.extract_json(raw)
                if parsed is not None:
                    yield _sse("result", {"mode": "jd", "data": parsed})
                    return
                if attempt == 0:
                    yield _sse("status", {"label": "输出格式有误，正在自动重试…"})
                    messages = messages + [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": "你上次的输出不是合法的 JSON。请只输出符合要求的 JSON 对象，"
                                                    "不要 Markdown 代码块、不要任何解释文字。"},
                    ]
            yield _sse("error", {"message": "JD 分析结果无法解析，请重试。", "raw": raw[:4000]})

        elif mode == "score":
            resume = body.get("resume", {})
            jd = body.get("jd", "")
            messages = [
                {"role": "system", "content": prompts.SYSTEM_SCORE},
                {"role": "user", "content": prompts.build_score_message(resume, jd)},
            ]
            for attempt in range(2):
                parts = []
                for delta in llm.stream_chat(settings, messages, json_mode=True, temperature=0.3):
                    parts.append(delta)
                    yield _sse("delta", {"text": delta})
                raw = "".join(parts)
                parsed = llm.extract_json(raw)
                if parsed is not None:
                    yield _sse("result", {"mode": "score", "data": parsed})
                    return
                if attempt == 0:
                    yield _sse("status", {"label": "输出格式有误，正在自动重试…"})
                    messages = messages + [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": "你上次的输出不是合法的 JSON。请只输出符合要求的 JSON 对象，"
                                                    "不要 Markdown 代码块、不要任何解释文字。"},
                    ]
            yield _sse("error", {"message": "评分结果无法解析，请重试。", "raw": raw[:4000]})

        else:
            yield _sse("error", {"message": f"未知模式：{mode}"})

    except llm.LLMError as e:
        yield _sse("error", {"message": str(e)})
    except Exception as e:  # noqa: BLE001
        yield _sse("error", {"message": f"服务器错误：{e}"})


# ---------------- HTTP Handler ----------------

class Handler(BaseHTTPRequestHandler):
    server_version = "ResumeServer/1.0"

    def log_message(self, fmt, *args):
        # 本地工具，静默访问日志（仅保留启动提示）
        pass

    # ---- 响应辅助 ----
    def _send_bytes(self, data: bytes, ctype: str, status: int = 200, filename: str = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, obj, status: int = 200):
        self._send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8", status)

    def _send_error(self, status: int = 404, msg: str = "Not Found"):
        self._send_bytes(msg.encode("utf-8"), "text/plain; charset=utf-8", status)

    def _read_body(self, limit: int = 10 * 1024 * 1024) -> bytes:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > limit:
            return b""
        return self.rfile.read(length)

    def _read_json_body(self):
        try:
            return json.loads(self._read_body() or b"{}")
        except Exception:
            return None

    # ---- GET ----
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_bytes((FRONTEND_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            f = (FRONTEND_DIR / rel).resolve()
            try:
                f.relative_to(FRONTEND_DIR.resolve())
            except ValueError:
                self._send_error(403, "Forbidden")
                return
            if not f.is_file():
                self._send_error(404, "Not Found")
                return
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            if ctype.startswith("text/"):
                ctype += "; charset=utf-8"
            self._send_bytes(f.read_bytes(), ctype)
            return
        if path == "/api/settings":
            self._send_json(_load_config())
            return
        if path == "/api/resumes":
            resumes = _load_resumes()
            lst = sorted(
                ({"id": v["id"], "name": v["name"], "updated_at": v["updated_at"]} for v in resumes.values()),
                key=lambda x: x["updated_at"], reverse=True)
            self._send_json({"resumes": lst})
            return
        if path.startswith("/api/resumes/"):
            rid = path.rsplit("/", 1)[-1]
            resumes = _load_resumes()
            if rid not in resumes:
                self._send_error(404, "Not Found")
                return
            self._send_json(resumes[rid])
            return
        self._send_error(404, "Not Found")

    # ---- POST / DELETE ----
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/settings":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Bad JSON")
                return
            _save_config({
                "api_key": str(body.get("api_key", "")).strip(),
                "base_url": str(body.get("base_url", "")).strip(),
                "model": str(body.get("model", "")).strip(),
                "temperature": float(body.get("temperature", 0.7)),
            })
            self._send_json({"ok": True})
            return
        if path == "/api/generate":
            self._handle_generate()
            return
        if path == "/api/export":
            self._handle_export()
            return
        if path == "/api/resumes/save":
            self._handle_resume_save()
            return
        self._send_error(404, "Not Found")

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/resumes/"):
            rid = path.rsplit("/", 1)[-1]
            resumes = _load_resumes()
            if rid in resumes:
                del resumes[rid]
                _save_resumes(resumes)
            self._send_json({"ok": True})
            return
        self._send_error(404, "Not Found")

    def _handle_resume_save(self):
        body = self._read_json_body()
        if body is None:
            self._send_error(400, "Bad JSON")
            return
        rid = str(body.get("id") or "").strip()
        if not rid:
            rid = uuid.uuid4().hex[:12]
        name = str(body.get("name") or "").strip() or "未命名简历"
        data = body.get("data")
        if not isinstance(data, dict):
            self._send_error(400, "Bad resume data")
            return
        resumes = _load_resumes()
        resumes[rid] = {"id": rid, "name": name, "updated_at": _now(), "data": data}
        _save_resumes(resumes)
        self._send_json({"ok": True, "id": rid, "name": name, "updated_at": resumes[rid]["updated_at"]})

    def _handle_generate(self):
        body = self._read_json_body()
        if body is None:
            self._send_error(400, "Bad JSON")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            for chunk in _generate_events(body):
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # noqa: BLE001
            try:
                self.wfile.write(_sse("error", {"message": f"服务器错误：{e}"}).encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    def _handle_export(self):
        body = self._read_json_body()
        if body is None:
            self._send_error(400, "Bad JSON")
            return
        fmt = body.get("fmt", "md")
        resume = body.get("resume", {})
        if fmt == "md":
            data = export_mod.build_markdown(resume).encode("utf-8")
            filename, media = "resume.md", "text/markdown; charset=utf-8"
        elif fmt == "docx":
            data = export_mod.build_docx_bytes(resume)
            filename = "resume.docx"
            media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            self._send_error(400, f"不支持的导出格式：{fmt}")
            return
        OUTPUT_DIR.mkdir(exist_ok=True)
        (OUTPUT_DIR / filename).write_bytes(data)
        self._send_bytes(data, media, filename=filename)


# ---------------- 启动 ----------------

def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    print(f"求职简历生成器已启动：http://127.0.0.1:{port}  （Ctrl+C 停止）")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
