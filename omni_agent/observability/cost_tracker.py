from dataclasses import dataclass, field
from typing import Dict, List
import time

@dataclass
class CostTracker:
    total_tokens: int = 0
    total_cost: float = 0.0  # Free = 0, but track for paid fallback
    calls: List[Dict] = field(default_factory=list)
    
    def log_call(self, model: str, tokens: int, cost: float = 0.0, latency: float = 0.0):
        self.total_tokens += tokens
        self.total_cost += cost
        self.calls.append({
            "timestamp": time.time(),
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "latency": latency
        })
    
    def get_summary(self) -> Dict:
        by_model = {}
        for call in self.calls:
            m = call["model"]
            if m not in by_model:
                by_model[m] = {"calls": 0, "tokens": 0, "cost": 0}
            by_model[m]["calls"] += 1
            by_model[m]["tokens"] += call["tokens"]
            by_model[m]["cost"] += call["cost"]
        
        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "total_calls": len(self.calls),
            "by_model": by_model,
            "avg_latency": sum(c.get("latency", 0) for c in self.calls) / max(1, len(self.calls))
        }
    
    def print_summary(self):
        summary = self.get_summary()
        print(f"\n💰 Cost Summary:")
        print(f"  Total tokens: {summary['total_tokens']}")
        print(f"  Total cost: ${summary['total_cost']:.4f} (free models = $0)")
        print(f"  Total calls: {summary['total_calls']}")
        for model, stats in summary["by_model"].items():
            print(f"    {model}: {stats['calls']} calls, {stats['tokens']} tokens")
