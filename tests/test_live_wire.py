"""WIRE-LIVE integration tests: real HTTP against fake OpenRouter + fake web.

No mocks — a real localhost OpenRouter-compatible server, the REAL
OpenRouterClient, the REAL Agent + tools. Proves the full loop works
over the wire (the sandbox firewall blocks real LLM hosts, so this is
the strongest live test possible here; run examples/05_live_smoke.py
on a normal network for true live validation).
"""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent1.agent import Agent
from agent1.config import AgentConfig
from agent1.llm import OpenRouterClient
from agent1.tools import ToolRegistry


class FakeOpenRouter(BaseHTTPRequestHandler):
    """Scripted OpenRouter: /models + /chat/completions with 429 rotation."""
    script: list = []
    requests: list = []
    n_429: int = 0  # fail this many chat requests with 429 first

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/models":
            self._json({"data": [{"id": "fakelab/nova:free"},
                                 {"id": "fakelab/paid-pro"},
                                 {"id": "meta-llama/llama-3.3-70b-instruct:free"}]})
        else:
            self._json({"error": "nope"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n) or b"{}")
        type(self).requests.append(payload)
        if type(self).n_429 > 0:
            type(self).n_429 -= 1
            self._json({"error": {"message": "rate limited"}}, 429)
            return
        if not type(self).script:
            self._json({"choices": [{"message": {"content": "FINAL: script empty"}}],
                        "usage": {}})
            return
        msg = type(self).script.pop(0)
        self._json({"choices": [{"message": msg}],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 10}})


def serve(handler):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def test_wire_discovery_and_rotation_and_tools():
    FakeOpenRouter.script = [
        {"content": "", "tool_calls": [{"function": {
            "name": "write_file",
            "arguments": json.dumps({"path": "hello.txt", "content": "live-wire-hi"})}}]},
        {"content": 'Verified via markdown fallback:\n```json\n'
                    '{"tool": "read_file", "arguments": {"path": "hello.txt"}}\n```'},
        {"content": "FINAL: hello.txt created and verified over the wire."},
    ]
    FakeOpenRouter.requests = []
    FakeOpenRouter.n_429 = 3  # first model's 3 _post retries all 429
    httpd = serve(FakeOpenRouter)
    try:
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        cfg = AgentConfig(api_key="wire-test", base_url=base,
                          workspace=tempfile.mkdtemp(), approval="auto", max_steps=8)
        client = OpenRouterClient(cfg)
        # live discovery
        assert client.discover_free_models() == [
            "fakelab/nova:free", "meta-llama/llama-3.3-70b-instruct:free"]
        casc = client.cascade("general")
        assert casc[0] == "fakelab/nova:free"
        # live agent run: 429 rotation + native tool call + markdown tool call
        agent = Agent(config=cfg, client=client)
        out = agent.run("create hello.txt then verify it")
        assert "verified over the wire" in out, out
        assert agent.last_model == casc[1]  # rotated past the 429'ing model
        assert "live-wire-hi" in open(f"{cfg.workspace}/hello.txt").read()
        assert client.total_prompt > 0 and client.stats["estimated_cost_usd"] == 0.0
        # server saw OpenAI-compatible payloads with tools
        assert FakeOpenRouter.requests
        assert "tools" in FakeOpenRouter.requests[-1]
        assert FakeOpenRouter.requests[-1]["messages"][0]["role"] == "system"
    finally:
        httpd.shutdown()


class FakeWeb(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/search"):
            body = json.dumps({"results": [
                {"title": "Live Result", "url": "http://x.test/a",
                 "content": "live content here"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/page":
            html = (b"<html><head><style>.x{}</style><script>alert(1)</script></head>"
                    b"<body><h1>Live Title</h1><p>Real paragraph.</p></body></html>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif self.path == "/huge":
            self.send_response(200)
            self.send_header("Content-Length", "99999999")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.send_response(404)
        self.end_headers()


def test_wire_web_search_and_fetch():
    httpd = serve(FakeWeb)
    old = os.environ.get("AGENT1_SEARCH_URL")
    try:
        port = httpd.server_address[1]
        os.environ["AGENT1_SEARCH_URL"] = f"http://127.0.0.1:{port}/search"
        t = ToolRegistry(workspace=tempfile.mkdtemp(), approval="auto")
        out = t.execute("web_search", {"query": "wire"})
        assert "Live Result" in out and "http://x.test/a" in out
        out = t.execute("web_fetch", {"url": f"http://127.0.0.1:{port}/page"})
        assert "Live Title" in out and "Real paragraph" in out
        assert "alert(1)" not in out and ".x{}" not in out  # scripts/styles stripped
        out = t.execute("web_fetch", {"url": f"http://127.0.0.1:{port}/huge"})
        assert "too large" in out
        out = t.execute("web_fetch", {"url": f"http://127.0.0.1:{port}/nope"})
        assert "ERROR" in out
    finally:
        if old is None:
            os.environ.pop("AGENT1_SEARCH_URL", None)
        else:
            os.environ["AGENT1_SEARCH_URL"] = old
        httpd.shutdown()
