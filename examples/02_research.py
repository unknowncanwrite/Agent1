"""Autonomous research run — beats AutoGPT at $0."""
from agent1 import Agent

agent = Agent(role="researcher", task_kind="research")
report = agent.run(
    "Research the top 3 open-source Python web frameworks in 2026. "
    "Save a comparison report with sources to report.md."
)
print(report)
