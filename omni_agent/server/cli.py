"""
CLI - Like OpenHands + Aider + Claude Code combined
Now with web server for Manus-like UI
"""
import typer
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from pathlib import Path

from ..config import OmniConfig
from ..core.agent import OmniAgent
from ..multi_agent.crew import create_dev_crew, create_research_crew, CrewTask

app = typer.Typer(help="OMNI-AGENT - Ultimate Agent CLI + Web UI (Manus-like)")
console = Console()

def get_config():
    try:
        return OmniConfig.from_env()
    except Exception as e:
        console.print(f"[red]Config error: {e}[/red]")
        console.print("[yellow]Set OPENROUTER_API_KEY env var. Get free key at https://openrouter.ai/keys[/yellow]")
        # Return dummy for init commands
        return OmniConfig(api_key=os.getenv("OPENROUTER_API_KEY", "dummy"))

@app.command()
def run(task: str, max_iter: int = 25, session: str = None, model: str = None):
    """Run a single task with OMNI-AGENT"""
    config = get_config()
    if model:
        config.default_model = model
    agent = OmniAgent(config=config, session_id=session)
    
    console.print(Panel(f"🚀 Task: {task}\nSession: {agent.session.id}\nModel: {config.default_model}", title="OMNI-AGENT"))
    
    result = agent.run(task, max_iterations=max_iter)
    
    console.print(Panel(Markdown(result["answer"]), title=f"✅ Completed in {result['iterations']} iterations"))
    console.print(f"📊 Tokens: {result['total_tokens']} | Model: {result['model_used']}")
    console.print(f"📝 Transcript: {result['transcript_path']}")

@app.command()
def chat():
    """Interactive chat mode"""
    config = get_config()
    agent = OmniAgent(config=config)
    
    console.print(Panel("💬 OMNI-AGENT Chat - Type 'exit' to quit, 'memory' to search memory", title="Chat"))
    
    while True:
        try:
            user_input = console.input("[bold cyan]You: [/bold cyan]")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            if user_input.lower().startswith("memory"):
                query = user_input.replace("memory", "").strip() or "general"
                from ..memory import HybridMemory
                mem = HybridMemory(config.memory_dir)
                results = mem.search(query)
                console.print(f"Memory results for '{query}': {results}")
                continue
            
            # If looks like a task, use full agent loop
            if len(user_input) > 100 or any(kw in user_input.lower() for kw in ["build", "create", "code", "analyze", "research"]):
                result = agent.run(user_input)
                console.print(Panel(Markdown(result["answer"]), title="🤖 OMNI"))
            else:
                answer = agent.chat(user_input)
                console.print(Panel(Markdown(answer), title="🤖 OMNI"))
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

@app.command()
def crew(task: str, roles: str = "senior_coder,researcher", parallel: bool = False):
    """Run a crew of agents"""
    config = get_config()
    role_names = [r.strip() for r in roles.split(",")]
    
    from ..multi_agent.crew import OmniCrew, PREDEFINED_ROLES
    crew_roles = [PREDEFINED_ROLES[r] for r in role_names if r in PREDEFINED_ROLES]
    
    if not crew_roles:
        console.print(f"[red]Invalid roles. Available: {list(PREDEFINED_ROLES.keys())}[/red]")
        return
    
    crew = OmniCrew(crew_roles, config=config)
    crew_task = CrewTask(description=task, expected_output="Complete the task with high quality")
    
    console.print(Panel(f"Crew: {', '.join([r.name for r in crew_roles])}\nTask: {task}", title="🚀 Crew Kickoff"))
    
    result = crew.kickoff([crew_task], parallel=parallel)
    
    console.print(Panel(Markdown(result["final_output"]), title="✅ Crew Result"))
    console.print(f"⏱️ {result['elapsed_seconds']:.1f}s | Tokens: {result['total_tokens']}")

@app.command()
def models():
    """List available free models"""
    from ..config import FREE_MODELS_REGISTRY
    console.print(Panel("Free Models Registry", title="📦 Models"))
    for category, models_list in FREE_MODELS_REGISTRY.items():
        console.print(f"[bold]{category}[/bold]:")
        for m in models_list:
            console.print(f"  - {m}")

@app.command()
def memory(query: str = "", list_all: bool = False):
    """Search or list memory"""
    config = get_config()
    from ..memory import HybridMemory
    mem = HybridMemory(config.memory_dir)
    
    if list_all:
        from ..memory import FileMemory
        fm = FileMemory(config.memory_dir)
        all_mem = fm.list_all()
        for m in all_mem:
            console.print(f"{m['category']}/{m['key']} - {m['size']} bytes")
    else:
        if not query:
            query = console.input("Search memory: ")
        results = mem.search(query)
        for r in results:
            console.print(Panel(r["content"][:500], title=f"{r['meta'].get('category','?')}/{r['meta'].get('key','?')}"))

@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000):
    """Start Manus-like web chat interface - Works on PC and Render"""
    # Render injects PORT env var
    port = int(os.getenv("PORT", port))
    
    console.print(Panel(f"""
🚀 Starting OMNI-AGENT Web UI (Manus-like)

• Web Chat: http://{host}:{port}/
• API Docs: http://{host}:{port}/docs
• Health: http://{host}:{port}/api/health

Works on:
• Your PC: python main.py serve
• Render: Auto-deploy with render.yaml
• Docker: docker run -p 8000:8000 omni-agent
• Any VPS

Features:
• Manus-like chat with tool calls & computer view
• Free OpenRouter models ($0 cost)
• File explorer & memory
• Crew & single agent modes
• Real-time agent execution

Get free key: https://openrouter.ai/keys
Set: OPENROUTER_API_KEY in .env or env var
    """, title="🌐 OMNI Web UI", border_style="blue"))
    
    from .api import start_server
    start_server(host=host, port=port)

@app.command()
def init():
    """Initialize workspace"""
    config = OmniConfig(api_key="dummy")  # Don't need key for init
    console.print(Panel(f"Workspace: {config.workspace_dir}\nMemory: {config.memory_dir}\nSkills: {config.skills_dir}", title="📁 Initialized"))
    
    # Create example .env if not exists
    if not Path(".env").exists() and Path(".env.example").exists():
        console.print("[yellow]Copy .env.example to .env and add your key: cp .env.example .env[/yellow]")
    
    console.print("[green]✅ Workspace ready! Run 'python main.py serve' to start web UI[/green]")

@app.command()
def web():
    """Shortcut for serve - start web UI"""
    serve()

if __name__ == "__main__":
    app()
