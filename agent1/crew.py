"""Multi-agent orchestration: CrewAI-style roles + AutoGen-style debate
+ LangGraph-style routing — in ~120 lines, on free models.

Modes:
  - sequential: researcher -> coder -> critic (pipeline)
  - hierarchical: planner breaks down, manager delegates, critic reviews
  - debate: N agents argue, judge picks the winner
"""
from __future__ import annotations

from typing import Callable

from .agent import Agent
from .config import AgentConfig


class Crew:
    def __init__(self, config: AgentConfig | None = None, client=None,
                 on_event: Callable[[dict], None] | None = None):
        self.config = config or AgentConfig.load()
        self._client = client
        self.on_event = on_event or (lambda e: None)

    def _agent(self, role: str, task_kind: str) -> Agent:
        return Agent(config=self.config, client=self._client, role=role,
                     task_kind=task_kind, on_event=self.on_event)

    def sequential(self, task: str, roles=("researcher", "coder", "critic")) -> str:
        kinds = {"researcher": "research", "coder": "code", "critic": "reason",
                 "planner": "general", "assistant": "general"}
        context, outs = "", {}
        for role in roles:
            agent = self._agent(role, kinds.get(role, "general"))
            prompt = (f"{task}\n\nPrevious crew output:\n{context[:4000]}"
                      if context else task)
            if role == "critic":
                prompt += ("\n\nReview the work above. List issues found, "
                           "fix what you can with tools, then give the FINAL verdict.")
            out = agent.run(prompt, max_steps=12)
            outs[role] = out
            context += f"\n\n### {role}:\n{out}"
            self.on_event({"type": "crew_step", "role": role})
        return context.strip()

    def hierarchical(self, task: str) -> str:
        planner = self._agent("planner", "general")
        plan = planner.run(
            f"Break this goal into 2-4 delegated subtasks (numbered, one line each). "
            f"Goal: {task}", max_steps=6)
        self.on_event({"type": "crew_step", "role": "planner", "plan": plan[:1000]})
        coder = self._agent("coder", "code")
        work = coder.run(f"Goal: {task}\nApproved plan:\n{plan}\nExecute it now.",
                         max_steps=15)
        critic = self._agent("critic", "reason")
        verdict = critic.run(f"Goal: {task}\nWork to review:\n{work}\n"
                             f"Verify and produce the FINAL answer.", max_steps=8)
        return f"## Plan\n{plan}\n\n## Work\n{work}\n\n## Final review\n{verdict}"

    def debate(self, task: str, rounds: int = 2) -> str:
        a, b = self._agent("researcher", "research"), self._agent("coder", "code")
        pa, pb = task, task
        for r in range(rounds):
            oa = a.run(f"{pa}\nArgue FOR your approach, rebut the other side.", max_steps=6)
            ob = b.run(f"{pb}\nArgue FOR your approach, rebut this: {oa[:2000]}", max_steps=6)
            pa, pb = f"{task}\nOpponent said: {ob[:2000]}", f"{task}\nOpponent said: {oa[:2000]}"
            self.on_event({"type": "crew_step", "role": f"debate-round-{r+1}"})
        judge = self._agent("critic", "reason")
        return judge.run(f"Question: {task}\nSide A: {oa}\nSide B: {ob}\n"
                         f"Pick the stronger side and give the FINAL answer.", max_steps=6)

    def run(self, task: str, mode: str = "sequential") -> str:
        mode = (mode or "sequential").lower()
        if mode == "hierarchical":
            return self.hierarchical(task)
        if mode == "debate":
            return self.debate(task)
        return self.sequential(task)
