"""
Intelligent Model Router - Heart of free-first strategy
- Routes tasks to best free model
- Auto-failover
- Cost tracking
- Performance learning
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from ..config import FREE_MODELS_REGISTRY, OmniConfig

@dataclass
class TaskProfile:
    task_type: str
    priority: str  # speed, quality, cost, long_context
    estimated_tokens: int
    requires_tools: bool
    requires_vision: bool = False

class ModelRouter:
    """
    Routes tasks to optimal free model based on task analysis
    Outperforms single-model agents by using specialized models per subtask
    """
    
    ROUTING_RULES = {
        # Coding tasks -> best coding free models
        "coding": {
            "primary": "qwen/qwen3-coder:free",
            "fallbacks": ["poolside/laguna-m.1:free", "cohere/north-mini-code:free", "openai/gpt-oss-120b:free"],
            "reason": "Qwen3 Coder is #1 free coding model with 1M context and tool use"
        },
        "code_review": {
            "primary": "qwen/qwen3-coder:free",
            "fallbacks": ["openai/gpt-oss-120b:free", "nvidia/nemotron-3-super-120b-a12b:free"],
            "reason": "Strong reasoning for review"
        },
        "research": {
            "primary": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallbacks": ["nvidia/nemotron-3-super-120b-a12b:free", "google/gemma-4-31b-it:free"],
            "reason": "1M context for deep research, large MoE"
        },
        "general": {
            "primary": "google/gemma-4-31b-it:free",
            "fallbacks": ["meta-llama/llama-3.3-70b-instruct:free", "openai/gpt-oss-20b:free"],
            "reason": "Balanced generalist"
        },
        "reasoning": {
            "primary": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallbacks": ["openai/gpt-oss-120b:free", "qwen/qwen3-next-80b-a3b-instruct:free"],
            "reason": "550B MoE for complex reasoning"
        },
        "fast": {
            "primary": "openai/gpt-oss-20b:free",
            "fallbacks": ["meta-llama/llama-3.2-3b-instruct:free", "nvidia/nemotron-3-nano-30b-a3b:free"],
            "reason": "Fast, lightweight"
        },
        "multimodal": {
            "primary": "google/gemma-4-31b-it:free",
            "fallbacks": ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"],
            "reason": "Vision + video support"
        },
        "long_context": {
            "primary": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallbacks": ["qwen/qwen3-coder:free", "nvidia/nemotron-3-super-120b-a12b:free"],
            "reason": "1M context window"
        }
    }
    
    def __init__(self, config: OmniConfig):
        self.config = config
        self.performance_log: Dict[str, Dict] = {}  # model -> stats
        self.task_history: List[Dict] = []
    
    def analyze_task(self, task_description: str) -> TaskProfile:
        """Analyze task to determine optimal routing"""
        desc_lower = task_description.lower()
        
        # Heuristics to detect task type
        if any(k in desc_lower for k in ["code", "program", "function", "bug", "debug", "refactor", "implement", "repo", "github"]):
            task_type = "coding"
        elif any(k in desc_lower for k in ["research", "analyze", "investigate", "report", "paper", "study"]):
            task_type = "research"
        elif any(k in desc_lower for k in ["reason", "logic", "math", "solve", "complex", "plan"]):
            task_type = "reasoning"
        elif any(k in desc_lower for k in ["image", "picture", "video", "vision", "screenshot"]):
            task_type = "multimodal"
        elif len(task_description) > 5000:
            task_type = "long_context"
        else:
            task_type = "general"
        
        # Estimate tokens
        est_tokens = len(task_description) // 4 + 1000
        
        return TaskProfile(
            task_type=task_type,
            priority="quality" if task_type in ["coding", "reasoning"] else "balanced",
            estimated_tokens=est_tokens,
            requires_tools=True,
            requires_vision=task_type == "multimodal"
        )
    
    def route(self, task_description: str, preferred_model: Optional[str] = None) -> List[str]:
        """
        Returns ordered list of models to try
        """
        if preferred_model:
            # User override
            return [preferred_model] + self.config.fallback_models
        
        profile = self.analyze_task(task_description)
        rule = self.ROUTING_RULES.get(profile.task_type, self.ROUTING_RULES["general"])
        
        models = [rule["primary"]] + rule["fallbacks"] + self.config.fallback_models
        
        # Deduplicate
        seen = set()
        ordered = []
        for m in models:
            if m not in seen:
                ordered.append(m)
                seen.add(m)
        
        # Boost models that performed well historically
        # Simple: if a model has good success rate, move it up
        if self.performance_log:
            ordered.sort(key=lambda m: self.performance_log.get(m, {}).get("success_rate", 0.5), reverse=True)
        
        return ordered
    
    def log_performance(self, model: str, success: bool, latency: float, tokens: int):
        """Learn from performance"""
        if model not in self.performance_log:
            self.performance_log[model] = {"success": 0, "fail": 0, "total_latency": 0, "total_tokens": 0}
        
        stats = self.performance_log[model]
        if success:
            stats["success"] += 1
        else:
            stats["fail"] += 1
        stats["total_latency"] += latency
        stats["total_tokens"] += tokens
        stats["success_rate"] = stats["success"] / max(1, stats["success"] + stats["fail"])
    
    def get_stats(self) -> Dict:
        return {
            "performance": self.performance_log,
            "routing_rules": self.ROUTING_RULES,
            "available_free_models": FREE_MODELS_REGISTRY,
        }
