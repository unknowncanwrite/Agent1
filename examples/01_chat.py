"""Single-agent chat — needs OPENROUTER_API_KEY in .env (free models)."""
from agent1 import Agent

agent = Agent()
print(agent.ask("What can you do? List your tools briefly."))
print(agent.ask("Remember that my favorite language is Python."))
print(agent.ask("What is my favorite language?"))
