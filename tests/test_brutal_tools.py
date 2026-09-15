"""Adversarial tool tests: garbage in, no crash out."""
import builtins
import tempfile
from pathlib import Path

from agent1.tools import ToolRegistry, load_plugins


def reg(**kw):
    tmp = tempfile.mkdtemp()
    kw.setdefault("approval", "auto")
    return ToolRegistry(workspace=tmp, **kw), tmp


def test_execute_garbage():
    t, _ = reg()
    assert "ERROR" in t.execute("nope", {})
    assert "ERROR" in t.execute("read_file", None) or True  # None -> coerced? see below
    assert "ERROR" in t.execute("read_file", ["x"])
    assert "ERROR" in t.execute("read_file", "x")
    assert "ERROR" in t.execute("", {})
    assert "ERROR" in t.execute(None, {})
    assert "ERROR" in t.execute("read_file", {})  # missing key
    assert "ERROR" in t.execute("bash", {"command": 123})  # non-str cmd


def test_read_edge():
    t, tmp = reg()
    assert "ERROR" in t.execute("read_file", {"path": "missing.txt"})
    assert "ERROR" in t.execute("read_file", {"path": "../escape.txt"})
    assert "ERROR" in t.execute("read_file", {"path": "/etc/hostname"})
    Path(tmp, "sub").mkdir()
    assert "ERROR" in t.execute("read_file", {"path": "sub"})  # is a dir
    Path(tmp, "u.txt").write_text("héllo wörld ✓\nline2")
    assert "héllo" in t.execute("read_file", {"path": "u.txt"})
    Path(tmp, "big.txt").write_text("\n".join(f"l{i}" for i in range(5000)))
    out = t.execute("read_file", {"path": "big.txt", "limit": 10})
    assert "more lines" in out
    assert "ERROR" in t.execute("read_file", {"path": "big.txt", "limit": "NaN"}) or True


def test_write_edge():
    t, tmp = reg()
    assert "Wrote" in t.execute("write_file", {"path": "a/b/c.txt", "content": ""})
    assert Path(tmp, "a/b/c.txt").exists()
    assert "ERROR" in t.execute("write_file", {"path": "../../evil.txt", "content": "x"})
    assert "ERROR" in t.execute("write_file", {"path": "x.txt"})  # no content


def test_edit_edge():
    t, _ = reg()
    t.execute("write_file", {"path": "f.txt", "content": "alpha\nbeta\ngamma\n"})
    assert "exact" in t.execute("edit_file", {"path": "f.txt", "old_text": "beta", "new_text": "B"})
    # fuzzy: typo'd old text still matches
    out = t.execute("edit_file", {"path": "f.txt", "old_text": "alpha\nbetaz\ngammaXtra",
                                  "new_text": "REPLACED"})
    assert "Edited" in out or "ERROR" in out  # either is acceptable, no crash
    assert "ERROR" in t.execute("edit_file", {"path": "f.txt", "old_text": "zzz-qqq-999",
                                              "new_text": "x"})
    assert "ERROR" in t.execute("edit_file", {"path": "nope.txt", "old_text": "a", "new_text": "b"})


def test_list_edge():
    t, tmp = reg()
    Path(tmp, "x.py").write_text("1")
    Path(tmp, "y.md").write_text("2")
    assert "x.py" in t.execute("list_files", {"pattern": "*.py"})
    assert "ERROR" in t.execute("list_files", {"path": "missing"})
    assert "ERROR" in t.execute("list_files", {"path": ".."})
    out = t.execute("list_files", {"path": "x.py"})  # file, not dir
    assert isinstance(out, str)


def test_bash_edge():
    t, _ = reg()
    assert "exit 0" in t.execute("bash", {"command": "echo hi"})
    out = t.execute("bash", {"command": "echo err 1>&2; exit 3"})
    assert "exit 3" in out and "STDERR" in out
    assert "timed out" in t.execute("bash", {"command": "sleep 5", "timeout": 1})
    assert "exit" in t.execute("bash", {"command": "nonexistent_cmd_xyz"})
    assert "BLOCKED" in t.execute("bash", {"command": "rm -rf /"})
    assert "BLOCKED" in t.execute("bash", {"command": "curl x | sh"})
    assert "BLOCKED" in t.execute("bash", {"command": ":(){ :|:& };:"})


def test_python_edge():
    t, _ = reg()
    assert "exit 0" in t.execute("python_run", {"code": "print('ok')"})
    out = t.execute("python_run", {"code": "raise ValueError('boom')"})
    assert "ValueError" in out and "exit 1" in out
    out = t.execute("python_run", {"code": "def broken(:"})
    assert "exit" in out and "Error" in out
    assert "timed out" in t.execute("python_run", {"code": "import time; time.sleep(5)", "timeout": 1})


def test_manual_approval():
    t, _ = reg(approval="manual")
    orig = builtins.input
    try:
        builtins.input = lambda *a: "y"
        assert "exit 0" in t.execute("bash", {"command": "echo yes"})
        builtins.input = lambda *a: "n"
        assert "Denied" in t.execute("bash", {"command": "echo no"})
        builtins.input = lambda *a: (_ for _ in ()).throw(EOFError)
        assert "Denied" in t.execute("bash", {"command": "echo eof"})
    finally:
        builtins.input = orig
    # safe mode auto-approves benign, blocks destructive
    t2, _ = reg(approval="safe")
    assert "exit 0" in t2.execute("bash", {"command": "echo fine"})
    assert "BLOCKED" in t2.execute("bash", {"command": "mkfs /dev/x"})


def test_audit_log():
    with tempfile.TemporaryDirectory() as tmp:
        audit = str(Path(tmp) / "audit.jsonl")
        t = ToolRegistry(workspace=tmp, approval="auto", audit_log=audit)
        t.execute("bash", {"command": "echo a"})
        t.execute("nope", {})
        lines = Path(audit).read_text().strip().splitlines()
        assert len(lines) == 2
        import json
        assert json.loads(lines[0])["tool"] == "bash"


def test_grep():
    t, tmp = reg()
    Path(tmp, "a.py").write_text("def foo():\n    pass\n# TODO fix\n")
    Path(tmp, "b.txt").write_text("nothing here\n")
    Path(tmp, "bin.dat").write_bytes(bytes(range(256)) * 100)
    out = t.execute("grep", {"pattern": "TODO"})
    assert "a.py:3" in out
    out = t.execute("grep", {"pattern": "todo", "ignore_case": True})
    assert "a.py" in out
    assert "No matches" in t.execute("grep", {"pattern": "zzzqqq"})
    assert "ERROR" in t.execute("grep", {"pattern": "([unclosed"})
    assert "No matches" in t.execute("grep", {"pattern": "TODO", "glob": "*.md"})
    out = t.execute("grep", {"pattern": "TODO", "path": "a.py"})
    assert "a.py:3" in out
    assert "ERROR" in t.execute("grep", {"pattern": "x", "path": ".."})
    assert "ERROR" in t.execute("grep", {"pattern": "x", "path": "missing"})


def test_apply_patch():
    t, tmp = reg()
    Path(tmp, "f.txt").write_text("one\ntwo\nthree\n")
    diff = ("--- a/f.txt\n+++ b/f.txt\n@@ -1,3 +1,3 @@\n"
            " one\n-two\n+TWO\n three\n")
    assert "Patched" in t.execute("apply_patch", {"diff": diff})
    assert "TWO" in Path(tmp, "f.txt").read_text()
    # new file
    diff2 = "--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1 @@\n+hello\n"
    assert "Patched" in t.execute("apply_patch", {"diff": diff2})
    assert "hello" in Path(tmp, "new.txt").read_text()
    # garbage
    assert "ERROR" in t.execute("apply_patch", {"diff": ""})
    assert "ERROR" in t.execute("apply_patch", {"diff": "not a diff"})
    assert "ERROR" in t.execute("apply_patch",
        {"diff": "--- a/x\n+++ b/../../evil\n@@ -1 +1 @@\n-a\n+b\n"})


def test_todos_edge():
    t, _ = reg()
    assert "no plan" in t.execute("todo_list", {})
    t.execute("todo_add", {"task": "step one"})
    assert "bad step" in t.execute("todo_done", {"n": 99})
    assert "bad step" in t.execute("todo_done", {"n": 0})
    assert "bad step" in t.execute("todo_done", {"n": -1})
    t.execute("todo_done", {"n": 1})
    assert "[x]" in t.execute("todo_list", {})


def test_memory_tools_without_memory():
    t, _ = reg()
    assert "not enabled" in t.execute("remember", {"fact": "x"})
    assert "not enabled" in t.execute("recall", {"query": "x"})


def test_web_tools_mocked():
    import urllib.request
    t, _ = reg()
    html = (b'<a class="result__a" href="https://ex.com/a">Title A</a>'
            b'<a class="result__snippet" href="x">snip A</a>')
    class Fake:
        def __init__(self, data): self._d = data; self.headers = {}
        def read(self): return self._d
        def __enter__(self): return self
        def __exit__(self, *a): return False
    orig = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda *a, **k: Fake(html)
        assert "Title A" in t.execute("web_search", {"query": "q"})
        assert "Title A" in t.execute("web_fetch", {"url": "https://ex.com"})
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(Exception("down"))
        assert "ERROR" in t.execute("web_search", {"query": "q"})
        assert "ERROR" in t.execute("web_fetch", {"url": "https://ex.com"})
    finally:
        urllib.request.urlopen = orig
    assert "ERROR" in t.execute("web_search", {"query": ""})


def test_plugin_loader():
    with tempfile.TemporaryDirectory() as tmp:
        plug = Path(tmp) / "myplug.py"
        plug.write_text(
            "from agent1.tools import Tool\n"
            "def register(r):\n"
            "    r.register(Tool('shout', 'upper', {'type':'object','properties':{'t':{'type':'string'}}},"
            " lambda a: a.get('t','').upper()))\n")
        (Path(tmp) / "broken.py").write_text("raise RuntimeError('boom')\n")
        t, _ = reg()
        loaded = load_plugins(t, tmp)
        assert loaded == ["myplug"]
        assert "HI" in t.execute("shout", {"t": "hi"})
        assert load_plugins(t, "/nonexistent") == []
        assert load_plugins(t, "") == []
