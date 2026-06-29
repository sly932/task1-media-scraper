"""OpenAI 兼容 LLM 客户端（默认 SiliconFlow / DeepSeek）。

只暴露两个能力：
  - chat_json(): 强制返回 JSON，pipeline 的 query理解/相关性/去重都走它
  - ping():      连通性自检
所有语义环节集中在此，便于控 token 与替换 provider。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from .config import env


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, cfg: dict[str, Any] | None = None):
        cfg = cfg or {}
        self.base_url = (env("LLM_BASE_URL") or "https://api.siliconflow.cn/v1").rstrip("/")
        self.model = env("LLM_MODEL") or "deepseek-ai/DeepSeek-V4-Flash"
        self.api_key = env("SILICONFLOW_API_KEY") or env("LLM_API_KEY") or ""
        self.temperature = cfg.get("temperature", 0.2)
        self.max_tokens = cfg.get("max_tokens", 2048)
        self.timeout_s = cfg.get("timeout_s", 60)

    # ---- 低层 ----
    def _post(self, messages: list[dict], **kw) -> str:
        if not self.api_key:
            raise LLMError("未配置 LLM key（SILICONFLOW_API_KEY）")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kw.get("temperature", self.temperature),
            "max_tokens": kw.get("max_tokens", self.max_tokens),
        }
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_s,
            )
            r.raise_for_status()
        except Exception as e:
            raise LLMError(f"LLM 请求失败: {e}") from e
        return r.json()["choices"][0]["message"]["content"]

    def chat_json(self, system: str, user: str, **kw) -> Any:
        """要求模型返回 JSON；带一次容错解析（剥 ```json 围栏 / 抓首个 JSON 块）。"""
        content = self._post(
            [{"role": "system", "content": system + "\n只输出 JSON，不要解释。"},
             {"role": "user", "content": user}],
            **kw,
        )
        return _extract_json(content)

    def ping(self) -> str:
        return self._post(
            [{"role": "user", "content": "reply with the single word: pong"}],
            max_tokens=10,
        ).strip()


def make_llm(cfg: dict[str, Any] | None = None):
    """工厂：LLM_STUB=1 时返回离线打桩客户端（自测用），否则返回真实客户端。"""
    if os.getenv("LLM_STUB") == "1":
        from .stub_llm import StubLLMClient
        return StubLLMClient()
    return LLMClient(cfg)


def _extract_json(text: str) -> Any:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            return json.loads(m.group(1))
        raise LLMError(f"LLM 返回非 JSON: {text[:200]}")


if __name__ == "__main__":
    # python -m media_scraper.llm --ping
    from .config import load_config
    load_config()
    c = LLMClient()
    print(f"base={c.base_url}\nmodel={c.model}\nkey={'set' if c.api_key else 'MISSING'}")
    try:
        print("ping ->", c.ping())
    except Exception as e:
        print("PING FAILED:", e)
