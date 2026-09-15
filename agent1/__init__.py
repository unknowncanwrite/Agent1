"""Agent1 Omni — one agent to beat them all.

Single-agent + multi-agent crew + coding agent + research agent + chat,
running on OpenRouter's FREE models ($0) with automatic fallback rotation.

Quick start:
    from agent1 import Agent
    agent = Agent()
    print(agent.run("Research the best Python web frameworks and save a report."))
"""
from .config import AgentConfig, FREE_MODELS, model_cascade_for
from .agent import Agent
from .crew import Crew

__version__ = "1.0.0"
__all__ = ["Agent", "Crew", "AgentConfig", "FREE_MODELS", "model_cascade_for"]
