# Deep research: every major agent (GitHub + web) — and how Agent1 beats them

Researched 2026-09-15 from GitHub repos, docs, and benchmark roundups.

## 1. GitHub agent repos surveyed

| Project | Repo | Stars (2026) | License | What it is |
|---|---|---|---|---|
| AutoGPT | Significant-Gravitas/AutoGPT | ~186K | Polyform+MIT | Viral autonomous task-runner, now a platform w/ AutoPilot builder |
| OpenClaw | openclaw/openclaw | ~247K | MIT | Self-hosted personal assistant (messaging + tools) |
| LangChain | langchain-ai/langchain | ~95K+ | MIT | Composable LLM-app toolkit, broadest integrations, v1.0 |
| LangGraph | langchain-ai/langgraph | ~37K | MIT | Stateful graph orchestration, retries, checkpoints, HITL |
| OpenHands (OpenDevin) | All-Hands-AI/OpenHands | ~70K | MIT | Autonomous coding agent, Docker sandbox, PR creation, v1.6 |
| SWE-agent | SWE-bench/SWE-agent | large | MIT | Research coding agent, EnIGMA security mode, mini 100-line variant |
| Aider | Aider-AI/aider | ~39K | Apache-2.0 | Terminal pair-programmer, diff/patch editing |
| Cline | cline/cline | ~61K | Apache-2.0 | IDE coding agent (VSCode/JetBrains) |
| CrewAI | crewAIInc/crewAI | ~55K | MIT | Role-based Crews + event Flows, 60% of Fortune 500 experimenting |
| MetaGPT | FoundationAgents/MetaGPT | ~45K | MIT | Simulated software company (PM/architect/engineer roles) |
| AutoGen (+AG2) | microsoft/autogen | ~35K | MIT | Conversational multi-agent; MS in maintenance, Agent Framework is successor |
| Dify | langgenius/dify | ~55K | source-available | Visual no-code agent/RAG app builder + cloud |
| SuperAGI | TransformerOptimus/SuperAGI | — | MIT | Early AutoGPT-successor w/ GUI (stale since ~2024) |
| AgentGPT | reworkd/AgentGPT | — | GPL-3.0 | Browser autonomous agent (cloud) |
| BabyAGI | yoheinakajima/babyagi | ~20K | MIT | Minimal task-loop pioneer (vector memory) |
| ChatDev | OpenBMB/ChatDev | ~25K | Apache-2.0 | Chat-simulated dev company |
| CAMEL | camel-ai/camel | ~5K | Apache-2.0 | Role-play multi-agent research |
| Mastra | mastra-ai/mastra | ~8K | Apache-2.0 | TypeScript-native agents + long-running systems |
| Agno (ex-Phidata) | agno-agi/agno | — | Apache-2.0 | Agent platform builder/runner |
| Haystack | deepset-ai/haystack | — | Apache-2.0 | Retrieval-heavy pipelines + agents |
| Browser Use | browser-use/browser-use | — | MIT | Browser automation for agents |
| Open Interpreter | KillianLucas/open-interpreter | ~57K | AGPL-3.0 | Direct code-execution conversational agent |
| n8n / Flowise / Rasa | various | — | fair-code/Apache | Visual automation / low-code / enterprise conversational |

## 2. Framework comparison (synthesis of 6 roundups)

| Framework | Best for | Control | Learning curve | Production-ready | Key limitation |
|---|---|---|---|---|---|
| LangGraph | Stateful prod workflows | Highest | Steepest | ✅ | Design overhead, DIY everything |
| CrewAI | Fast role-based prototypes | Medium | Easiest | ✅ w/ observability | Hierarchy ceiling, multi-agent cost |
| AutoGen | Multi-agent conversation research | Medium | Medium | maintenance mode | Loops, weak termination |
| LangChain | Integrations scaffolding | Medium | Moderate | ✅ v1.0 | Abstraction sprawl |
| MetaGPT | Software-role simulation | Medium | Med-High | experimental | Dev-workflows only |
| OpenHands | Autonomous coding | N/A (agent) | Low* | ✅ w/ Docker | Docker+cost ($1–10/session) |
| SWE-agent | Issue→fix research | N/A | Low | ✅ CLI | CLI-only, no browser/MCP/multi-agent |
| Aider/Cline | Human-in-loop coding | N/A | Low | ✅ | Not autonomous |

SWE-bench Verified (June 2026): mini-SWE-agent >74% · OpenHands 72% · Cline ~60% · Aider 31%.

## 3. OpenRouter FREE models (the $0 arsenal Agent1 uses)

Free = `$0/in+out`, gated by requests/day (not tokens), **rotates often** —
hence Agent1's live auto-discovery + cascade fallback. Verified Sept 2026:

| Model id | Context | Best for |
|---|---|---|
| nvidia/nemotron-3-ultra-550b-a55b:free | 1M | Long-horizon agents, orchestration |
| qwen/qwen3-coder:free | 1M | Agentic coding, tool calling |
| poolside/laguna-m.1:free | 262K | Complex software engineering |
| poolside/laguna-xs-2.1:free | 262K | Fast compact coding |
| openai/gpt-oss-120b:free | 131K | Reasoning + tool use (Apache-2.0) |
| openai/gpt-oss-20b:free | 131K | Lightweight, fast |
| nex-agi/nex-n2.5-pro:free / mini | 262K | Agentic coding w/ visual feedback loop |
| google/gemma-4-31b-it:free | 262K | Multimodal, 140+ languages |
| meta-llama/llama-3.3-70b-instruct:free | 131K | Stable generalist (since Dec 2024) |
| deepseek/deepseek-r1:free | 128K | Deep reasoning |
| z-ai/glm-4.5-air:free | 131K | Light generalist |
| qwen/qwen3-next-80b-a3b-instruct:free | 262K | RAG, long multi-turn |
| inclusionai/ling-3.0-flash-vl/fin/sante:free | 262K | Vision / finance / medical MoE |
| cohere/north-mini-code:free | 256K | Terminal + agentic coding |

Strategy (matches 2026 best practice): **draft/agents on free, finals on paid only if needed** —
Agent1 pins `AGENT1_MODEL` to override the cascade for that.

## 4. Gap analysis → Agent1's winning moves

1. **Every framework assumes paid models.** None ships free-model fallback/rotation.
   → Agent1: task-routed cascade + 429 cooldown + live discovery. Cost $0.00.
2. **Coding agents need Docker/heavy setup** (OpenHands) or aren't autonomous (Aider/Cline).
   → Agent1: sandboxed shell+python+file tools, zero deps, verify-after-edit loop.
3. **Multi-agent costs explode** (CrewAI) or need graph-assembly expertise (LangGraph).
   → Agent1: 3 one-line crew modes (sequential/hierarchical/debate) on free models.
4. **Memory is DIY everywhere** (vector DBs, LangSmith, configs).
   → Agent1: stdlib SQLite facts + episodic log, zero-config.
5. **Observability costs extra** (LangSmith, AgentOps).
   → Agent1: JSONL traces + audit log + token stats built in.
6. **Setup ranges from moderate→steep.** → Agent1: clone, key, one command.

## 5. Sources

- arsum.com agentic-framework comparisons (May–Jul 2026)
- scrimba.com best-agent-frameworks 2026 · gist manduks comparison 2026
- taskade.com 20 open-source agents · flowith.io 10 OSS agent projects (Mar 2026)
- eesel.ai 9 best OSS agents · buildbetter.ai AutoGPT alternatives · 10xclaw top GitHub 2026
- vibecoding OpenHands review · localaimaster OpenHands-vs-SWE-agent · aifoss coding agents 2026
- OpenRouter model catalog + aitoolsradar / pinggy.io / buldrr.com free-model guides (Jun–Jul 2026)
