# 🏆 Live model rankings: which FREE model for what work

Ranked **2026-09-15** from same-day live data (not vibes). Wired into
`agent1/config.py` — the cascade order IS this table.

## Sources (all live, Sep 14–15 2026)
- **OpenRouter τ²-Bench Airline** — agentic multi-step tool-use, 123 models, run Sep 15 2026
- **OpenRouter usage rankings** — real traffic through Sep 14 2026 (Nemotron 3 Ultra free = #9 overall, 3.45T tokens)
- **OpenRouter benchmarks page** — Gemma 4 31B = value Pareto winner
- Community coding reports (Qwen3-Coder #1 free code pick, Poolside Laguna flagship)

## The verdict: best free model per job

| Your work | 🥇 Use first | 🥈 Then | 🥉 Then | Why |
|---|---|---|---|---|
| General agent | Nemotron 3 Ultra | Gemma 4 31B | GLM-4.5-Air | τ² tools: 76.9 / 76.1 / 70.9 |
| Coding agent | Qwen3-Coder | Laguna M.1 | Nemotron 3 Ultra | specialists + best-tools backup |
| Deep research (1M ctx) | Nemotron 3 Ultra | Gemma 4 31B | Qwen3-Next 80B | 1M ctx + tools; RAG-stable 4th |
| Hard reasoning | DeepSeek R1 | gpt-oss-120B | Nemotron 3 Ultra | thinker → o3-class → tools |
| Fast/cheap | GLM-4.5-Air | Llama 3.3 70B | Qwen3-Next 80B | 2.4m+70.9% → 43s chat → 62s |
| Vision | Gemma 4 31B | Ling Flash VL | Nemotron 3 Ultra | multimodal + tools first |

## Full tool-use scores (τ² Airline, higher = better agent)

| # | Free family | Score | Speed | Verdict |
|---|---|---|---|---|
| 13 | Nemotron 3 Ultra | 76.9% (±0.8!) | 2.6m | 👑 best free agent brain |
| 22 | Gemma 4 31B | 76.1% | 5.5m | 💎 best value on Earth ($0.016, Pareto) |
| 59 | GLM-4.5-Air | 70.9% | 2.4m | ⚡ fast + strong |
| 78 | gpt-oss-120B | 64.1% | 3.5m | solid reasoning backup |
| 89 | Ling 3.0 Flash (VL kin) | 57.3% | 2.0m | vision-capable |
| 91 | DeepSeek R1 | 54.5% | 13.4m | 🧠 reason, don't agent |
| 93 | gpt-oss-20B | 51.4% | 18.7m | ⚠️ loops — last resort |
| 97 | Qwen3-Next 80B | 47.0% | 62s | RAG/chat, not tools |
| 98 | Qwen3-Coder 480B | 46.7% | 65s | ✈️ airline≠code — still #1 for code |
| 103 | Llama 4 Maverick | 44.6% | 1.8m | mid |
| 113 | Llama 3.3 70B | 38.7% | 43s | 💬 chat yes, agent no |

Unranked (too new, in cascade on provider claims): Nex N2.5 Pro (agentic),
Poolside Laguna M.1 (coding flagship).

## What this changed in Agent1
- `general`/`research` now lead Nemotron → Gemma → GLM (was: newest-first guess)
- `gpt-oss-20b` demoted to last (18.7m runaway loops on τ²)
- `llama-3.3-70b` kept only for `fast` chat (43s, but 38.7% tools)
- `reason` leads DeepSeek R1 (thinking) with tool-strong backups
- Every model carries its τ² score + note: `python -m agent1.cli models --explain`
