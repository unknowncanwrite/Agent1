"""Central configuration + the free-model intelligence that beats paid agents.

Ranked 2026-09-15 from LIVE data (see MODEL_RANKINGS.md):
  - OpenRouter τ²-Bench Airline (agentic tool-use, 123 models, run Sep 15 2026)
  - OpenRouter usage rankings (through Sep 14 2026)
  - Artificial Analysis + community coding reports
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FreeModel:
    id: str
    context: int
    best_for: str  # coding | reasoning | general | fast | longctx | vision
    tau2: float = 0.0   # τ²-Bench Airline tool-use score (%) — 0 = unranked
    note: str = ""      # one-line evidence for this rank


# Live τ²-Bench Airline tool-use scores (Sep 15 2026) for our families:
# Nemotron 3 Ultra 76.9 (#13) · Gemma 4 31B 76.1 (#22, Pareto value) ·
# GLM-4.5-Air 70.9 (#59) · gpt-oss-120b 64.1 (#78) · Ling Flash 57.3 (#89) ·
# DeepSeek R1 54.5 (#91, slow) · gpt-oss-20b 51.4 (#93, loops!) ·
# Qwen3-Next 47.0 (#97) · Qwen3-Coder 46.7 (#98, airline-shaped, not code) ·
# Llama 4 44.6 · Llama 3.3 70B 38.7 (#113, fast 43s) · Qwen3-Coder-30B 43.1.
# Usage: Nemotron 3 Ultra (free) is #9 on ALL of OpenRouter (3.45T tokens).
FREE_MODELS: list[FreeModel] = [
    FreeModel("nvidia/nemotron-3-ultra-550b-a55b:free", 1_000_000, "longctx",
              76.9, "best free tool-user, #9 on OpenRouter, 1M ctx"),
    FreeModel("google/gemma-4-31b-it:free", 262_000, "vision",
              76.1, "Pareto value, multimodal, 140+ langs"),
    FreeModel("z-ai/glm-4.5-air:free", 131_000, "fast",
              70.9, "fast + strong tools (2.4m/task)"),
    FreeModel("openai/gpt-oss-120b:free", 131_000, "reasoning",
              64.1, "o3-mini-class reasoning, Apache-2.0"),
    FreeModel("qwen/qwen3-coder:free", 1_000_000, "coding",
              46.7, "coding specialist, 1M ctx (τ² is not code-shaped)"),
    FreeModel("poolside/laguna-m.1:free", 262_000, "coding",
              0.0, "flagship free coding agent model"),
    FreeModel("deepseek/deepseek-r1:free", 128_000, "reasoning",
              54.5, "deep thinker, slow — reason, don't agent"),
    FreeModel("inclusionai/ling-3.0-flash-vl:free", 262_000, "vision",
              57.3, "vision MoE, tool-calling, Sep 2026"),
    FreeModel("nex-agi/nex-n2.5-pro:free", 262_000, "general",
              0.0, "agentic coder w/ visual loop, Sep 2026"),
    FreeModel("qwen/qwen3-next-80b-a3b-instruct:free", 262_000, "general",
              47.0, "RAG/long-chat, stable output, 62s"),
    FreeModel("meta-llama/llama-3.3-70b-instruct:free", 131_000, "general",
              38.7, "fast chat 43s — weak tools, don't agent"),
    FreeModel("openai/gpt-oss-20b:free", 131_000, "fast",
              51.4, "⚠️ loops 18.7m/task — last resort only"),
]

# Explicit evidence-based leaders per task (then capability-sorted rest).
_TASK_FIRST: dict[str, list[str]] = {
    "general": ["nvidia/nemotron-3-ultra-550b-a55b:free",
                "google/gemma-4-31b-it:free",
                "z-ai/glm-4.5-air:free",
                "openai/gpt-oss-120b:free"],
    "code": ["qwen/qwen3-coder:free",
             "poolside/laguna-m.1:free",
             "nvidia/nemotron-3-ultra-550b-a55b:free",
             "openai/gpt-oss-120b:free"],
    "research": ["nvidia/nemotron-3-ultra-550b-a55b:free",
                 "google/gemma-4-31b-it:free",
                 "z-ai/glm-4.5-air:free",
                 "qwen/qwen3-next-80b-a3b-instruct:free"],
    "reason": ["deepseek/deepseek-r1:free",
               "openai/gpt-oss-120b:free",
               "nvidia/nemotron-3-ultra-550b-a55b:free",
               "google/gemma-4-31b-it:free"],
    "fast": ["z-ai/glm-4.5-air:free",
             "meta-llama/llama-3.3-70b-instruct:free",
             "qwen/qwen3-next-80b-a3b-instruct:free",
             "openai/gpt-oss-20b:free"],
    "vision": ["google/gemma-4-31b-it:free",
               "inclusionai/ling-3.0-flash-vl:free",
               "nvidia/nemotron-3-ultra-550b-a55b:free",
               "z-ai/glm-4.5-air:free"],
}

# Task -> preferred capability order for the non-leader remainder.
_TASK_ROUTE: dict[str, list[str]] = {
    "code": ["coding", "reasoning", "longctx", "general", "fast", "vision"],
    "research": ["longctx", "general", "reasoning", "fast", "coding", "vision"],
    "reason": ["reasoning", "longctx", "general", "coding", "fast", "vision"],
    "vision": ["vision", "longctx", "general", "reasoning", "fast", "coding"],
    "fast": ["fast", "general", "coding", "reasoning", "longctx", "vision"],
    "general": ["general", "longctx", "reasoning", "coding", "fast", "vision"],
}


def model_cascade_for(task: str = "general") -> list[str]:
    """Return free-model IDs ordered for this task kind.

    Evidence-based leaders first, then the rest capability-sorted
    (higher τ² tool-use score wins ties within a capability).
    """
    prefs = _TASK_ROUTE.get(task, _TASK_ROUTE["general"])
    rank = {cap: i for i, cap in enumerate(prefs)}
    first = _TASK_FIRST.get(task, _TASK_FIRST["general"])
    rest = [m for m in FREE_MODELS if m.id not in first]
    rest.sort(key=lambda m: (rank.get(m.best_for, 9), -m.tau2, -m.context))
    return first + [m.id for m in rest]


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
