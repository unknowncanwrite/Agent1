"""Toolbelt: everything top agents have, in one dependency-free file.

OpenHands/SWE-agent need Docker + setup. Agent1 tools run anywhere with
just Python: files, sandboxed shell, python runner, keyless web search
+ fetch, persistent memory hooks, and a todo planner. All tools expose
OpenAI-function schemas (MCP-style portable) and are audit-logged.
"""
from __future__ import annotations

import difflib
import html as _html
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# ---------------- helpers ----------------

def _safe_path(root: Path, p: str) -> Path:
    target = (root / p).resolve()
    if target != root.resolve() and root.resolve() not in target.parents:
        raise PermissionError(f"Path escapes workspace: {p}")
    return target


def _html_to_text(data: bytes, limit: int = 8000) -> str:
    try:
        text = data.decode("utf-8", "ignore")
    except Exception:
        return ""
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]*>", " ", text)
    text = _html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()[:limit]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[[dict], str]

    def schema(self) -> dict:
        return {"name": self.name, "description": self.description,
                "parameters": self.parameters}


DANGEROUS = re.compile(
    r"(rm\s+-rf\s+/(?:\s|$)|\brm\b.*\s+/\s|mkfs|dd\s+of=|:\s*\(\s*\)\s*\{|shutdown|reboot|"
    r"curl[^|]*\|\s*(ba)?sh|wget[^|]*\|\s*(ba)?sh)", re.I)


class ToolRegistry:
    def __init__(self, workspace: str = "./workspace",
                 approval: str = "safe", memory=None,
                 audit_log: str | None = None):
        self.root = Path(workspace).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.approval = approval  # auto | safe | manual
        self.memory = memory
        self.audit_log = audit_log
        self.todos: list[dict] = []
        self._tools: dict[str, Tool] = {}
        self._register_all()

    # ----- plumbing -----
    def _log(self, name: str, args: dict, out: str):
        if not self.audit_log:
            return
        try:
            with open(self.audit_log, "a") as f:
                f.write(json.dumps({"tool": name, "args": args,
                                    "out": out[:2000]}) + "\n")
        except Exception:
            pass

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def openai_tools(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    def describe(self) -> str:
        lines = []
        for t in self._tools.values():
            props = t.parameters.get("properties", {})
            req = t.parameters.get("required", [])
            args = ", ".join(f"{k}{'' if k in req else '?'}"
                             for k in props) or "none"
            lines.append(f"- {t.name}({args}): {t.description}")
        return "\n".join(lines)

    def _approve(self, name: str, args: dict) -> str | None:
        """Return denial message, or None if approved."""
        cmd = str(args.get("command", "")) + str(args.get("code", ""))
        if DANGEROUS.search(cmd):
            return "BLOCKED: command matches destructive pattern."  # all modes
        if self.approval == "auto":
            return None
        risky = name in ("bash", "python_run", "write_file", "edit_file")
        if self.approval == "manual" and risky:
            try:
                ans = input(f"\nApprove {name} {json.dumps(args)[:300]}? [y/N] ").strip()
                return None if ans.lower() in ("y", "yes") else "Denied by user."
            except EOFError:
                return "Denied (non-interactive)."
        return None  # safe: destructive blocked, rest auto-approved

    def execute(self, name: str, args: dict | None = None) -> str:
        if not isinstance(args, dict):
            return f"ERROR: args for '{name}' must be an object, got {type(args).__name__}."
        if not isinstance(name, str) or not name:
            return "ERROR: tool name must be a non-empty string."
        tool = self._tools.get(name)
        if not tool:
            msg = f"ERROR: unknown tool '{name}'. Available: {', '.join(self.names())}"
            self._log(name if isinstance(name, str) else "?", args, msg)
            return msg
        missing = [k for k in tool.parameters.get("required", []) if k not in args]
        if missing:
            msg = f"ERROR: '{name}' missing required args: {', '.join(missing)}."
            self._log(name, args, msg)
            return msg
        denied = self._approve(name, args)
        if denied:
            self._log(name, args, denied)
            return denied
        try:
            out = tool.func(args)
        except Exception as e:
            out = f"ERROR in {name}: {e}"
        self._log(name, args, out)
        return out

    # ----- tools -----
    def _register_all(self):
        S = {"type": "object"}
        self.register(Tool("read_file", "Read a file from the workspace.",
            {"type": "object", "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer", "default": 2000}}, "required": ["path"]},
            self._read_file))
        self.register(Tool("write_file", "Create/overwrite a file in the workspace.",
            {"type": "object", "properties": {
                "path": {"type": "string"}, "content": {"type": "string"}},
             "required": ["path", "content"]}, self._write_file))
        self.register(Tool("edit_file", "Fuzzy-match old_text and replace with new_text.",
            {"type": "object", "properties": {
                "path": {"type": "string"}, "old_text": {"type": "string"},
                "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]},
            self._edit_file))
        self.register(Tool("list_files", "List files/dirs under a workspace path.",
            {"type": "object", "properties": {
                "path": {"type": "string", "default": "."},
                "pattern": {"type": "string", "default": "*"}}, "required": []},
            self._list_files))
        self.register(Tool("bash", "Run a shell command in the workspace (timeout 60s).",
            {"type": "object", "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 60}}, "required": ["command"]},
            self._bash))
        self.register(Tool("python_run", "Run Python code (timeout 60s).",
            {"type": "object", "properties": {
                "code": {"type": "string"},
                "timeout": {"type": "integer", "default": 60}}, "required": ["code"]},
            self._python_run))
        self.register(Tool("web_search", "Keyless web search. Returns titles/urls/snippets.",
            {"type": "object", "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer", "default": 5}}, "required": ["query"]},
            self._web_search))
        self.register(Tool("web_fetch", "Fetch a URL and return cleaned text.",
            {"type": "object", "properties": {
                "url": {"type": "string"}, "limit": {"type": "integer", "default": 8000}},
             "required": ["url"]}, self._web_fetch))
        self.register(Tool("remember", "Save a fact to long-term memory.",
            {"type": "object", "properties": {
                "fact": {"type": "string"}, "topic": {"type": "string", "default": "general"}},
             "required": ["fact"]}, self._remember))
        self.register(Tool("recall", "Search long-term memory.",
            {"type": "object", "properties": {"query": {"type": "string"}},
             "required": ["query"]}, self._recall))
        self.register(Tool("todo_add", "Add a plan step.",
            {"type": "object", "properties": {"task": {"type": "string"}},
             "required": ["task"]}, self._todo_add))
        self.register(Tool("todo_done", "Mark plan step N done (1-based).",
            {"type": "object", "properties": {"n": {"type": "integer"}},
             "required": ["n"]}, self._todo_done))
        self.register(Tool("todo_list", "Show the plan.", S, lambda a: self._todo_list()))
        self.register(Tool("grep", "Regex search across workspace files. Returns file:line matches.",
            {"type": "object", "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "glob": {"type": "string", "default": "*"},
                "ignore_case": {"type": "boolean", "default": False}}, "required": ["pattern"]},
            self._grep))
        self.register(Tool("apply_patch", "Apply a unified diff to workspace files (multi-file edits).",
            {"type": "object", "properties": {
                "diff": {"type": "string"}}, "required": ["diff"]},
            self._apply_patch))

    # -- implementations --
    def _read_file(self, a: dict) -> str:
        p = _safe_path(self.root, a["path"])
        if not p.exists():
            return f"ERROR: not found: {a['path']}"
        lines = p.read_text(errors="ignore").splitlines()
        lim = int(a.get("limit", 2000))
        out = "\n".join(f"{i+1:4d} {l}" for i, l in enumerate(lines[:lim]))
        if len(lines) > lim:
            out += f"\n... ({len(lines)-lim} more lines)"
        return out or "(empty file)"

    def _write_file(self, a: dict) -> str:
        p = _safe_path(self.root, a["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a.get("content", ""))
        return f"Wrote {len(a.get('content',''))} chars to {a['path']}"

    def _edit_file(self, a: dict) -> str:
        p = _safe_path(self.root, a["path"])
        if not p.exists():
            return f"ERROR: not found: {a['path']}"
        src = p.read_text(errors="ignore")
        old, new = a["old_text"], a["new_text"]
        if old in src:
            p.write_text(src.replace(old, new, 1))
            return "Edited (exact match)."
        # fuzzy fallback
        best, ratio = "", 0.0
        for chunk in [src[i:i+len(old)+200] for i in range(0, max(len(src), 1), 400)] or [""]:
            r = difflib.SequenceMatcher(None, old, chunk).ratio()
            if r > ratio:
                best, ratio = chunk, r
        if ratio > 0.7:
            p.write_text(src.replace(best, new, 1))
            return f"Edited (fuzzy match {ratio:.2f})."
        return "ERROR: old_text not found (no close match)."

    def _list_files(self, a: dict) -> str:
        p = _safe_path(self.root, a.get("path", "."))
        if not p.exists():
            return f"ERROR: not found: {a.get('path')}"
        pat = a.get("pattern", "*")
        items = sorted(p.rglob(pat) if "*" in pat or "?" in pat else p.iterdir())
        out = [str(i.relative_to(self.root)) + ("/" if i.is_dir() else "")
               for i in items[:200]]
        return "\n".join(out) or "(empty)"

    def _bash(self, a: dict) -> str:
        cmd = a["command"]
        try:
            r = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True,
                               text=True, timeout=int(a.get("timeout", 60)))
            out = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
            return f"[exit {r.returncode}]\n" + (out.strip()[:6000] or "(no output)")
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out."

    def _python_run(self, a: dict) -> str:
        code = a["code"]
        try:
            r = subprocess.run(["python3", "-c", code], cwd=self.root,
                               capture_output=True, text=True,
                               timeout=int(a.get("timeout", 60)))
            out = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
            return f"[exit {r.returncode}]\n" + (out.strip()[:6000] or "(no output)")
        except subprocess.TimeoutExpired:
            return "ERROR: python timed out."

    def _web_search(self, a: dict) -> str:
        q = urllib.parse.quote(a.get("query", ""))
        if not q:
            return "ERROR: query is empty."
        page = ""
        last_err: Exception | None = None
        for url in (f"https://html.duckduckgo.com/html/?q={q}",
                    f"https://lite.duckduckgo.com/lite/?q={q}"):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=25) as r:
                    page = r.read().decode("utf-8", "ignore")
                break
            except Exception as e:
                last_err = e
        if not page:
            return f"ERROR: search failed: {last_err}"
        hits = re.findall(r'(?is)<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
                          r'class="result__snippet"[^>]*>(.*?)</a>' , page)
        if not hits:
            hits = re.findall(r'(?is)<a[^>]*class="result__a"[^>]*>(.*?)</a>', page)
            links = re.findall(r'result__a[^h]*href="([^"]+)"', page)
            hits = list(zip(links, hits, [""] * len(hits)))
        out = []
        for i, (link, title, snip) in enumerate(hits[:int(a.get("count", 5))]):
            title = re.sub(r"<[^>]+>", "", title).strip()
            snip = re.sub(r"<[^>]+>", "", snip).strip()
            if link.startswith("//"):
                link = "https:" + link
            out.append(f"{i+1}. {title}\n   {link}\n   {snip[:300]}")
        return "\n\n".join(out) or "No results."

    def _web_fetch(self, a: dict) -> str:
        req = urllib.request.Request(a["url"], headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if int(r.headers.get("Content-Length", 0) or 0) > 2_000_000:
                    return "ERROR: page too large."
                return f"URL: {a['url']}\n\n" + _html_to_text(r.read(), int(a.get("limit", 8000)))
        except Exception as e:
            return f"ERROR: fetch failed: {e}"

    def _remember(self, a: dict) -> str:
        if not self.memory:
            return "Memory not enabled."
        self.memory.save_fact(a["fact"], a.get("topic", "general"))
        return "Saved."

    def _recall(self, a: dict) -> str:
        if not self.memory:
            return "Memory not enabled."
        hits = self.memory.search(a["query"])
        return "\n".join(f"- [{t}] {f}" for t, f in hits) or "No memories."

    def _todo_add(self, a: dict) -> str:
        self.todos.append({"task": a["task"], "done": False})
        return f"Step {len(self.todos)} added."

    def _todo_done(self, a: dict) -> str:
        n = int(a["n"]) - 1
        if 0 <= n < len(self.todos):
            self.todos[n]["done"] = True
            return f"Step {n+1} done."
        return "ERROR: bad step number."

    def _todo_list(self) -> str:
        if not self.todos:
            return "(no plan yet)"
        return "\n".join(f"{'[x]' if t['done'] else '[ ]'} {i+1}. {t['task']}"
                         for i, t in enumerate(self.todos))

    def _grep(self, a: dict) -> str:
        import fnmatch
        try:
            rx = re.compile(a["pattern"], re.I if a.get("ignore_case") else 0)
        except re.error as e:
            return f"ERROR: bad regex: {e}"
        try:
            base = _safe_path(self.root, a.get("path", "."))
        except PermissionError as e:
            return f"ERROR: {e}"
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = [p for p in base.rglob("*")
                     if p.is_file() and ".trace" not in p.parts
                     and not any(part.startswith(".") for part in p.relative_to(self.root).parts)]
        else:
            return f"ERROR: not found: {a.get('path')}"
        glob = a.get("glob", "*")
        hits, scanned = [], 0
        for p in sorted(files)[:2000]:
            if not fnmatch.fnmatch(p.name, glob):
                continue
            try:
                if p.stat().st_size > 500_000:
                    continue
                text = p.read_text(errors="strict")
            except Exception:
                continue  # binary / unreadable
            scanned += 1
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    rel = p.relative_to(self.root)
                    hits.append(f"{rel}:{i}: {line.strip()[:200]}")
                    if len(hits) >= 60:
                        return "\n".join(hits) + "\n…(capped at 60 hits)"
        return "\n".join(hits) or f"No matches (scanned {scanned} files)."

    def _apply_patch(self, a: dict) -> str:
        """Minimal unified-diff applier: ---/+++ headers + @@ hunks, context-aware."""
        diff = a.get("diff", "")
        if not diff.strip():
            return "ERROR: empty diff."
        cur_file: Path | None = None
        hunks: list[tuple[Path, list[str]]] = []
        buf: list[str] = []
        old: str | None = None
        for raw in diff.splitlines():
            line = raw.rstrip("\n")
            if line.startswith("--- "):
                old = line[4:].strip().removeprefix("a/").removeprefix("b/")
            elif line.startswith("+++ "):
                new = line[4:].strip().removeprefix("a/").removeprefix("b/")
                if cur_file and buf:
                    hunks.append((cur_file, buf))
                buf = []
                try:
                    cur_file = _safe_path(self.root, new if new != "/dev/null" else (old or ""))
                except PermissionError as e:
                    return f"ERROR: {e}"
            elif line.startswith("@@"):
                buf.append(line)
            elif cur_file is not None and (line.startswith((" ", "+", "-")) or line == ""):
                buf.append(line)
        if cur_file and buf:
            hunks.append((cur_file, buf))
        if not hunks:
            return "ERROR: no parseable hunks (need ---/+++/@@ headers)."
        applied = []
        for path, hunk_lines in hunks:
            ok, msg = self._apply_hunks(path, hunk_lines)
            if not ok:
                return f"ERROR applying to {path.name}: {msg} (earlier files kept: {applied})"
            applied.append(str(path.relative_to(self.root)))
        return "Patched: " + ", ".join(applied)

    def _apply_hunks(self, path: Path, hunk_lines: list[str]) -> tuple[bool, str]:
        lines = path.read_text(errors="ignore").splitlines() if path.exists() else []
        out: list[str] = []
        i = 0  # cursor in original
        j = 0
        hunk_re = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
        while j < len(hunk_lines):
            m = hunk_re.match(hunk_lines[j])
            if not m:
                j += 1
                continue
            start = int(m.group(1))
            # copy through to hunk start (1-based, forgiving)
            while i < min(start - 1, len(lines)):
                out.append(lines[i]); i += 1
            j += 1
            while j < len(hunk_lines) and not hunk_lines[j].startswith("@@"):
                h = hunk_lines[j]
                if h.startswith("\\"):
                    j += 1
                    continue  # "\ No newline at end of file"
                if h.startswith("+") and not h.startswith("+++"):
                    out.append(h[1:])
                elif h.startswith("-") and not h.startswith("---"):
                    i += 1  # drop original line
                else:  # context (or bare line treated as context)
                    out.append(h[1:] if h.startswith(" ") else h)
                    i += 1
                j += 1
        out.extend(lines[i:])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(out) + ("\n" if out else ""))
        except Exception as e:
            return False, str(e)
        return True, "ok"


def load_plugins(registry: ToolRegistry, plugins_dir: str) -> list[str]:
    """Load extra tools from *.py files. Each may define register(registry).
    Only runs when AGENT1_PLUGINS is set — off by default for safety."""
    import importlib.util
    loaded = []
    base = Path(plugins_dir or "")
    if not plugins_dir or not base.is_dir():
        return loaded
    for f in sorted(base.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(f"a1plug_{f.stem}", f)
            if not spec or not spec.loader:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(registry)
                loaded.append(f.stem)
        except Exception:
            continue
    return loaded
