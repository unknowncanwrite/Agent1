"""Adversarial agent-loop tests: recovery, caps, compaction, traces."""
import json
import tempfile

from agent1.agent import Agent, REFLECT
from agent1.config import AgentConfig
from agent1.crew import Crew
from agent1.llm import MockClient, ChatResult


def agent(script, **kw):
    tmp = tempfile.mkdtemp()
    base = dict(workspace=tmp, approval="auto", max_steps=8, reflect_every=2)
    base.update(kw)
    return Agent(config=AgentConfig(**base), client=MockClient(script))


def test_unknown_tool_recovery():
    a = agent([ChatResult(text="", tool_calls=[{"tool": "nope", "arguments": {}}], model="m"),
               ChatResult(text="FINAL: recovered", model="m")])
    assert a.run("do it") == "recovered"
    joined = " ".join(str(m.get("content", "")) for m in a.history)
    assert "unknown tool" in joined


def test_tool_error_recovery():
    a = agent([ChatResult(text="", tool_calls=[{"tool": "bash", "arguments": {}}], model="m"),
               ChatResult(text="FINAL: handled", model="m")])
    assert a.run("x") == "handled"


def test_three_tools_per_message_cap():
    evs = []
    tmp = tempfile.mkdtemp()
    cfg = AgentConfig(workspace=tmp, approval="auto", max_steps=4)
    a = Agent(config=cfg, client=MockClient([
        ChatResult(text="", tool_calls=[{"tool": "todo_add", "arguments": {"task": f"t{i}"}}
                                        for i in range(5)], model="m"),
        ChatResult(text="FINAL: done", model="m")]), on_event=evs.append)
    a.run("x")
    assert len([e for e in evs if e.get("type") == "tool"]) == 3


def test_max_steps_exhaustion():
    script = [ChatResult(text="", tool_calls=[
        {"tool": "todo_add", "arguments": {"task": "t"}}], model="m")] * 10
    a = agent(script, max_steps=5)
    out = a.run("never ends")
    assert a.steps == 5 and isinstance(out, str)


def test_reflection_injected():
    a = agent([ChatResult(text="working…", model="m")] * 20, max_steps=5, reflect_every=2)
    a.run("x")
    joined = " ".join(str(m.get("content", "")) for m in a.history)
    assert "Briefly reflect" in joined


def test_compaction_triggers():
    long = "y" * 5000
    script = [ChatResult(text="", tool_calls=[
        {"tool": "write_file", "arguments": {"path": f"f{i}.txt", "content": long}}],
        model="m") for i in range(8)]
    script.append(ChatResult(text="FINAL: compacted ok", model="m"))
    a = agent(script, max_steps=12, history_char_budget=2000)
    assert a.run("write stuff") == "compacted ok"
    assert a.compactions >= 1


def test_trace_and_transcript_valid():
    a = agent([ChatResult(text="FINAL: t", model="m")])
    a.run("task abc")
    lines = open(a.trace_path).read().strip().splitlines()
    assert len(lines) >= 2
    for ln in lines:
        json.loads(ln)  # valid JSONL
    types = [json.loads(ln)["type"] for ln in lines]
    assert "task_start" in types and "task_done" in types
    assert open(a.transcript_path).read().startswith("# task abc")


def test_ask_tool_round_cap():
    a = agent([ChatResult(text="", tool_calls=[
        {"tool": "todo_add", "arguments": {"task": "t"}}], model="m")] * 10)
    a.ask("hi")  # must terminate despite endless tool calls
    assert len(a.history) > 2
    assert a.last_model == "m"


def test_memory_injection():
    a = agent([ChatResult(text="FINAL: z", model="m")])
    a.memory.save_fact("user likes Urdu poetry", "prefs")
    a.run("write an Urdu poem")
    sys_blobs = " ".join(str(m.get("content", "")) for m in a.history
                         if m["role"] == "system")
    assert "Urdu" in sys_blobs


def test_empty_and_weird_tasks():
    a = agent([ChatResult(text="FINAL: e", model="m")])
    assert a.run("") == "e"
    a2 = agent([ChatResult(text="FINAL: u", model="m")])
    assert a2.run("héllo ✓\n\t") == "u"


def test_crew_modes_offline():
    tmp = tempfile.mkdtemp()
    cfg = AgentConfig(workspace=tmp, approval="auto", max_steps=4)
    for mode in ("sequential", "hierarchical", "debate"):
        c = Crew(config=cfg, client=MockClient())
        out = c.run("T", mode=mode)
        assert isinstance(out, str) and len(out) > 0
    c = Crew(config=cfg, client=MockClient())
    assert "researcher" in c.run("T", mode="bogus-mode-still-runs-sequential")


def test_role_system_prompts():
    for role in ("assistant", "researcher", "coder", "critic", "planner", "bogus"):
        a = agent([ChatResult(text="FINAL: r", model="m")], )
        a.role = role
        assert isinstance(a._system(), str) and "```json" in a._system()
