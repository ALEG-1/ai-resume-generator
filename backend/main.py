"""求职简历生成器 - 本地 HTTP 服务（仅用 Python 标准库，无需安装任何包）。

启动：python -m backend.main [端口，默认 8010]
"""

import json
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import export as export_mod
from . import llm, prompts

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_PATH = BASE_DIR / "config.json"

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


# ---------------- AI 生成（SSE 流式） ----------------

def _parse_json(raw: str):
    """从模型输出中提取 JSON 对象；容忍 ```json 围栏等杂质。"""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return None


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _generate_events(body: dict):
    """根据请求体产出 SSE 事件字符串（生成器）。"""
    settings = _load_config()
    mode = body.get("mode")
    try:
        if mode == "full":
            user_data = body.get("user_data", {})
            messages = [
                {"role": "system", "content": prompts.SYSTEM_RESUME_EXPERT},
                {"role": "user", "content": prompts.build_full_resume_user_message(user_data)},
            ]
            parts = []
            for delta in llm.stream_chat(settings, messages, json_mode=True):
                parts.append(delta)
                yield _sse("delta", {"text": delta})
            parsed = _parse_json("".join(parts))
            if parsed is None:
                yield _sse("error", {
                    "message": "模型输出无法解析为 JSON，请重试一次；若仍失败可换用更稳的模型（如 deepseek-chat）。",
                    "raw": "".join(parts)[:8000],
                })
                return
            yield _sse("result", {"mode": "full", "data": parsed})

        elif mode == "module":
            module = body.get("module")
            entry = body.get("entry", {})
            context = body.get("context", {})
            messages = [
                {"role": "system", "content": prompts.SYSTEM_MODULE_POLISH},
                {"role": "user", "content": prompts.build_module_polish_message(module, entry, context)},
            ]
            parts = []
            for delta in llm.stream_chat(settings, messages, json_mode=False):
                parts.append(delta)
                yield _sse("delta", {"text": delta})
            yield _sse("result", {"mode": "module", "module": module, "text": "".join(parts).strip()})

        elif mode == "jd":
            jd = body.get("jd", "")
            user_data = body.get("user_data", {})
            messages = [
                {"role": "system", "content": prompts.SYSTEM_JD_ANALYSIS},
                {"role": "user", "content": prompts.build_jd_analysis_message(jd, user_data)},
            ]
            parts = []
            for delta in llm.stream_chat(settings, messages, json_mode=True):
                parts.append(delta)
                yield _sse("delta", {"text": delta})
            parsed = _parse_json("".join(parts))
            if parsed is None:
                yield _sse("error", {
                    "message": "JD 分析结果无法解析，请重试。",
                    "raw": "".join(parts)[:4000],
                })
                return
            yield _sse("result", {"mode": "jd", "data": parsed})

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
        self._send_error(404, "Not Found")

    # ---- POST ----
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/settings":
            try:
                body = json.loads(self._read_body() or b"{}")
            except Exception:
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
        self._send_error(404, "Not Found")

    def _handle_generate(self):
        try:
            body = json.loads(self._read_body() or b"{}")
        except Exception:
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
        try:
            body = json.loads(self._read_body() or b"{}")
        except Exception:
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
