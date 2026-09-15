"""CLI: `python -m agent1.cli run "task"` — simpler than Aider, OpenHands, AutoGPT."""
from __future__ import annotations

import argparse
import sys

from .agent import Agent
from .config import AgentConfig
from .crew import Crew
from .llm import MockClient


def _print_events(verbose: bool):
    def on_event(e: dict):
        t = e.get("type")
        if t == "llm" and verbose:
            print(f"\n🧠 [{e.get('model','?')}] {str(e.get('text',''))[:400]}")
            for c in e.get("tool_calls", []) or []:
                print(f"   🔧 {c['tool']} {str(c.get('arguments'))[:200]}")
        elif t == "tool":
            print(f"   ✅ {e.get('tool')}: {str(e.get('output',''))[:300]}")
        elif t == "crew_step":
            print(f"\n👥 crew → {e.get('role')}")
        elif t == "llm_error":
            print(f"   ⚠️ {e.get('error')}")
    return on_event


def main(argv=None):
    p = argparse.ArgumentParser(prog="agent1",
        description="Agent1 Omni — the $0 agent that beats paid agents.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--approval", choices=["auto", "safe", "manual"])
        sp.add_argument("--model", help="Pin one OpenRouter model id")
        sp.add_argument("--workspace", default="./workspace")
        sp.add_argument("--max-steps", type=int, default=25)
        sp.add_argument("--demo", action="store_true",
                        help="Offline demo (no key/network)")
        sp.add_argument("-v", "--verbose", action="store_true")

    r = sub.add_parser("run", help="Autonomous task run")
    r.add_argument("task")
    r.add_argument("--mode", default="general",
                   choices=["general", "code", "research", "reason", "fast"])
    r.add_argument("--role", default="assistant",
                   choices=["assistant", "researcher", "coder", "critic", "planner"])
    add_common(r)

    c = sub.add_parser("crew", help="Multi-agent run")
    c.add_argument("task")
    c.add_argument("--mode", default="sequential",
                   choices=["sequential", "hierarchical", "debate"])
    add_common(c)

    ch = sub.add_parser("chat", help="Interactive chat")
    add_common(ch)

    s = sub.add_parser("serve", help="Start web UI + API")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8080)
    add_common(s)

    m = sub.add_parser("models", help="Show free-model cascade")
    add_common(m)

    d = sub.add_parser("doctor", help="Diagnose setup (key, network, models, workspace)")
    add_common(d)

    args = p.parse_args(argv)
    config = AgentConfig.load()
    if args.approval: config.approval = args.approval
    if getattr(args, "model", None): config.model_override = args.model
    if args.workspace: config.workspace = args.workspace
    if getattr(args, "max_steps", None): config.max_steps = args.max_steps

    if getattr(args, "demo", False):
        config.demo = True
    client = MockClient() if config.demo else None

    if args.cmd == "models":
        from .llm import OpenRouterClient
        print("Free-model cascade (task-routed, auto-fallback):")
        for i, mid in enumerate(config.cascade(), 1):
            print(f"  {i:2d}. {mid}")
        if not args.demo and config.api_key:
            live = OpenRouterClient(config).discover_free_models()
            print(f"\nLive :free on OpenRouter right now: {len(live)}")
            for mid in live[:15]:
                print(f"  • {mid}")
        return

    if args.cmd == "doctor":
        run_doctor(config)
        return

    if args.cmd == "serve":
        from .server import serve
        serve(args.host, args.port)
        return

    on_event = _print_events(verbose=True)
    if args.cmd == "chat":
        agent = Agent(config=config, client=client, on_event=on_event)
        print("Agent1 Omni chat (free models). Empty line quits.\n")
        try:
            while True:
                try:
                    msg = input("you> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not msg:
                    break
                print(agent.ask(msg) + "\n")
        finally:
            if agent.history:
                agent._save_transcript("chat session", f"{len(agent.history)} messages")
                print(f"(transcript: {agent.transcript_path})")
        return

    if args.cmd == "crew":
        print(f"👥 Crew ({args.mode}) working on: {args.task}\n")
        print(Crew(config=config, client=client, on_event=on_event).run(args.task, args.mode))
        return

    print(f"🤖 Agent ({args.role}/{args.mode}) working on: {args.task}\n")
    agent = Agent(config=config, client=client, role=args.role,
                  task_kind=args.mode, on_event=on_event)
    print("\n" + "=" * 60 + "\n" + agent.run(args.task) + "\n" + "=" * 60)
    print(f"\nsteps={agent.steps} model={agent.last_model} "
          f"compactions={agent.compactions} cost=$0.00 stats={agent.client.stats}")
    print(f"trace={agent.trace_path}\ntranscript={agent.transcript_path}")


def run_doctor(config):
    import sys, urllib.request
    from pathlib import Path
    ok, fails = "✅", "❌"
    print("Agent1 Omni doctor\n")
    print(f"{ok if sys.version_info >= (3, 9) else fails} python {sys.version.split()[0]} (need 3.9+)")
    ws = Path(config.workspace)
    try:
        ws.mkdir(parents=True, exist_ok=True)
        probe = ws / ".trace" / ".writetest"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok"); probe.unlink()
        print(f"{ok} workspace writable: {ws.resolve()}")
    except Exception as e:
        print(f"{fails} workspace: {e}")
    key = config.api_key
    print(f"{ok if key else fails} OPENROUTER_API_KEY: "
          + (f"set (…{key[-4:]})" if key else "MISSING — copy .env.example to .env"))
    print(f"{ok} cascade: {len(config.cascade())} free models "
          f"(top: {config.cascade()[0]})")
    # fast network probe (8s cap, never hangs the doctor)
    try:
        req = urllib.request.Request(
            f"{config.base_url}/models",
            headers={"Authorization": f"Bearer {key}"} if key else {})
        with urllib.request.urlopen(req, timeout=8) as r:
            import json as _j
            n = len(_j.load(r).get("data", []))
        print(f"{ok} OpenRouter reachable ({n} models in catalog)")
    except Exception as e:
        print(f"{fails} OpenRouter unreachable from here: {str(e)[:120]}")
        print("   (sandbox networks may block it; your machine usually works. "
              "Use --demo to test offline.)")
    print(f"\napproval={config.approval} demo={config.demo} "
          f"history_budget={config.history_char_budget} plugins={config.plugins_dir or 'off'}")


if __name__ == "__main__":
    sys.exit(main())
