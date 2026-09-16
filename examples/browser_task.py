"""
Example: Browser/Web Task - Beats Browser-Use, Skyvern
"""
import os
from dotenv import load_dotenv
load_dotenv()

from omni_agent import OmniAgent, OmniConfig

config = OmniConfig.from_env()
agent = OmniAgent(config=config)

task = """
Scrape and analyze the top 5 trending AI repositories on GitHub today.

Steps:
1. Search web for 'top trending AI GitHub repositories 2026'
2. Fetch GitHub trending page or relevant articles
3. Extract repo names, stars, descriptions
4. For each repo, fetch its README or description
5. Create analysis report at ./workspace/research/trending_ai_repos.md
6. Include table with repo, stars, language, purpose, why trending
7. Save findings to memory

Use web_search and web_fetch tools.
"""

result = agent.run(task)
print(result["answer"])
