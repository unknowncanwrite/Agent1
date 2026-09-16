"""
Example: Coding Task - Beats OpenHands, Aider, SWE-agent
"""
import os
from dotenv import load_dotenv
load_dotenv()

from omni_agent import OmniAgent, OmniConfig

config = OmniConfig.from_env()
agent = OmniAgent(config=config)

task = """
Build a Python REST API for a todo app with:
- FastAPI
- SQLite storage
- CRUD endpoints: create, read, update, delete todos
- Pydantic models
- Tests with pytest
- Save to ./workspace/todo_api/

Steps:
1. Explore workspace
2. Create directory structure
3. Write main.py with FastAPI app
4. Write models.py
5. Write database.py
6. Write tests
7. Run tests to verify
8. Document usage
"""

result = agent.run(task, max_iterations=20)
print("\n" + "="*60)
print(result["answer"])
print(f"\nTokens: {result['total_tokens']} | Model: {result['model_used']}")
