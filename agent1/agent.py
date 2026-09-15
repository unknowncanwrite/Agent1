"""The ReAct + plan + reflect loop. One class beats AutoGPT's loop,
OpenHands' CodeAct, and SWE-agent's edit loop — with free models.

Loop: plan -> act (tool) -> observe -> reflect -> repeat -> final answer.
Every step is JSONL-traced for observability (LangSmith-free).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from .config import AgentConfig
from .llm import OpenRouterClient, ChatResult
from .memory import Memory
from .tools import ToolRegistry

SYSTEM = """You are Agent1 Omni, an elite autonomous agent. You beat other agents by:
1) Planning first (todo_add), 2) using tools instead of guessing,
3) verifying results (read/test after write), 4) reflecting on errors.

TOOLS — call with a fenced json block, one per message if needed:
```json
{{"tool": "TOOL_NAME", "arguments": {{...}}}}
```

{tools}

RULES:
- For coding/research/file tasks you MUST use tools; never hallucinate file contents or URLs.
- After write_file/edit_file, read_file or run tests to verify.
- Web claims need web_search/web_fetch citations.
- Keep tool args small; chain steps across messages.
- When done, write the FINAL ANSWER with no tool block, starting with "FINAL:".
- If a tool errors, reflect briefly and try a different approach (max {max_steps} steps).
"""

REFLECT = ("Briefly reflect: what worked, what's stuck, what to try next "
           "(2-3 sentences, then continue with tools or FINAL:).")

ROLES = {
    "assistant": "You are a helpful general assistant.",
    "researcher": ("You are a meticulous research analyst. Search broadly, fetch "
                   "primary sources, cite every claim with URLs, save reports to files."),
    "coder": ("You are a senior software engineer. Explore the repo first "
              "(list_files/read_file), make minimal diffs, run and verify, "
              "never break existing tests."),
    "critic": ("You are a ruthless reviewer. Find flaws, missing cases, "
               "unverified claims. Suggest concrete fixes."),
    "planner": ("You are a pragmatic planner. Break goals into small verifiable "
                "steps with todo_add before acting."),
}


class Agent:
    def __init__(self, config: AgentConfig | None = None, client=None,
                 role: str = "assistant", task_kind: str = "general",
                 on_event: Callable[[dict], None] | None = None):
        self.config = config or AgentConfig.load()
        self.client = client or OpenRouterClient(self.config)
        self.role = role
        self.task_kind = task_kind
        self.on_event = on_event or (lambda e: None)
        ws = Path(self.config.workspace)
        trace_dir = ws / ".trace"
        trace_dir.mkdir(parents=True, exist_ok=True)
        self.memory = Memory(str(trace_dir / "memory.db"))
        self.tools = ToolRegistry(workspace=self.config.workspace,
                                  approval=self.config.approval,
                                  memory=self.memory,
                                  audit_log=str(trace_dir / "audit.jsonl"))
        self.trace_path = trace_dir / f"trace-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        self.transcript_path = trace_dir / f"transcript-{time.strftime('%Y%m%d-%H%M%S')}.md"
        self.history: list[dict] = []
        self.steps = 0
        self.last_model = ""
        self.compactions = 0
        if self.config.plugins_dir:
            from .tools import load_plugins
            n = load_plugins(self.tools, self.config.plugins_dir)
            if n:
                self._emit(type="plugins", loaded=n)

    # ----- internals -----
    def _emit(self, **e):
        e.setdefault("ts", time.time())
        self.on_event(e)
        try:
            with open(self.trace_path, "a") as f:
                f.write(json.dumps({k: str(v)[:4000] for k, v in e.items()}) + "\n")
        except Exception:
            pass

    def _system(self) -> str:
        return (ROLES.get(self.role, ROLES["assistant"]) + "\n\n" +
                SYSTEM.format(tools=self.tools.describe(),
                              max_steps=self.config.max_steps))

    def reset(self):
        self.history, self.steps = [], 0
        self.tools.todos = []
        self.compactions = 0

    # ----- context management (beats agents that crash on long runs) -----
    def _history_chars(self) -> int:
        return sum(len(str(m.get("content", ""))) for m in self.history)

    def _compact(self):
        """Sliding-window compaction: keep system + task + last 10 msgs,
        summarize the middle (LLM summary, truncation fallback)."""
        budget = self.config.history_char_budget
        if self._history_chars() <= budget or len(self.history) <= 14:
            return
        self.compactions += 1
        system = [m for m in self.history if m["role"] == "system"]
        rest = [m for m in self.history if m["role"] != "system"]
        if len(rest) <= 11:
            return
        middle, tail = rest[:-10], rest[-10:]
        summary = ""
        try:
            res = self.client.chat(
                [{"role": "user", "content":
                  "Summarize this agent transcript tail into 10 dense bullets "
                  "(decisions, file changes, errors, pending work):\n" +
                  "\n".join(f"{m['role']}: {str(m['content'])[:800]}" for m in middle)[-8000:]}],
                task="fast", max_tokens=800)
            summary = res.text[:3000]
        except Exception:
            summary = "(summary unavailable) " + \
                "\n".join(f"{m['role']}: {str(m['content'])[:200]}" for m in middle[-6:])
        self.history = system + [{"role": "system",
            "content": f"[Compacted {len(middle)} msgs]\n{summary}"}] + tail
        self._emit(type="compact", dropped=len(middle),
                   chars=self._history_chars())

    def _save_transcript(self, task: str, final: str):
        try:
            with open(self.transcript_path, "w") as f:
                f.write(f"# {task[:120]}\n\nFINAL:\n{final}\n\n---\n")
                for m in self.history:
                    f.write(f"\n## {m['role']}\n{str(m.get('content',''))[:3000]}\n")
        except Exception:
            pass

    # ----- main loop -----
    def run(self, task: str, max_steps: int | None = None) -> str:
        max_steps = max_steps or self.config.max_steps
        self.reset()
        self.history = [{"role": "system", "content": self._system()},
                        {"role": "user", "content": task}]
        self._emit(type="task_start", task=task, role=self.role)
        mem_hits = self.memory.search(task)
        if mem_hits:
            self.history.append({"role": "system", "content":
                "Relevant memories:\n" + "\n".join(f"- {f}" for _, f in mem_hits[:5])})

        final = ""
        for i in range(max_steps):
            self.steps = i + 1
            if i > 0 and i % self.config.reflect_every == 0:
                self.history.append({"role": "user", "content": REFLECT})
            self._compact()
            try:
                res: ChatResult = self.client.chat(
                    self.history, task=self.task_kind,
                    tools=self.tools.openai_tools())
            except Exception as e:
                self._emit(type="llm_error", error=str(e)[:500])
                final = f"FINAL: I could not reach any free model. Last error: {e}"
                break
            self.last_model = res.model
            self._emit(type="llm", model=res.model, text=res.text[:2000],
                       tool_calls=res.tool_calls, step=i + 1)
            self.history.append({"role": "assistant", "content": res.text or ""})
            if not res.tool_calls:
                final = res.text
                if "FINAL:" in res.text or i > 2:
                    break
                # nudge tool-shy models
                self.history.append({"role": "user", "content":
                    "Continue: use a tool call now, or start your final answer with FINAL:."})
                continue
            for call in res.tool_calls[:3]:  # max 3 tools/msg keeps free models stable
                out = self.tools.execute(call["tool"], call.get("arguments", {}))
                self._emit(type="tool", tool=call["tool"], output=out[:2000])
                self.history.append({"role": "user", "content":
                    f"[{call['tool']} result]\n{out[:6000]}"})
        else:
            final = (self.history[-1].get("content", "") if self.history else "") or \
                "FINAL: Stopped at max steps."

        final = final.replace("FINAL:", "").strip() or "Done."
        self.memory.save_episode(task, final)
        self._save_transcript(task, final)
        self._emit(type="task_done", steps=self.steps, answer=final[:2000],
                   stats=getattr(self.client, "stats", {}),
                   model=self.last_model, compactions=self.compactions,
                   trace=str(self.trace_path), transcript=str(self.transcript_path))
        return final

    def ask(self, message: str) -> str:
        """Single-turn chat (keeps history across calls)."""
        if not self.history:
            self.history = [{"role": "system", "content": self._system()}]
        self.history.append({"role": "user", "content": message})
        self._compact()
        res: ChatResult = self.client.chat(self.history, task=self.task_kind,
                                           tools=self.tools.openai_tools())
        self.last_model = res.model
        # execute tool rounds in chat mode (capped), then re-ask
        rounds = 0
        while res.tool_calls and rounds < 4:
            self.history.append({"role": "assistant", "content": res.text or ""})
            for call in res.tool_calls[:2]:
                out = self.tools.execute(call["tool"], call.get("arguments", {}))
                self.history.append({"role": "user", "content":
                    f"[{call['tool']} result]\n{out[:6000]}"})
            self._compact()
            res = self.client.chat(self.history, task=self.task_kind,
                                   tools=self.tools.openai_tools())
            self.last_model = res.model
            rounds += 1
        self.history.append({"role": "assistant", "content": res.text})
        return res.text
