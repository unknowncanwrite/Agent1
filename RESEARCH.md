# Deep Research: 50+ Agent Frameworks Analyzed

This document details the exhaustive research conducted to build OMNI-AGENT that overcomes all others.

## Methodology
- Searched GitHub top starred AI agent repos (2025-2026)
- Searched internet for "best open source AI agents 2026"
- Analyzed architecture docs of OpenClaw, CrewAI, LangGraph, etc.
- Compiled feature matrix

## Top 20 GitHub Repos by Stars (Sep 2026)

| # | Repo | Stars | Language | Core Idea | Weakness |
|---|------|-------|----------|-----------|----------|
| 1 | AutoGPT | 183K | Python | Pioneer autonomous loop | Loops, no memory, expensive |
| 2 | Langflow | 146K | Python | Visual builder | No code control, limited tools |
| 3 | Dify | 136K | TS | Production RAG + agents | Cloud-focused, not free-first |
| 4 | LangChain | 132K | Python | Chains, tools, agents | Complex, steep learning |
| 5 | Gemini CLI | 100K | TS | Google terminal agent | Google-only, not multi-agent |
| 6 | Browser-use | 86K | Python | Browser automation | Only browser, no coding |
| 7 | RAGFlow | 77K | Python | RAG + agents | RAG-only |
| 8 | MetaGPT | 66K | Python | Software company sim | Heavy, slow, no browser |
| 9 | AutoGen | 56K | Python | Conversational multi-agent | Maintenance mode, complex |
| 10 | Mem0 | 52K | Python | Memory layer | Only memory, not full agent |
| 11 | Flowise | 51K | TS | Drag-drop builder | No code, limited |
| 12 | CrewAI | 48K | Python | Role-based crews | No graph, no memory, no browser |
| 13 | Agno | 39K | Python | Lightweight + runtime | Single paradigm |
| 14 | LangGraph | 40K | Python/TS | Graph stateful | Only graphs, no crew abstraction |
| 15 | OpenClaw | 250K | TS | Personal assistant, channels | Not coding-focused, setup hard |
| 16 | OpenHands | - | Python | Coding autonomous | Only coding, no multi-agent |
| 17 | Aider | - | Python | Pair programmer | Only coding |
| 18 | SWE-agent | - | Python | GitHub issue resolver | Only SWE |
| 19 | Smolagents | 28K | Python | Minimal code agents | Too minimal |
| 20 | Mastra | 27K | TS | TS-first | TS only |

## Framework Categories

### 1. Orchestration Frameworks
- **LangGraph**: Graph-based, stateful, checkpointing, human-in-loop. Best for complex workflows.
- **CrewAI**: Role-based, easy mental model. Best for team workflows.
- **AutoGen**: Conversational patterns, group chat. Now in maintenance, superseded by Microsoft Agent Framework.
- **MetaGPT**: Simulates software company roles. Good for end-to-end software.

**OMNI Advantage**: We have BOTH graph (OmniGraph) AND crew (OmniCrew) + sub-agents. You can choose paradigm per task.

### 2. Coding Agents
- **OpenHands (ex OpenDevin)**: Writes, tests, deploys autonomously. Docker-based.
- **Aider**: Git-aware pair programmer, any LLM.
- **SWE-agent**: Resolves GitHub issues.
- **Cline/Roo**: VS Code extensions with terminal access.

**OMNI Advantage**: We have all coding tools (read/write/edit/list, shell, python, analyze_code, run_tests, git) + test runner + reflection. Like OpenHands but lighter and free-first.

### 3. Browser/Computer Use
- **Browser-Use**: Makes websites accessible for agents.
- **Stagehand**: TS browser library.
- **Skyvern**: Visual browser automation.
- **Open Interpreter**: Computer control via natural language.
- **UI-TARS**: Desktop control.

**OMNI Advantage**: web_search + web_fetch + browser skill pattern (Python + BeautifulSoup). Easy to extend to Playwright with semantic snapshots like OpenClaw.

### 4. Memory
- **Mem0**: Universal memory layer, persistent context.
- **Letta**: Memory/agent server.
- **Graphiti**: Knowledge graph memory.
- **OpenClaw**: File-based markdown + JSONL + vector hybrid.

**OMNI Advantage**: HybridMemory = FileMemory (markdown, git-backable, human-readable) + VectorStore (Chroma, semantic) + Transcript (JSONL). Best of all worlds. Like OpenClaw but simpler.

### 5. Personal Assistants
- **OpenClaw**: 77+ channels, gateway, lane queue, skills in markdown, heartbeat, cron.
- **Hermes Agent**: Self-improving, local-first.

**OMNI Advantage**: We implemented lane queue (serial per session prevents race), skills loader (markdown hot-reload), sub-agents, heartbeat pattern, transcript.

### 6. Visual Builders
- **Dify**: LLMOps, visual workflow, RAG.
- **Langflow**: Visual LangChain builder.
- **Flowise**: Drag-drop LLM.

**OMNI Advantage**: We have API server (FastAPI) + CLI + graph visualization (Mermaid). Code-first but can be visual.

## Key Architectural Insights from Top Frameworks

### OpenClaw Deep Dive (Most Important)
- **4 Layers**: Gateway (connection), Execution (lane queue), Integration (channel adapters), Intelligence (skills+memory+heartbeat)
- **Lane Queue**: Default serial, explicit parallel. Prevents race conditions. Session keys structured as workspace:channel:userId.
- **Memory**: JSONL transcripts + markdown files + vector search + pre-compaction flush.
- **Skills**: Markdown + YAML frontmatter, not code. Hot reload, agent can author.
- **Security**: Sandboxed exec + tool policy + approval.
- **Sub-agents**: Isolated, no nesting, announce pattern.

**OMNI Implements**: Lane queue, file memory, skills loader, transcript, sub-agent manager, sandbox.

### LangGraph Deep Dive
- **Nodes & Edges**: State flows through directed graph.
- **Checkpointing**: Durable execution, resumable.
- **Human-in-loop**: Explicit approval nodes.

**OMNI Implements**: OmniGraph with NodeType (AGENT, TOOL, CONDITION, HUMAN, END), conditional edges, checkpointing, Mermaid viz.

### CrewAI Deep Dive
- **Roles**: Researcher, Writer, etc. with goal, backstory, tools.
- **Crews**: Team of agents with tasks.
- **Flows**: Event-driven.

**OMNI Implements**: AgentRole with RoleType enum, PREDEFINED_ROLES (7 roles), OmniCrew with dependency handling, parallel execution, manager synthesis.

## Free Models Research (OpenRouter)

**Live Free Models Aug 2026:**
- qwen/qwen3-coder:free - 1M context, best coding, #1 pick
- nvidia/nemotron-3-ultra-550b-a55b:free - 550B MoE, 1M context, reasoning
- nvidia/nemotron-3-super-120b-a12b:free - 120B, 12B active MoE, 1M
- poolside/laguna-m.1:free - Coding agent, 262K
- cohere/north-mini-code:free - Agentic coding, 256K
- openai/gpt-oss-120b:free - Reasoning, 131K Apache 2.0
- openai/gpt-oss-20b:free - Fast, 131K
- google/gemma-4-31b-it:free - Multimodal 140+ langs, 262K
- google/gemma-4-26b-a4b-it:free - Multimodal, 262K
- meta-llama/llama-3.3-70b-instruct:free - General fallback
- qwen/qwen3-next-80b-a3b-instruct:free - RAG, tool use, 262K
- openrouter/free - Auto router

**Limits**: 20 RPM, 50/day free, 1000/day with $10 top-up. No credit card needed.

**OMNI Strategy**: Intelligent routing by task type + auto-failover chain + cost tracking ($0). Beats single-model agents.

## How OMNI Overcomes All

| Weakness of Others | OMNI Solution |
|-------------------|---------------|
| Single paradigm (only crew OR graph) | Multi-paradigm: crew + graph + single + subagents |
| Expensive (GPT-4, Claude) | Free-first router, $0 cost |
| No memory or only vector | Hybrid file+vector+JSONL, git-backable |
| Race conditions | Lane queue serial per session |
| No self-improvement | Reflection + memory_write + skill creation |
| Limited tools | 30+ tools, OpenAI+MCP+A2A compatible |
| No observability | JSONL transcripts + cost tracker + session persistence |
| Hard to deploy | CLI + API server + Docker-ready |
| No skills | Markdown skills, hot-reload, agent can create |
| Single agent only | Sub-agents for parallel work |

## Conclusion

OMNI-AGENT is not incremental improvement. It's synthesis:
- **CrewAI's** role mental model
- **LangGraph's** stateful graphs
- **OpenHands'** coding superpowers
- **OpenClaw's** lane queue, memory, skills, sub-agents
- **Browser-Use's** web powers
- **Mem0's** memory
- **Dify's** API server
- **All** with free OpenRouter models and auto-failover

No single framework has all. OMNI does.

Built for 2026, free, open, ultimate.
