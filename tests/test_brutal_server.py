"""Live HTTP tests against the real server (MockClient, random port)."""
import json
import tempfile
import threading
import urllib.request

from agent1.config import AgentConfig
from agent1.llm import MockClient
from agent1.server import build_server


def _serve():
    tmp = tempfile.mkdtemp()
    import os
    os.environ["AGENT1_WORKSPACE"] = tmp  # build_server loads env config
    httpd, agent, crew = build_server("127.0.0.1", 0, client=MockClient())
    port = httpd.server_address[1]
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    return httpd, port


def _get(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _post(port, path, obj=None, raw=None):
    data = raw if raw is not None else json.dumps(obj or {}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


import urllib.error  # noqa: E402


def test_pages_and_models():
    httpd, port = _serve()
    try:
        s, body = _get(port, "/")
        assert s == 200 and b"Agent1 Omni" in body
        s, body = _get(port, "/api/models")
        assert s == 200 and "cascade" in json.loads(body)
        s, body = _get(port, "/api/stats")
        j = json.loads(body)
        assert "grep" in j["tools"] and "apply_patch" in j["tools"]
        s, _ = _get(port, "/nope")
        assert s == 404
    finally:
        httpd.shutdown()


def test_trace_and_todos():
    httpd, port = _serve()
    try:
        s, body = _get(port, "/api/trace?limit=5")
        assert s == 200 and "events" in json.loads(body)
        s, body = _get(port, "/api/trace?limit=bogus")
        assert s == 200
        s, body = _get(port, "/api/todos")
        assert s == 200 and json.loads(body)["todos"] == []
    finally:
        httpd.shutdown()


def test_chat_api():
    httpd, port = _serve()
    try:
        s, j = _post(port, "/api/chat", {"message": ""})
        assert s == 400
        s, j = _post(port, "/api/chat", {"message": "hello", "mode": "general"})
        assert s == 200 and "reply" in j and "model" in j
        s, j = _post(port, "/api/chat", raw=b"not json{{{")
        assert s == 400  # bad body -> empty -> 400, no crash
        s, j = _post(port, "/api/chat", raw=b"[1,2]")
        assert s == 400
    finally:
        httpd.shutdown()


def test_task_api():
    httpd, port = _serve()
    try:
        s, j = _post(port, "/api/task", {"task": ""})
        assert s == 400
        s, j = _post(port, "/api/task", {"task": "do T", "mode": "general"})
        assert s == 200 and "steps" in j
        s, j = _post(port, "/api/task", {"task": "do T", "crew": "sequential"})
        assert s == 200 and "researcher" in j["reply"]
    finally:
        httpd.shutdown()
