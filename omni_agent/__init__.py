"""
OMNI-AGENT: The Ultimate Agent that overcomes all others.
Combines best of OpenClaw, CrewAI, LangGraph, OpenHands, AutoGPT, Browser-Use, MetaGPT, Mem0, etc.
Built free-first on OpenRouter.
"""
__version__ = "1.0.0"
__author__ = "OMNI-AGENT"

from .core.agent import OmniAgent
from .multi_agent.crew import OmniCrew
from .multi_agent.roles import AgentRole
from .config import OmniConfig

__all__ = ["OmniAgent", "OmniCrew", "AgentRole", "OmniConfig"]
