"""Central configuration + the free-model intelligence that beats paid agents.

Why this beats every other framework:
  - LangGraph/CrewAI/AutoGen/OpenHands all assume you bring an expensive key
    (GPT-4/Claude) or wire fallbacks yourself.
  - Agent1 ships with a curated, task-routed cascade of OpenRouter :free
    models, auto-discovery of new free models, 429 rotation and offline demo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FreeModel:
    id: str
    context: int
    best_for: str  # coding | reasoning | general | fast | longctx | vision


# Curated September 2026 free roster (verified via OpenRouter catalog +
# community benchmarks). Ordered = default fallback priority.
# The client ALSO auto-discovers live :free models at runtime and prepends
# any new ones it finds, so this list never goes stale.
FREE_MODELS: list[FreeModel] = [
    FreeModel("nvidia/nemotron-3-ultra-550b-a55b:free", 1_000_000, "longctx"),
    FreeModel("qwen/qwen3-coder:free", 1_000_000, "coding"),
    FreeModel("poolside/laguna-m.1:free", 262_000, "coding"),
    FreeModel("openai/gpt-oss-120b:free", 131_000, "reasoning"),
    FreeModel("nex-agi/nex-n2.5-pro:free", 262_000, "general"),
    FreeModel("google/gemma-4-31b-it:free", 262_000, "vision"),
    FreeModel("meta-llama/llama-3.3-70b-instruct:free", 131_000, "general"),
    FreeModel("deepseek/deepseek-r1:free", 128_000, "reasoning"),
    FreeModel("z-ai/glm-4.5-air:free", 131_000, "fast"),
    FreeModel("openai/gpt-oss-20b:free", 131_000, "fast"),
    FreeModel("inclusionai/ling-3.0-flash-vl:free", 262_000, "vision"),
    FreeModel("qwen/qwen3-next-80b-a3b-instruct:free", 262_000, "general"),
]

# Task -> preferred capability order (beats one-size-fits-all model choice)
_TASK_ROUTE: dict[str, list[str]] = {
    "code": ["coding", "reasoning", "longctx", "general", "fast", "vision"],
    "research": ["longctx", "general", "reasoning", "fast", "coding", "vision"],
    "reason": ["reasoning", "longctx", "general", "coding", "fast", "vision"],
    "vision": ["vision", "longctx", "general", "reasoning", "fast", "coding"],
    "fast": ["fast", "general", "coding", "reasoning", "longctx", "vision"],
    "general": ["general", "longctx", "reasoning", "coding", "fast", "vision"],
}


def model_cascade_for(task: str = "general") -> list[str]:
    """Return free-model IDs ordered for this task kind."""
    prefs = _TASK_ROUTE.get(task, _TASK_ROUTE["general"])
    rank = {cap: i for i, cap in enumerate(prefs)}
    ordered = sorted(FREE_MODELS, key=lambda m: (rank.get(m.best_for, 9), -m.context))
    return [m.id for m in ordered]


def _load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader (no dependency). Real python-dotenv wins if installed."""
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(path)
        return
    except Exception:
        pass
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


@dataclass
class AgentConfig:
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    default_task: str = "general"
    model_override: str = ""
    workspace: str = "./workspace"
    approval: str = "safe"       # auto | safe | manual
    max_steps: int = 25
    reflect_every: int = 6
    request_timeout: int = 120
    max_retries_per_model: int = 1
    referer: str = "https://github.com/unknowncanwrite/Agent1"
    app_name: str = "Agent1-Omni"
    demo: bool = False           # offline MockClient (AGENT1_DEMO=1)
    history_char_budget: int = 60000  # sliding-window compaction above this
    plugins_dir: str = ""        # AGENT1_PLUGINS: extra tool .py files
    web_timeout: int = 25

    @classmethod
    def load(cls) -> "AgentConfig":
        _load_dotenv()
        return cls(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
            default_task=os.environ.get("AGENT1_TASK", "general"),
            model_override=os.environ.get("AGENT1_MODEL", ""),
            workspace=os.environ.get("AGENT1_WORKSPACE", "./workspace"),
            approval=os.environ.get("AGENT1_APPROVAL", "safe"),
            max_steps=int(os.environ.get("AGENT1_MAX_STEPS", "25")),
            demo=os.environ.get("AGENT1_DEMO", "") in ("1", "true", "yes"),
            history_char_budget=int(os.environ.get("AGENT1_HISTORY_BUDGET", "60000")),
            plugins_dir=os.environ.get("AGENT1_PLUGINS", ""),
            web_timeout=int(os.environ.get("AGENT1_WEB_TIMEOUT", "25")),
        )

    def cascade(self, task: str | None = None) -> list[str]:
        if self.model_override:
            rest = [m for m in model_cascade_for(task or self.default_task)
                    if m != self.model_override]
            return [self.model_override] + rest
        return model_cascade_for(task or self.default_task)
