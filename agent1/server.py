"""Zero-dependency web server: REST API + chat UI (beats Dify/Flowise setup:
no Docker, no Node — one command).

Endpoints:
  GET  /                 chat UI
  GET  /api/models       free-model cascade + live discovery
  GET  /api/stats        token usage ($0.00 forever on :free)
  GET  /api/trace?limit  recent agent events (observability)
  GET  /api/todos        current plan
  POST /api/chat  {message, mode}            single agent turn(s)
  POST /api/task  {task, mode, crew}         full autonomous run
"""
from __future__ import annotations

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .agent import Agent
from .config import AgentConfig, FREE_MODELS
from .crew import Crew

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class _Handler(BaseHTTPRequestHandler):
    agent: Agent | None = None
    crew: Crew | None = None
    config: AgentConfig | None = None
    events: list = []

    def log_message(self, *a):
        pass

    # -- helpers --
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(n) if n else b"{}"
            obj = json.loads(raw or b"{}")
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    # -- routes --
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path.startswith("/index"):
            page = (WEB_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif parsed.path == "/api/models":
            assert self.config
            self._json({"cascade": self.config.cascade(),
                        "catalog": [{"id": m.id, "context": m.context,
                                     "best_for": m.best_for} for m in FREE_MODELS]})
        elif parsed.path == "/api/stats":
            assert self.agent
            self._json({"stats": self.agent.client.stats,
                        "tools": self.agent.tools.names(),
                        "model": getattr(self.agent, "last_model", ""),
                        "steps": self.agent.steps,
                        "demo": bool(self.config and self.config.demo)})
        elif parsed.path == "/api/trace":
            q = urllib.parse.parse_qs(parsed.query)
            try:
                limit = max(1, min(int(q.get("limit", ["50"])[0]), 500))
            except ValueError:
                limit = 50
            evs = (self.events or [])[-limit:]
            self._json({"events": [
                {k: (str(v)[:800] if not isinstance(v, (int, float)) else v)
                 for k, v in e.items()} for e in evs]})
        elif parsed.path == "/api/todos":
            assert self.agent
            self._json({"todos": self.agent.tools.todos})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        assert self.agent and self.crew
        data = self._body()
        try:
            if self.path == "/api/chat":
                msg = str(data.get("message", ""))[:8000]
                if not msg.strip():
                    return self._json({"error": "message is empty"}, 400)
                self.agent.task_kind = {"code": "code", "research": "research"}.get(
                    str(data.get("mode", "general")), "general")
                reply = self.agent.ask(msg)
                self._json({"reply": reply, "model": self.agent.last_model,
                            "stats": self.agent.client.stats})
            elif self.path == "/api/task":
                task = str(data.get("task", ""))[:12000]
                if not task.strip():
                    return self._json({"error": "task is empty"}, 400)
                if data.get("crew"):
                    reply = self.crew.run(task, str(data.get("crew")))
                else:
                    self.agent.task_kind = str(data.get("mode", "general"))
                    reply = self.agent.run(task)
                self._json({"reply": reply, "steps": self.agent.steps,
                            "model": self.agent.last_model,
                            "stats": self.agent.client.stats})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e)[:1000]}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def build_server(host="0.0.0.0", port=8080, client=None):
    """Construct (httpd, agent, crew) without serving — test-friendly."""
    from .llm import MockClient
    config = AgentConfig.load()
    events: list[dict] = []
    if client is None and config.demo:
        client = MockClient()
    agent = Agent(config=config, client=client, on_event=events.append)
    crew = Crew(config=config, client=client, on_event=events.append)
    _Handler.agent, _Handler.crew = agent, crew
    _Handler.config, _Handler.events = config, events
    return ThreadingHTTPServer((host, port), _Handler), agent, crew


def serve(host="0.0.0.0", port=8080):
    httpd, _, _ = build_server(host, port)
    print(f"\n  Agent1 Omni live at http://{host}:{port}  (FREE models, $0)\n")
    httpd.serve_forever()
