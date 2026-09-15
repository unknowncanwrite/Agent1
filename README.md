# 🤖 Agent1 Omni — the agent that beats every other agent

One codebase that does what **AutoGPT + CrewAI + LangGraph + OpenHands + SWE-agent + Dify** do —
on **OpenRouter FREE models ($0 forever)**, with **zero required dependencies** and **no Docker**.

| Capability | AutoGPT | CrewAI | LangGraph | OpenHands | SWE-agent | **Agent1 Omni** |
|---|---|---|---|---|---|---|
| Autonomous tool loop | ✅ | ✅ | build-it-yourself | ✅ | ✅ | ✅ |
| Multi-agent crews | ❌ | ✅ | build-it-yourself | partial | ❌ | ✅ (3 modes) |
| Coding (edit/run/verify) | partial | partial | build-it-yourself | ✅ Docker | ✅ | ✅ no-Docker |
| Web research (no API key) | ✅ | via tools | via tools | ✅ | ❌ | ✅ built-in |
| Persistent memory | vector DIY | configurable | DIY | basic | ❌ | ✅ 3-layer |
| Free-model cascade + 429 rotation | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Live free-model auto-discovery | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Task-routed models (code/research/…) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Cost | $$$ | $$$ | $$$ | $1–10/session | $1–8/session | **$0.00** |
| Setup | moderate | pip+keys | steep | Docker+4GB | pip+key | **1 command, stdlib-only** |
| Interfaces | GUI/cloud | Python | Python | Web+CLI | CLI | **CLI+Web+API+SDK** |
| Safety modes + audit log | basic | basic | DIY | ✅ | ❌ | ✅ |

Full deep-research behind this table: [`RESEARCH.md`](RESEARCH.md).

## ⚡ 60-second start

```bash
git clone https://github.com/unknowncanwrite/Agent1 && cd Agent1
cp .env.example .env   # paste your OPENROUTER_API_KEY (free models = $0)
python -m agent1.cli run "Research the best free LLM APIs and save a report to report.md" --mode research
```

No key yet? Run the offline demo: `python -m agent1.cli run "demo" --demo`

## 🖥️ Web UI + API (no Docker, no Node)

```bash
python -m agent1.cli serve --port 8080
# open http://localhost:8080
```

## 💬 CLI

```bash
python -m agent1.cli chat                                   # interactive chat + tools + memory
python -m agent1.cli run "Fix the bug in app.py" --mode code --role coder
python -m agent1.cli crew "Build a habit-tracker prototype" --mode sequential     # | hierarchical | debate
python -m agent1.cli models                                  # show free-model cascade + live discovery
python -m agent1.cli doctor                                  # diagnose setup (key, network, workspace)
python -m tests                                              # 55 brutal offline tests, ~25s
```

## 🧰 15 tools + plugins

`read/write/edit/list_files`, `grep` (code search), `apply_patch` (unified diffs),
sandboxed `bash` + `python_run`, keyless `web_search` (with fallback) + `web_fetch`,
`remember`/`recall` (long-term memory), `todo_add/done/list` — all with required-arg
validation, sandboxing, destructive-command blocking in every approval mode, and audit logging.
Drop extra tools in a dir and set `AGENT1_PLUGINS` — each `.py` with `register(registry)` loads automatically.

## 🧪 Hardened by brutal testing

- **55 adversarial tests** (`python -m tests`, zero deps): garbage args, path escapes,
  fork-bombs, timeouts, bad regex, malformed diffs/JSON, server fuzz, full CLI e2e.
- **Context compaction** — long runs summarize history instead of overflowing context.
- **Transcripts + JSONL traces** for every run (`workspace/.trace/`), `/api/trace` live feed in the Web UI.
- **Offline demo** — `AGENT1_DEMO=1` (or `--demo`) runs everything without key/network.

## 🐍 Python SDK

```python
from agent1 import Agent, Crew
print(Agent(role="researcher", task_kind="research").run("Compare Qwen3 vs Llama 4 for coding"))
print(Crew().run("Write and test a markdown todo CLI", mode="hierarchical"))
```

## 🧠 How it beats paid agents for $0

1. **Free-model cascade** — 12 curated `:free` models (Nemotron 3 Ultra 1M, Qwen3-Coder,
   gpt-oss-120B, Gemma 4, Llama 3.3 70B, DeepSeek R1, Nex N2.5, Ling Flash…) ordered
   per task kind. Any failure/429 → instant rotation to the next.
2. **Auto-discovery** — polls OpenRouter's live catalog and prepends brand-new free models,
   so the roster never goes stale (free models rotate!).
3. **Tool-call robustness** — tries native function-calling AND ` ```json ` parsing,
   because free models are inconsistent. Others assume GPT-4-level tool use.
4. **Verify-everything loop** — plan → act → observe → reflect, with re-read/re-test
   after every edit (the OpenHands/SWE-agent trick, minus Docker).
5. **3-layer memory** — rolling context + SQLite long-term facts + episodic markdown log.
6. **Safety** — `safe` mode blocks destructive commands, `manual` approves each risky
   tool, everything audit-logged to `workspace/.trace/`.

## 🗂️ Layout

```
agent1/  config.py  llm.py  tools.py  memory.py  agent.py  crew.py  server.py  cli.py
web/     index.html (chat UI)      examples/  tests/  workspace/  RESEARCH.md
```

## ⚠️ Keys & safety

- Never commit `.env`. If a key ever leaks into chat/logs, rotate it at
  https://openrouter.ai/keys.
- `AGENT1_APPROVAL=safe` (default) blocks destructive shell; use `manual` for max caution.
