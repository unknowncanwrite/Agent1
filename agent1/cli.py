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

    args = p.parse_args(argv)
    config = AgentConfig.load()
    if args.approval: config.approval = args.approval
    if getattr(args, "model", None): config.model_override = args.model
    if args.workspace: config.workspace = args.workspace
    if getattr(args, "max_steps", None): config.max_steps = args.max_steps

    client = MockClient() if getattr(args, "demo", False) else None

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

    if args.cmd == "serve":
        from .server import serve
        serve(args.host, args.port)
        return

    on_event = _print_events(verbose=True)
    if args.cmd == "chat":
        agent = Agent(config=config, client=client, on_event=on_event)
        print("Agent1 Omni chat (free models). Empty line quits.\n")
        while True:
            try:
                msg = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not msg:
                break
            print(agent.ask(msg) + "\n")
        return

    if args.cmd == "crew":
        print(f"👥 Crew ({args.mode}) working on: {args.task}\n")
        print(Crew(config=config, client=client, on_event=on_event).run(args.task, args.mode))
        return

    print(f"🤖 Agent ({args.role}/{args.mode}) working on: {args.task}\n")
    agent = Agent(config=config, client=client, role=args.role,
                  task_kind=args.mode, on_event=on_event)
    print("\n" + "=" * 60 + "\n" + agent.run(args.task) + "\n" + "=" * 60)
    print(f"\nsteps={agent.steps} cost=$0.00 stats={agent.client.stats}")


if __name__ == "__main__":
    sys.exit(main())
