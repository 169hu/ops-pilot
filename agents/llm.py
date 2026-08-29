"""LLM 客户端抽象。

- 生产：走 DeepSeek API（deepseek-chat），实现结构 JSON 输出。
- 本地/无 key：走_rule_fallback，规则化分类，保证评测与自测可离线、可复现。
设计目的：Triage/Action 的分类逻辑几乎可以完全由规则覆盖，LLM 是增强而非依赖，
这既降低每次评测成本，也让「无网络」也能跑通全链路（面试演示不回因网络断掉）。

LLM_DRIVER=deepseek 走远端；否则走 rule（默认）。
"""
import json
import os
import time
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

_DRIVER = os.getenv("LLM_DRIVER", "rule")


def get_driver() -> str:
    return _DRIVER


def resolve(tool_config: str) -> str:
    return _DRIVER


class LlmClient:
    def __init__(self, model: str | None = None):
        import openai
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def chat_json(self, messages: list[dict], temperature: float = 0.0,
                  max_tokens: int = 512) -> tuple[dict, float, int]:
        t0 = time.monotonic()
        import openai
        try:
            resp = self._client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, response_format={"type": "json_object"})
            text = resp.choices[0].message.content or "{}"
            tokens = resp.usage.total_tokens if resp.usage else 0
            return json.loads(text), time.monotonic() - t0, tokens
        except openai.OpenAIError as e:
            return {"error": repr(e)}, time.monotonic() - t0, 0


class _Runner:
    """屏蔽驱动差异：统一给出 chat_json(messages)->(data, dt, tokens)。"""

    def __init__(self):
        self._rule_fn: Callable | None = None
        self._client: LlmClient | None = None
        if _DRIVER == "deepseek":
            self._client = LlmClient()
        else:
            from agents import rule_only
            self._rule_fn = rule_only.dispatch

    def chat_json(self, messages: list[dict], temperature=0.0, max_tokens=512):
        if self._client is not None:
            return self._client.chat_json(messages, temperature, max_tokens)
        user = m_last_user(messages)
        # 通过 system content 里的 role 标记路由到规则
        sys_role = m_sys_role(messages)
        data = self._rule_fn(user, sys_role)
        return data, 0.0, 0


def m_last_user(messages):  # pragma: no cover - helper
    for m in reversed(messages):
        if m.get("role") == "user":
            return m["content"]
    return ""


def m_sys_role(messages):  # pragma: no cover - helper
    for m in messages:
        if m.get("role") == "system":
            return m["content"]
    return ""


_client = None


def chat_json(messages: list[dict], temperature=0.0, max_tokens=512):
    """统一入口。"""
    global _client
    if _client is None:
        _client = _Runner()
    return _client.chat_json(messages, temperature=temperature, max_tokens=max_tokens)