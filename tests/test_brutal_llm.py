"""Adversarial LLM-client tests: parsing chaos, cascade, rotation."""
import json
import time
import urllib.request

from agent1.config import AgentConfig, model_cascade_for
from agent1.llm import OpenRouterClient, MockClient, extract_tool_calls, strip_tool_blocks, ChatResult


def cfg(**kw):
    kw.setdefault("api_key", "test-key")
    return AgentConfig(**kw)


def test_extract_shapes():
    assert extract_tool_calls("no json here") == []
    assert extract_tool_calls("```json\n{not json}\n```") == []
    assert extract_tool_calls("```json\n[1,2]\n```") == []  # array ignored
    c = extract_tool_calls('```json\n{"tool": "bash", "arguments": {"command": "ls"}}\n```')
    assert c == [{"tool": "bash", "arguments": {"command": "ls"}}]
    c = extract_tool_calls('```tool\n{"name": "x", "args": {"a": 1}}\n```')
    assert c == [{"tool": "x", "arguments": {"a": 1}}]
    c = extract_tool_calls('```json\n{"function": {"name": "f", "arguments": "{\\"k\\": 2}"}}\n```')
    assert c == [{"tool": "f", "arguments": {"k": 2}}]
    c = extract_tool_calls('```JSON\n{"tool":"a","arguments":{"x":1}}\n```\ntext\n'
                           '```json\n{"tool":"b","arguments":{}}\n```')
    assert [x["tool"] for x in c] == ["a", "b"]
    # args as raw string stays usable
    c = extract_tool_calls('```json\n{"tool": "t", "arguments": "oops"}\n```')
    assert c[0]["arguments"] == {"_raw": "oops"}
    # missing tool name ignored
    assert extract_tool_calls('```json\n{"arguments": {}}\n```') == []
    assert "{" not in strip_tool_blocks('hi ```json\n{"tool":"a","arguments":{}}\n``` bye')


def test_cascade_routing():
    for task, expect in [("code", ("coder", "laguna")), ("research", ("nemotron",)),
                         ("reason", ("oss-120b", "deepseek")), ("fast", ("glm", "oss-20b")),
                         ("general", ("nex", "llama", "qwen3-next")),
                         ("nonsense-task", ("free",))]:
        c = model_cascade_for(task)
        assert len(c) >= 10 and all(m.endswith(":free") for m in c)
        assert any(e in c[0] for e in expect), f"{task} -> {c[0]}"
    # override pinning
    cc = cfg(model_override="x/y:free").cascade("code")
    assert cc[0] == "x/y:free" and len(cc) == len(set(cc))


def test_cooldown_skip_and_usage():
    c = OpenRouterClient(cfg())
    c._cooldown[c.cascade("general")[0]] = time.time() + 999
    calls = []
    def fake_post(payload):
        calls.append(payload["model"])
        return {"choices": [{"message": {"content": "FINAL: ok", "tool_calls": None}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    c._post = fake_post
    r = c.chat([{"role": "user", "content": "hi"}])
    assert r.model == calls[0] and r.text == "FINAL: ok"
    assert c.total_prompt == 10 and c.total_completion == 5
    assert c.stats["estimated_cost_usd"] == 0.0
    assert c.last_model == r.model and c.last_errors == []


def test_openai_tool_calls_parsed():
    c = OpenRouterClient(cfg())
    c.discover_free_models = lambda: []  # offline
    c._post = lambda p: {"choices": [{"message": {
        "content": "", "tool_calls": [
            {"function": {"name": "bash", "arguments": '{"command": "ls"}'}},
            {"function": {"name": "bad", "arguments": "{oops}"}}]}}], "usage": {}}
    r = c.chat([{"role": "user", "content": "go"}])
    assert r.tool_calls[0] == {"tool": "bash", "arguments": {"command": "ls"}}
    assert r.tool_calls[1]["arguments"] == {"_raw": "{oops}"}


def test_discovery_cache_and_failure():
    c = OpenRouterClient(cfg())
    n = {"i": 0}
    class Fake:
        headers = {}
        def read(self): return json.dumps({"data": [
            {"id": "a/b:free"}, {"id": "paid/model"}, {"id": "c/d:free"}]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    orig = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda *a, **k: (n.__setitem__("i", n["i"] + 1), Fake())[1]
        assert c.discover_free_models() == ["a/b:free", "c/d:free"]
        assert c.discover_free_models() == ["a/b:free", "c/d:free"]
        assert n["i"] == 1  # cached
        casc = c.cascade("general")
        assert casc[0] == "a/b:free"  # fresh models prepended
    finally:
        urllib.request.urlopen = orig
    c2 = OpenRouterClient(cfg())
    urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(Exception("down"))
    try:
        assert c2.discover_free_models() == []
    finally:
        urllib.request.urlopen = orig


def test_all_fail_and_fastfail():
    c = OpenRouterClient(cfg())
    c._post = lambda p: (_ for _ in ()).throw(Exception("<urlopen error down>"))
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should raise")
    except RuntimeError as e:
        assert "network unreachable" in str(e)  # fast-fail, not 12 slow tries
    assert len(c.last_errors) >= 2
    # HTTP 429s rotate through everything instead
    seen = []
    def r429(p):
        seen.append(p["model"])
        raise Exception("HTTP 429: rate limited")
    c2 = OpenRouterClient(cfg())
    c2._post = r429
    try:
        c2.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should raise")
    except RuntimeError as e:
        assert "429" in str(e)
    assert len(seen) == len(c2.cascade())  # rotated through all
    assert all(v > time.time() for v in c2._cooldown.values())


def test_no_key():
    c = OpenRouterClient(AgentConfig(api_key=""))
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should raise")
    except RuntimeError as e:
        assert "OPENROUTER_API_KEY" in str(e)


def test_mock_client():
    m = MockClient([ChatResult(text="a", model="mock")])
    assert m.chat([]).text == "a"
    assert "Mock final" in m.chat([]).text  # exhausted -> default
    assert len(m.calls) == 2
