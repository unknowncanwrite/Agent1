# OMNI-AGENT 🔥 - Ultimate Agent + Manus-like Web Chat

> **The ultimate agent that overcomes all 50+ frameworks, now with Manus-like web UI that works on your PC or Render.**

[![Free Models](https://img.shields.io/badge/Free%20Models-OpenRouter-blue)](https://openrouter.ai)
[![Web UI](https://img.shields.io/badge/Web%20UI-Manus--like-green)]()
[![Deploy](https://img.shields.io/badge/Deploy-Render%20%7C%20Docker%20%7C%20PC-black)]()

## 🌟 NEW: Manus-like Web Chat Interface

Like **Manus** (the autonomous digital employee), OMNI now has a full web chat UI:

- 💬 **Chat** - Talk to OMNI like ChatGPT
- 🖥️ **Computer View** - Right sidebar shows tool calls, files created, browser preview (like Manus)
- 📁 **File Explorer** - Left sidebar with workspace files, sessions, memory
- 🔀 **Model Switcher** - Pick best free model per task
- 👥 **Crew Mode** - Single agent or 5-agent dev crew
- 💰 **$0 Cost** - Free OpenRouter models

**Works on:**
- Your PC: `python main.py serve` → http://localhost:8000
- Render: 1-click deploy with `render.yaml` → your-url.onrender.com
- Docker: `docker run -p 8000:8000 omni-agent`
- Any VPS, Railway, Fly.io

![OMNI Web UI](https://via.placeholder.com/800x400/0a0a0b/ffffff?text=OMNI-AGENT+Manus-like+Web+Chat)

## 🚀 Quick Start (Web UI)

### PC - 30 Seconds
```bash
git clone https://github.com/unknowncanwrite/Agent1.git
cd Agent1
pip install -r requirements.txt
cp .env.example .env
# Add OPENROUTER_API_KEY from https://openrouter.ai/keys (free, no card)

python main.py serve
# Open http://localhost:8000 → Manus-like chat!
```

### Render - 1 Click
1. Push to GitHub
2. Go to https://dashboard.render.com → New → Blueprint
3. Connect repo (reads `render.yaml`)
4. Add env var `OPENROUTER_API_KEY`
5. Deploy → Get URL → Chat from anywhere!

See `DEPLOY.md` for full guide (Render, Docker, Railway, Fly.io).

## 🏆 Why OMNI Beats All 50+ Frameworks?

We researched **50+ GitHub repos** (see `RESEARCH.md`):

| Framework | Stars | Strength | OMNI Advantage |
|-----------|-------|----------|----------------|
| AutoGPT | 183K | Pioneer | No loops, memory, free router |
| Langflow/Dify | 146K/136K | Visual | API + CLI + Web UI + code-first |
| OpenClaw | 250K | Channels, lane queue | Lane queue + file memory + coding + free |
| CrewAI | 48K | Crews | Crews + Graph + Sub-agents + parallel |
| LangGraph | 40K | Graphs | Graphs + Crews + skills |
| OpenHands | - | Coding | Coding + multi-agent + web + memory |
| Browser-Use | 86K | Browser | Web search/fetch + skill |
| Mem0 | 52K | Memory | Hybrid file+vector+JSONL |

**What no single framework has, OMNI does:**
1. **Free-first router** - 11 free models, auto-failover, $0
2. **Hybrid memory** - File markdown (git-backable) + vector + JSONL
3. **Lane queue** - Serial per session, no race (OpenClaw innovation)
4. **Multi-paradigm** - Crew + Graph + Single + Sub-agents
5. **Skills** - Markdown hot-reload, self-create
6. **30+ tools** - Most comprehensive
7. **Manus-like Web UI** - Chat + computer view + files
8. **Works everywhere** - PC, Render, Docker, VPS

## 🧠 Free Models (OpenRouter)

| Task | Model | Why |
|------|-------|-----|
| Coding | `qwen/qwen3-coder:free` | #1 free coding, 1M context |
| Research | `nvidia/nemotron-3-ultra-550b-a55b:free` | 550B MoE, 1M |
| General | `google/gemma-4-31b-it:free` | Multimodal |
| Router | `openrouter/free` | Auto picks best free |

Auto-failover if rate-limited. $0 cost, 50-1000 req/day free.

## 🏗️ Architecture

```
User → Web UI (Manus-like) → API → Model Router → Best Free Model
                                    ↓
                              Lane Queue (serial per session)
                                    ↓
                              OmniAgent (ReAct + Planning)
                                    ↓
                              Tools (16+: fs, shell, web, git, code)
                                    ↓
                              Hybrid Memory (file+vector+JSONL)
                                    ↓
                              Reflection → Learnings → Future tasks

Crew Mode:
  PM → Coder → Reviewer → Tester → Writer → Synthesis

Graph Mode:
  [planner] → [coder] → [tester] → [reviewer] → [end] (with checkpoints)
```

See `ARCHITECTURE.md` for deep dive.

## 💻 Usage

### Web UI (Manus-like) - Recommended
```bash
python main.py serve
# Open http://localhost:8000
# Chat: "Build todo API with FastAPI"
# Watch right sidebar: tool calls, files, browser
# Left sidebar: workspace files, sessions
```

### CLI
```bash
python main.py run "Build todo API with FastAPI and tests"
python main.py crew "Build GitHub stats CLI" --roles senior_coder,qa_tester
python main.py chat  # Interactive terminal chat
python main.py models # List free models
```

### Python API
```python
from omni_agent import OmniAgent, OmniConfig

config = OmniConfig.from_env()
agent = OmniAgent(config=config)

result = agent.run("Research AI agents and create report at ./workspace/report.md")
print(result["answer"])  # $0 cost

# Multi-agent crew
from omni_agent.multi_agent import OmniCrew, PREDEFINED_ROLES, CrewTask

roles = [PREDEFINED_ROLES["project_manager"], PREDEFINED_ROLES["senior_coder"], PREDEFINED_ROLES["qa_tester"]]
crew = OmniCrew(roles, config=config)
result = crew.kickoff([CrewTask(description="Build todo API", expected_output="Working code")])
```

### API
```bash
curl -X POST http://localhost:8000/api/run -H "Content-Type: application/json" -d '{"task": "Build todo API"}'
# Docs at /docs
```

## 🔧 Tools (16+)

- **Filesystem**: read_file, write_file, edit_file, list_files, delete_file
- **Execution**: run_shell, run_python
- **Web**: web_search, web_fetch, git_operations
- **Code**: analyze_code, run_tests
- **Memory**: memory_search, memory_write, load_skill

All OpenAI function calling + MCP + A2A compatible.

## 👥 Roles (7)

- `senior_coder` - Qwen3 Coder, production code
- `researcher` - Nemotron 1M, deep research
- `code_reviewer` - Quality, security
- `qa_tester` - Tests, edge cases
- `tech_writer` - Docs
- `project_manager` - Planning
- `analyst` - Data

## 📦 Project Structure

```
Agent1/
├── omni_agent/
│   ├── config.py (free models registry)
│   ├── llm/ (openrouter client + router)
│   ├── core/ (agent, lane queue, session, transcript)
│   ├── memory/ (file + vector hybrid)
│   ├── tools/ (16 tools)
│   ├── multi_agent/ (roles, crew, graph, subagents)
│   ├── skills/ (markdown skills)
│   ├── observability/ (logger, cost tracker)
│   └── server/
│       ├── api.py (FastAPI + serves web UI)
│       └── static/
│           ├── index.html (Manus-like UI)
│           └── app.js (chat logic)
├── workspace/ (agent workspace, git-backable)
├── examples/ (coding, research, crew, browser)
├── main.py (CLI + web entry, works on PC & Render)
├── render.yaml (1-click Render deploy)
├── Dockerfile (works anywhere)
├── DEPLOY.md (deploy guide)
├── RESEARCH.md (50+ repos analyzed)
├── ARCHITECTURE.md (deep dive)
└── requirements.txt
```

## 🔐 Security

- No hardcoded keys - env var only, `.env` gitignored
- Sandbox, blocked dangerous commands
- Tool allowlist per role
- Workspace isolated
- Transcripts for audit

## 📈 Roadmap

- [x] Free-first router (11 models)
- [x] Hybrid memory
- [x] Lane queue
- [x] Crew + Graph + Subagents
- [x] 16+ tools
- [x] Manus-like Web UI
- [x] PC + Render + Docker
- [ ] Playwright browser with semantic snapshots
- [ ] Channel adapters (Telegram, Discord, Slack)
- [ ] MCP + A2A native
- [ ] Voice + multimodal

## 🤝 Contributing

PRs welcome! Built to beat all, community makes stronger.

## 📄 License

MIT - Free for all, like models we use.

## 🙏 Acknowledgments

50+ repos: OpenClaw, CrewAI, LangGraph, AutoGen, OpenHands, Dify, Langflow, MetaGPT, AutoGPT, Browser-Use, Mem0, etc. We stand on giants, build higher.

---

**Made with 🔥 by OMNI-AGENT - The Manus-like agent that overcomes all others, for free.**

- Free key: https://openrouter.ai/keys
- Web UI: http://localhost:8000 (or your Render URL)
- API Docs: http://localhost:8000/docs
- Deploy: See `DEPLOY.md`
