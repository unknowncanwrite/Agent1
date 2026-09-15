import tempfile
from agent1.agent import Agent
from agent1.config import AgentConfig
from agent1.crew import Crew
from agent1.llm import MockClient, ChatResult


def _agent(script):
    tmp = tempfile.mkdtemp()
    cfg = AgentConfig(workspace=tmp, approval="auto", max_steps=6)
    return Agent(config=cfg, client=MockClient(script))


def test_tool_loop_and_final():
    agent = _agent([
        ChatResult(text="", tool_calls=[
            {"tool": "write_file", "arguments": {"path": "note.txt", "content": "hi"}}],
            model="mock"),
        ChatResult(text="FINAL: file created and verified.", model="mock"),
    ])
    out = agent.run("create note.txt")
    assert "created" in out
    assert agent.steps >= 1


def test_crew_sequential_offline():
    tmp = tempfile.mkdtemp()
    cfg = AgentConfig(workspace=tmp, approval="auto", max_steps=4)
    crew = Crew(config=cfg, client=MockClient())
    out = crew.run("do something", mode="sequential")
    assert "researcher" in out and "coder" in out and "critic" in out


def test_cascade_ordering():
    from agent1.config import model_cascade_for
    code = model_cascade_for("code")
    assert "coder" in code[0] or "laguna" in code[0]
    assert all(m.endswith(":free") for m in code)
