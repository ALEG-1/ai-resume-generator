"""核心功能测试（仅用 Python 标准库，无需安装任何依赖）。

运行：python -m unittest discover -s tests -v
"""

import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import docx_min, export, llm, main  # noqa: E402


SAMPLE_RESUME = {
    "basic": {"name": "张伟", "target": "Python 后端开发工程师", "phone": "138-0000-0000",
              "email": "a@b.com", "city": "上海", "links": "github.com/x"},
    "summary": "4 年后端经验，擅长高并发服务。",
    "educations": [{"school": "华东理工大学", "major": "计算机", "degree": "本科",
                    "period": "2016-2020", "description": "- 奖学金\n- GPA 3.6"}],
    "experiences": [{"company": "某公司", "position": "后端工程师", "period": "2021-至今",
                     "description": "- 订单系统重构，QPS 提升 4 倍\n- 监控体系搭建"}],
    "projects": [{"name": "智能客服", "role": "核心开发", "period": "2022",
                  "description": "- 日均 10 万次对话"}],
    "skills": "Python\nFastAPI\nRedis",
    "self_assessment": "热爱技术，乐于承担复杂问题。",
}


class TestJsonParse(unittest.TestCase):
    """模型输出 JSON 解析（容忍代码块围栏与前后杂质）。"""

    def test_plain(self):
        self.assertEqual(llm.extract_json('{"a": 1}'), {"a": 1})

    def test_fenced(self):
        self.assertEqual(llm.extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_surrounded(self):
        self.assertEqual(llm.extract_json('前缀文字 {"a": 1} 后缀文字'), {"a": 1})

    def test_invalid(self):
        self.assertIsNone(llm.extract_json("没有 json"))
        self.assertIsNone(llm.extract_json(""))


class TestSseErrors(unittest.TestCase):
    """SSE 生成器在缺 Key / 未知模式时的错误事件。"""

    def test_no_key_module(self):
        events = list(main._generate_events(
            {"mode": "module", "module": "summary", "entry": {"content": "x"}, "context": {}}))
        self.assertTrue(any("event: error" in e and "未配置 API Key" in e for e in events), events)

    def test_no_key_full(self):
        events = list(main._generate_events({"mode": "full", "user_data": {}}))
        self.assertTrue(any("event: error" in e for e in events), events)

    def test_unknown_mode(self):
        events = list(main._generate_events({"mode": "bogus"}))
        self.assertTrue(any("未知模式" in e for e in events), events)

    def test_no_key_star(self):
        events = list(main._generate_events({"mode": "star", "entry": {"star": {"action": "x"}}, "context": {}}))
        self.assertTrue(any("event: error" in e and "未配置 API Key" in e for e in events), events)

    def test_no_key_score(self):
        events = list(main._generate_events({"mode": "score", "resume": {}, "jd": ""}))
        self.assertTrue(any("event: error" in e and "未配置 API Key" in e for e in events), events)


class TestLlmJson(unittest.TestCase):
    def test_extract_json(self):
        from backend import llm
        self.assertEqual(llm.extract_json('{"a": 1}'), {"a": 1})
        self.assertEqual(llm.extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertIsNone(llm.extract_json("no json"))


class TestMarkdown(unittest.TestCase):
    def test_markdown(self):
        md = export.build_markdown(SAMPLE_RESUME)
        for expect in ("# 张伟", "求职意向", "## 工作经历", "订单系统重构", "- 订单系统重构"):
            self.assertIn(expect, md)


class TestDocx(unittest.TestCase):
    def _check(self, data):
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(data)))
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertIn("word/document.xml", z.namelist())
        xml = z.read("word/document.xml").decode("utf-8")
        self.assertIn("张伟", xml)
        self.assertIn("订单系统重构", xml)

    def test_dispatched(self):
        """走导出调度（有 python-docx 用 python-docx，否则自动降级）。"""
        self._check(export.build_docx_bytes(SAMPLE_RESUME))

    def test_min_fallback(self):
        """内置轻量 docx 生成器。"""
        self._check(docx_min.build_docx_bytes(SAMPLE_RESUME))


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._orig = main.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        main.CONFIG_PATH = Path(self._tmpdir.name) / "config.json"

    def tearDown(self):
        main.CONFIG_PATH = self._orig
        self._tmpdir.cleanup()

    def test_roundtrip(self):
        main._save_config({"api_key": "k", "base_url": "http://x/v1", "model": "m", "temperature": 0.5})
        got = main._load_config()
        self.assertEqual(got["api_key"], "k")
        self.assertEqual(got["model"], "m")
        self.assertEqual(got["temperature"], 0.5)


class TestHttpServer(unittest.TestCase):
    """端到端：真实启动 HTTP 服务并请求各接口。"""

    @classmethod
    def setUpClass(cls):
        cls._orig_cfg = main.CONFIG_PATH
        cls._orig_out = main.OUTPUT_DIR
        cls._orig_res = main.RESUMES_FILE
        cls._tmpdir = tempfile.TemporaryDirectory()
        main.CONFIG_PATH = Path(cls._tmpdir.name) / "config.json"
        main.OUTPUT_DIR = Path(cls._tmpdir.name) / "out"
        main.RESUMES_FILE = Path(cls._tmpdir.name) / "resumes.json"
        cls.server = main.ThreadingHTTPServer(("127.0.0.1", 0), main.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        main.CONFIG_PATH = cls._orig_cfg
        main.OUTPUT_DIR = cls._orig_out
        main.RESUMES_FILE = cls._orig_res
        cls._tmpdir.cleanup()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def post_json(self, path, payload):
        req = urllib.request.Request(
            self.url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.headers, resp.read()

    def test_index(self):
        with urllib.request.urlopen(self.url("/"), timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("求职简历生成器".encode("utf-8"), resp.read())

    def test_static(self):
        with urllib.request.urlopen(self.url("/static/js/app.js"), timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read()
        self.assertGreater(len(body), 1000)

    def test_settings(self):
        status, _, _ = self.post_json("/api/settings", {
            "api_key": "sk-x", "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat", "temperature": 0.7})
        self.assertEqual(status, 200)
        with urllib.request.urlopen(self.url("/api/settings"), timeout=10) as resp:
            cfg = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(cfg["api_key"], "sk-x")

    def test_export_md(self):
        status, headers, body = self.post_json("/api/export", {"fmt": "md", "resume": SAMPLE_RESUME})
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        self.assertIn("# 张伟".encode("utf-8"), body)
        self.assertTrue((main.OUTPUT_DIR / "resume.md").exists())

    def test_export_docx(self):
        status, _, body = self.post_json("/api/export", {"fmt": "docx", "resume": SAMPLE_RESUME})
        self.assertEqual(status, 200)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(body)))

    def test_generate_error_event(self):
        status, _, body = self.post_json("/api/generate", {
            "mode": "module", "module": "summary", "entry": {"content": "x"}, "context": {}})
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn("event: error", text)
        self.assertIn("未配置 API Key", text)

    def test_resumes_crud(self):
        # 保存（新建）
        status, _, body = self.post_json("/api/resumes/save", {
            "id": None, "name": "投字节", "data": {"template": "modern", "basic": {"name": "张三"}, "experiences": []}})
        self.assertEqual(status, 200)
        saved = json.loads(body.decode("utf-8"))
        rid = saved["id"]
        self.assertTrue(rid)
        self.assertEqual(saved["name"], "投字节")
        # 列表
        with urllib.request.urlopen(self.url("/api/resumes"), timeout=10) as resp:
            lst = json.loads(resp.read().decode("utf-8"))["resumes"]
        self.assertEqual(len(lst), 1)
        self.assertEqual(lst[0]["id"], rid)
        # 读取
        with urllib.request.urlopen(self.url(f"/api/resumes/{rid}"), timeout=10) as resp:
            detail = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(detail["data"]["basic"]["name"], "张三")
        self.assertEqual(detail["data"]["template"], "modern")
        # 更新
        status, _, _ = self.post_json("/api/resumes/save", {
            "id": rid, "name": "投字节v2", "data": {"basic": {"name": "张三"}, "summary": "改过了"}})
        self.assertEqual(status, 200)
        with urllib.request.urlopen(self.url(f"/api/resumes/{rid}"), timeout=10) as resp:
            detail = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(detail["name"], "投字节v2")
        self.assertEqual(detail["data"]["summary"], "改过了")
        # 删除
        req = urllib.request.Request(self.url(f"/api/resumes/{rid}"), method="DELETE")
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
        with urllib.request.urlopen(self.url("/api/resumes"), timeout=10) as resp:
            lst = json.loads(resp.read().decode("utf-8"))["resumes"]
        self.assertEqual(len(lst), 0)
        # 404
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.url(f"/api/resumes/{rid}"), timeout=10)
        self.assertEqual(ctx.exception.code, 404)

    def test_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.url("/not-exist"), timeout=10)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
