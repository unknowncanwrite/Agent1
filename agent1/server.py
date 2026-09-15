"""Zero-dependency web server: REST API + chat UI (beats Dify/Flowise setup:
no Docker, no Node — one command).

Endpoints:
  GET  /                 chat UI
  GET  /api/models       free-model cascade + live discovery
  GET  /api/stats        token usage ($0.00 forever on :free)
  POST /api/chat  {message, mode}            single agent turn(s)
  POST /api/task  {task, mode, crew}         full autonomous run
"""
from __future__ import annotations

import json
import threading
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
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    # -- routes --
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            page = (WEB_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif self.path == "/api/models":
            assert self.config
            self._json({"cascade": self.config.cascade(),
                        "catalog": [{"id": m.id, "context": m.context,
                                     "best_for": m.best_for} for m in FREE_MODELS]})
        elif self.path == "/api/stats":
            assert self.agent
            self._json({"stats": self.agent.client.stats,
                        "tools": self.agent.tools.names()})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        assert self.agent and self.crew
        data = self._body()
        try:
            if self.path == "/api/chat":
                msg = data.get("message", "")
                mode = data.get("mode", "general")
                self.agent.task_kind = {"code": "code", "research": "research"}.get(mode, "general")
                self._json({"reply": self.agent.ask(msg)})
            elif self.path == "/api/task":
                task = data.get("task", "")
                if data.get("crew"):
                    reply = self.crew.run(task, data.get("crew"))
                else:
                    self.agent.task_kind = data.get("mode", "general")
                    reply = self.agent.run(task)
                self._json({"reply": reply, "steps": self.agent.steps})
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


def serve(host="0.0.0.0", port=8080):
    config = AgentConfig.load()
    events: list[dict] = []
    agent = Agent(config=config, on_event=events.append)
    crew = Crew(config=config, on_event=events.append)
    _Handler.agent, _Handler.crew, _Handler.config = agent, crew, config
    httpd = ThreadingHTTPServer((host, port), _Handler)
    print(f"\n  Agent1 Omni live at http://{host}:{port}  (FREE models, $0)\n")
    httpd.serve_forever()
