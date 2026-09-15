"""Free-model LLM client: OpenRouter with cascade fallback + rotation.

Beats the competition:
  - AutoGen/CrewAI/LangChain: single-model failure = dead agent.
  - Agent1: per-request cascade across :free models, 429 rotation,
    live auto-discovery of new free models, token/cost tracking,
    and an offline MockClient so everything is testable without a key.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .config import AgentConfig, FREE_MODELS


JSON_BLOCK = re.compile(r"```(?:json|tool|tool_call|function)?\s*(\{.*?\})\s*```", re.S | re.I)


@dataclass
class ChatResult:
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    model: str = ""
    usage: dict = field(default_factory=dict)


def extract_tool_calls(text: str) -> list[dict]:
    """Parse tool calls from free-form text.

    Supports: ```json {"tool": ..., "arguments": {...}} ```
    and {"name": ..., "arguments"/"args"/"parameters": {...}} variants.
    Free models are inconsistent, so we accept all shapes.
    """
    calls: list[dict] = []
    for m in JSON_BLOCK.finditer(text or ""):
        try:
            obj = json.loads(m.group(1))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("tool") or obj.get("name") or obj.get("function")
        args = obj.get("arguments", obj.get("args", obj.get("parameters", {})))
        if isinstance(name, dict):  # {"function": {"name":..,"arguments":..}}
            args = name.get("arguments", args)
            name = name.get("name")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {"_raw": args}
        if name and isinstance(args, dict):
            calls.append({"tool": str(name), "arguments": args})
    return calls


def strip_tool_blocks(text: str) -> str:
    return JSON_BLOCK.sub("", text or "").strip()


class OpenRouterClient:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig.load()
        self._discovered: list[str] = []
        self._cooldown: dict[str, float] = {}
        self.total_prompt = 0
        self.total_completion = 0

    # ---------- model discovery ----------
    def discover_free_models(self) -> list[str]:
        """Ask OpenRouter for the live catalog, keep :free models. Cached."""
        if self._discovered:
            return self._discovered
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/models",
                headers=self._headers(),
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            ids = [m["id"] for m in data.get("data", [])
                   if str(m.get("id", "")).endswith(":free")]
            # newest / most-context first is unknowable here; keep catalog order
            self._discovered = ids
        except Exception:
            self._discovered = []
        return self._discovered

    def cascade(self, task: str | None = None) -> list[str]:
        base = self.config.cascade(task)
        live = self.discover_free_models()
        if not live:
            return base
        fresh = [m for m in live if m not in base]
        return fresh + [m for m in base if m in live] + [m for m in base if m not in live]

    # ---------- chat ----------
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.config.referer,
            "X-Title": self.config.app_name,
        }

    def _post(self, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        last_err: Exception | None = None
        for attempt in range(3):
            req = urllib.request.Request(
                f"{self.config.base_url}/chat/completions",
                data=data, headers=self._headers(), method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.config.request_timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode()[:500]
                except Exception:
                    pass
                err = Exception(f"HTTP {e.code}: {body}")
                if e.code in (429, 500, 502, 503, 529):
                    last_err = err
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise err
            except Exception as e:  # network blip -> retry
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise last_err or Exception("request failed")

    def chat(self, messages: list[dict], task: str | None = None,
             tools: list[dict] | None = None, temperature: float = 0.4,
             max_tokens: int = 4096) -> ChatResult:
        if not self.config.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set. Copy .env.example to .env.")
        errors: list[str] = []
        network_fails = 0
        for model in self.cascade(task):
            if self._cooldown.get(model, 0) > time.time():
                continue
            payload: dict[str, Any] = {
                "model": model, "messages": messages,
                "temperature": temperature, "max_tokens": max_tokens,
            }
            if tools:  # OpenAI-compatible function calling (strong models use it)
                payload["tools"] = [{"type": "function",
                                     "function": t} for t in tools]
                payload["tool_choice"] = "auto"
            try:
                data = self._post(payload)
                choice = data["choices"][0]["message"]
                usage = data.get("usage", {})
                self.total_prompt += usage.get("prompt_tokens", 0)
                self.total_completion += usage.get("completion_tokens", 0)
                text = choice.get("content") or ""
                calls: list[dict] = []
                for tc in choice.get("tool_calls") or []:
                    fn = tc.get("function", {})
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except Exception:
                        args = {"_raw": fn.get("arguments", "")}
                    calls.append({"tool": fn.get("name", ""), "arguments": args})
                if not calls:
                    calls = extract_tool_calls(text)
                    text = strip_tool_blocks(text)
                self.last_model = model
                self.last_errors = []
                return ChatResult(text=text, tool_calls=calls, model=model, usage=usage)
            except Exception as e:
                msg = str(e)
                errors.append(f"{model}: {msg[:160]}")
                if "429" in msg or "rate" in msg.lower() or "limit" in msg.lower():
                    self._cooldown[model] = time.time() + 120  # rotate away 2 min
                if "HTTP " not in msg:  # network-level: no point trying 12 models
                    network_fails += 1
                    if network_fails >= 2:
                        errors.append("…cascade aborted: network unreachable "
                                      "(check connection / firewall for openrouter.ai)")
                        break
                continue
        self.last_errors = errors[:8]
        raise RuntimeError("All free models failed:\n" + "\n".join(errors[:8]))

    @property
    def stats(self) -> dict:
        return {"prompt_tokens": self.total_prompt,
                "completion_tokens": self.total_completion,
                "estimated_cost_usd": 0.0}


class MockClient:
    """Deterministic offline client so tests/demos run with no key/network."""

    def __init__(self, script: list[ChatResult] | None = None):
        self.script = list(script or [])
        self.calls: list[list[dict]] = []
        self.total_prompt = 0
        self.total_completion = 0

    def chat(self, messages: list[dict], **kwargs) -> ChatResult:
        self.calls.append(messages)
        if self.script:
            return self.script.pop(0)
        return ChatResult(text="Mock final answer. Provide a script for richer demos.",
                          model="mock")

    def cascade(self, task=None):
        return ["mock"]

    @property
    def stats(self):
        return {"prompt_tokens": 0, "completion_tokens": 0, "estimated_cost_usd": 0.0}
