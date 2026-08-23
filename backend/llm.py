"""OpenAI 兼容的流式聊天调用（仅用 Python 标准库）。

支持所有兼容 /v1/chat/completions 的服务：
DeepSeek、OpenAI、Kimi(Moonshot)、硅基流动、通义、Ollama 本地等。
"""

import json
import urllib.error
import urllib.request

DEFAULT_SETTINGS = {
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "temperature": 0.7,
}


class LLMError(Exception):
    """模型调用相关错误（缺少 Key、网络失败、接口错误等）。"""


def stream_chat(settings: dict, messages: list, json_mode: bool = False):
    """以 SSE 流式返回文本增量（生成器）；出错抛 LLMError。"""
    api_key = (settings.get("api_key") or "").strip()
    base_url = (settings.get("base_url") or DEFAULT_SETTINGS["base_url"]).strip().rstrip("/")
    model = (settings.get("model") or DEFAULT_SETTINGS["model"]).strip()
    try:
        temperature = float(settings.get("temperature", 0.7))
    except (TypeError, ValueError):
        temperature = 0.7

    if not api_key:
        raise LLMError("未配置 API Key，请点击右上角「⚙️ 设置」填写。")
    if not model:
        raise LLMError("未配置模型名称。")

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise LLMError(f"模型接口返回 {e.code}：{body[:500]}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"网络请求失败：{e.reason}") from e

    try:
        for line in resp:
            line = line.decode("utf-8", "ignore").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
    finally:
        resp.close()


def chat_text(settings: dict, messages: list, json_mode: bool = False) -> str:
    """一次性获取完整回复文本。"""
    return "".join(stream_chat(settings, messages, json_mode))
