"""Multi-agent crew — CrewAI-style collaboration at $0."""
from agent1 import Crew

crew = Crew()
print(crew.run(
    "Design a simple habit-tracker CLI spec and implement a working prototype.",
    mode="sequential",  # or hierarchical | debate
))
