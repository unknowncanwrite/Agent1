"""Autonomous coding run — mini OpenHands/SWE-agent at $0."""
from agent1 import Agent

agent = Agent(role="coder", task_kind="code")
print(agent.run(
    "In the workspace, create a Python package `calc` with add/sub/mul/div, "
    "a test file, run the tests, and fix anything failing."
))
