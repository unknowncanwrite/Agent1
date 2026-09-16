"""
Example: Research Task - Beats GPT Researcher, Perplexity
"""
import os
from dotenv import load_dotenv
load_dotenv()

from omni_agent import OmniAgent, OmniConfig

config = OmniConfig.from_env()
agent = OmniAgent(config=config)

task = """
Research the latest AI agent frameworks in 2026 and create a comprehensive report.

Requirements:
1. Search for top 10 AI agent frameworks (GitHub stars, features)
2. Compare: LangGraph, CrewAI, AutoGen, OpenHands, OpenClaw, Dify
3. Focus on: multi-agent, memory, tool use, free models support
4. Create report at ./workspace/research/ai_agents_2026.md
5. Include table comparison, pros/cons, recommendation
6. Store key findings in memory for future

Use web_search and web_fetch extensively.
"""

result = agent.run(task, max_iterations=20)
print(result["answer"])
