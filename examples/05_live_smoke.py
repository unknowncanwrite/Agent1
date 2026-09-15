"""TRUE-LIVE smoke test — run on a normal network (not a firewalled sandbox):

    python examples/05_live_smoke.py

Uses your OPENROUTER_API_KEY (.env) and FREE models only ($0).
Checks: key -> live :free catalog -> chat -> autonomous tool task ->
research task -> crew. Prints a PASS/FAIL report.
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent1 import Agent, Crew  # noqa: E402
from agent1.config import AgentConfig  # noqa: E402
from agent1.llm import OpenRouterClient  # noqa: E402

RESULTS = []


def check(name, fn):
    t0 = time.time()
    try:
        detail = fn()
        RESULTS.append((name, "PASS", f"{time.time()-t0:.1f}s", str(detail)[:160]))
        print(f"  PASS {name} ({time.time()-t0:.1f}s) {str(detail)[:120]}")
        return True
    except Exception as e:
        RESULTS.append((name, "FAIL", f"{time.time()-t0:.1f}s", str(e)[:200]))
        print(f"  FAIL {name}: {str(e)[:200]}")
        traceback.print_exc(limit=2)
        return False


def main():
    cfg = AgentConfig.load()
    print("Agent1 Omni LIVE smoke (free models, $0)\n")

    def has_key():
        assert cfg.api_key, "OPENROUTER_API_KEY missing — copy .env.example to .env"
        return f"key …{cfg.api_key[-4:]}"
    check("1. API key present", has_key)

    client = OpenRouterClient(cfg)

    def catalog():
        live = client.discover_free_models()
        assert live, "no :free models in live catalog"
        print("     live free:", ", ".join(live[:8]))
        return f"{len(live)} free models"
    if not check("2. Live :free catalog", catalog):
        print("\nSTOP: network/OpenRouter unreachable from here.")
        return 1

    def chat():
        r = client.chat([{"role": "user", "content": "Reply with exactly: LIVE-OK"}],
                        task="fast", max_tokens=50)
        assert "LIVE-OK" in r.text, f"unexpected: {r.text[:100]}"
        return f"model={r.model}"
    check("3. Chat completion", chat)

    def tool_task():
        cfg.workspace = "./workspace-live-smoke"
        cfg.approval = "safe"
        a = Agent(config=cfg, role="coder", task_kind="code")
        out = a.run("Create live_proof.txt containing the line 'smoke-42', "
                    "then read it back to verify. Reply FINAL with the content.", max_steps=10)
        assert "smoke-42" in out, f"not verified: {out[:200]}"
        assert "smoke-42" in Path("./workspace-live-smoke/live_proof.txt").read_text()
        return f"model={a.last_model} steps={a.steps}"
    check("4. Autonomous tool task (write+verify)", tool_task)

    def research():
        a = Agent(config=cfg, role="researcher", task_kind="research")
        out = a.run("Use web_search (1 query) for 'OpenRouter free models'. "
                    "Reply FINAL with the 2 top result titles. No files.", max_steps=8)
        assert len(out) > 30, "empty research answer"
        return f"model={a.last_model} steps={a.steps}"
    check("5. Live web research", research)

    def crew():
        c = Crew(config=cfg)
        out = c.run("One sentence: what is 7*8? Then FINAL with just the number.",
                    mode="sequential")
        assert "56" in out, f"crew missed it: {out[:200]}"
        return "researcher->coder->critic"
    check("6. Crew (sequential)", crew)

    print("\n==== LIVE REPORT ====")
    for n, s, d, det in RESULTS:
        print(f"{s:4s} {n:38s} {d:>7s}  {det}")
    fails = [r for r in RESULTS if r[1] == "FAIL"]
    print(f"\n{len(RESULTS)-len(fails)}/{len(RESULTS)} live checks passed, "
          f"cost=$0.00 tokens={client.stats}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
