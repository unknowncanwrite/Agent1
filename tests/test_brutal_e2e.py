"""End-to-end: CLI doctor/models/demo, plugins, chat-EOF, patch roundtrip."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_cli(*args, env=None, inp=None, timeout=120):
    e = dict(os.environ)
    e.pop("OPENROUTER_API_KEY", None)
    e["AGENT1_WORKSPACE"] = tempfile.mkdtemp()
    if env:
        e.update(env)
    return subprocess.run([sys.executable, "-m", "agent1.cli", *args],
                          cwd=ROOT, capture_output=True, text=True,
                          input=inp, timeout=timeout, env=e)


def test_doctor_fast_and_graceful():
    t0 = time.time()
    r = run_cli("doctor", timeout=60)
    assert r.returncode == 0, r.stderr
    assert "doctor" in r.stdout.lower()
    assert "OPENROUTER_API_KEY" in r.stdout
    assert "cascade" in r.stdout
    assert time.time() - t0 < 45  # never hangs


def test_models_demo():
    r = run_cli("models", "--demo")
    assert r.returncode == 0
    assert ":free" in r.stdout


def test_run_demo():
    r = run_cli("run", "hello world", "--demo", "-v")
    assert r.returncode == 0, r.stderr
    assert "cost=$0.00" in r.stdout and "trace=" in r.stdout


def test_crew_demo_all_modes():
    for mode in ("sequential", "hierarchical", "debate"):
        r = run_cli("crew", "T", "--mode", mode, "--demo", timeout=180)
        assert r.returncode == 0, f"{mode}: {r.stderr}"


def test_chat_eof_and_empty():
    r = run_cli("chat", "--demo", inp="")  # immediate EOF
    assert r.returncode == 0, r.stderr
    r = run_cli("chat", "--demo", inp="hello\n\n")
    assert r.returncode == 0 and "(transcript:" in r.stdout


def test_plugins_e2e():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "rev.py").write_text(
            "from agent1.tools import Tool\n"
            "def register(r):\n"
            "    r.register(Tool('rev', 'reverse', {'type':'object','properties':{'t':{'type':'string'}}},"
            " lambda a: a.get('t','')[::-1]))\n")
        from agent1.agent import Agent
        from agent1.config import AgentConfig
        from agent1.llm import MockClient, ChatResult
        cfg = AgentConfig(workspace=tempfile.mkdtemp(), approval="auto",
                          max_steps=4, plugins_dir=tmp)
        a = Agent(config=cfg, client=MockClient([ChatResult(text="FINAL: p", model="m")]))
        assert "rev" in a.tools.names()
        assert a.tools.execute("rev", {"t": "abc"}) == "cba"


def test_patch_roundtrip_big():
    from agent1.tools import ToolRegistry
    with tempfile.TemporaryDirectory() as tmp:
        t = ToolRegistry(workspace=tmp, approval="auto")
        t.execute("write_file", {"path": "code.py",
                                 "content": "a = 1\nb = 2\nc = 3\nprint(a)\n"})
        diff = ("--- a/code.py\n+++ b/code.py\n@@ -1,4 +1,4 @@\n"
                " a = 1\n-b = 2\n+b = 20\n c = 3\n print(a)\n")
        assert "Patched" in t.execute("apply_patch", {"diff": diff})
        assert "b = 20" in t.execute("read_file", {"path": "code.py"})


def test_demo_env_var():
    r = run_cli("run", "x", env={"AGENT1_DEMO": "1"})
    assert r.returncode == 0, r.stderr
    assert "Mock final" in r.stdout  # proves MockClient engaged, not a network fail
    # direct loader check
    import os as _os
    from agent1.config import AgentConfig
    old = _os.environ.get("AGENT1_DEMO")
    try:
        _os.environ["AGENT1_DEMO"] = "1"
        assert AgentConfig.load().demo is True
        _os.environ["AGENT1_DEMO"] = "0"
        assert AgentConfig.load().demo is False
    finally:
        if old is None:
            _os.environ.pop("AGENT1_DEMO", None)
        else:
            _os.environ["AGENT1_DEMO"] = old
