"""
Configuration - Central brain for OMNI-AGENT
Handles OpenRouter key securely, model registry, workspace paths
"""
import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

# dotenv optional - for Render build phase
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

# NEVER hardcode keys - always from env
def get_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        env_path = Path(".env")
        if env_path.exists():
            try:
                load_dotenv(env_path)
                key = os.getenv("OPENROUTER_API_KEY")
            except:
                pass
    if not key:
        if os.getenv("ALLOW_DUMMY_KEY", "true").lower() == "true":
            return os.getenv("OPENROUTER_API_KEY", "dummy-key-for-ui")
        raise ValueError(
            "OPENROUTER_API_KEY not set. Set env var or create .env file. "
            "Get free key at https://openrouter.ai/keys"
        )
    return key

FREE_MODELS_REGISTRY = {
    "coder": [
        "qwen/qwen3-coder:free",
        "poolside/laguna-m.1:free",
        "poolside/laguna-xs-2.1:free",
        "poolside/laguna-s-2.1:free",
        "cohere/north-mini-code:free",
        "openai/gpt-oss-120b:free",
    ],
    "reasoning": [
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "openai/gpt-oss-20b:free",
        "openai/gpt-oss-120b:free",
    ],
    "general": [
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
    ],
    "router": ["openrouter/free"],
    "omni": [
        "qwen/qwen3-coder:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-31b-it:free",
        "poolside/laguna-m.1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "openai/gpt-oss-20b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "cohere/north-mini-code:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "openrouter/free",
    ]
}

@dataclass
class OmniConfig:
    api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = field(default_factory=lambda: os.getenv("OMNI_DEFAULT_MODEL", "qwen/qwen3-coder:free"))
    fallback_models: List[str] = field(default_factory=lambda: (
        os.getenv("OMNI_FALLBACK_MODELS", "").split(",") if os.getenv("OMNI_FALLBACK_MODELS") else FREE_MODELS_REGISTRY["omni"]
    ))
    workspace_dir: Path = field(default_factory=lambda: Path(os.getenv("OMNI_WORKSPACE", "./workspace")))
    memory_dir: Path = field(default_factory=lambda: Path(os.getenv("OMNI_MEMORY_DIR", "./workspace/memory")))
    skills_dir: Path = field(default_factory=lambda: Path(os.getenv("OMNI_SKILLS_DIR", "./workspace/skills")))
    transcripts_dir: Path = field(default_factory=lambda: Path(os.getenv("OMNI_TRANSCRIPTS_DIR", "./workspace/transcripts")))
    max_iterations: int = 25
    max_tokens: int = 4096
    temperature: float = 0.2
    enable_browser: bool = True
    enable_code_exec: bool = True
    enable_memory: bool = True
    enable_subagents: bool = True
    sandbox_mode: bool = True
    daily_token_limit: int = 500_000
    enable_cost_tracking: bool = True
    
    def __post_init__(self):
        self.fallback_models = [m.strip() for m in self.fallback_models if m.strip()]
        for d in [self.workspace_dir, self.memory_dir, self.skills_dir, self.transcripts_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "OmniConfig":
        try:
            api_key = get_api_key()
        except ValueError:
            api_key = os.getenv("OPENROUTER_API_KEY", "dummy-key-for-ui")
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=os.getenv("OMNI_DEFAULT_MODEL", "qwen/qwen3-coder:free"),
        )
    
    def get_model_for_task(self, task_type: str = "omni") -> List[str]:
        if task_type in FREE_MODELS_REGISTRY:
            return FREE_MODELS_REGISTRY[task_type]
        return self.fallback_models
