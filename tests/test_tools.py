import tempfile
from agent1.tools import ToolRegistry


def test_files_and_bash():
    with tempfile.TemporaryDirectory() as tmp:
        t = ToolRegistry(workspace=tmp, approval="auto")
        assert "Wrote" in t.execute("write_file", {"path": "a.txt", "content": "hello"})
        assert "hello" in t.execute("read_file", {"path": "a.txt"})
        assert "Edited" in t.execute("edit_file", {"path": "a.txt",
            "old_text": "hello", "new_text": "hi"})
        assert "a.txt" in t.execute("list_files", {})
        out = t.execute("bash", {"command": "echo ok"})
        assert "ok" in out
        out = t.execute("python_run", {"code": "print(2+2)"})
        assert "4" in out


def test_sandbox_escape_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        t = ToolRegistry(workspace=tmp, approval="auto")
        out = t.execute("read_file", {"path": "../../etc/hostname"})
        assert "ERROR" in out or "escapes" in out


def test_dangerous_blocked_in_safe_mode():
    with tempfile.TemporaryDirectory() as tmp:
        t = ToolRegistry(workspace=tmp, approval="safe")
        out = t.execute("bash", {"command": "rm -rf /"})
        assert "BLOCKED" in out
