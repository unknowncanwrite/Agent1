"""
OMNI-AGENT - Main Entry Point - Works on PC and Render
Auto-installs deps + fixes Render venv + .local path issues
"""
import os
import sys
from pathlib import Path
import subprocess
import site

# Fix Render paths - add .venv and .local site-packages to path
# Render installs to .venv or /opt/render/.local
possible_paths = [
    Path(".venv/lib/python3.11/site-packages"),
    Path(".venv/lib/python3.10/site-packages"),
    Path(".venv/lib/python3.12/site-packages"),
    Path("/opt/render/.local/lib/python3.11/site-packages"),
    Path("/opt/render/project/src/.venv/lib/python3.11/site-packages"),
    Path.home() / ".local/lib/python3.11/site-packages",
]
for p in possible_paths:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Also add user site
try:
    user_site = site.getusersitepackages()
    if user_site and user_site not in sys.path:
        sys.path.insert(0, user_site)
except:
    pass

def ensure_deps():
    try:
        import fastapi
        import httpx
        import uvicorn
        return True
    except ImportError as e:
        print(f"⚠️ Missing dependency: {e}")
        print(f"📦 Python path: {sys.path[:3]}")
        print(f"📦 Trying to install...")
        req_file = "requirements-render.txt" if Path("requirements-render.txt").exists() else "requirements.txt"
        env = os.environ.copy()
        env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"
        # Try multiple ways
        cmds = [
            [sys.executable, "-m", "pip", "install", "-r", req_file, "--break-system-packages"],
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            ["pip", "install", "-r", req_file, "--break-system-packages"],
            ["pip3", "install", "-r", req_file, "--break-system-packages"],
        ]
        for cmd in cmds:
            try:
                print(f"   Trying: {' '.join(cmd)}")
                subprocess.check_call(cmd, env=env)
                print(f"✅ Installed {req_file} via {' '.join(cmd[:3])}")
                # Try import again
                try:
                    import fastapi
                    import httpx
                    print("✅ Dependencies now available!")
                    return True
                except ImportError:
                    continue
            except Exception as ex:
                print(f"   Failed: {ex}")
                continue
        return False

# Ensure deps before anything
if not ensure_deps():
    print("⚠️ First ensure failed, trying again with full install...")
    ensure_deps()

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path(__file__).parent / ".env")
    demo_env = Path("./workspace/.env")
    if demo_env.exists():
        load_dotenv(demo_env)
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

if not os.getenv("OPENROUTER_API_KEY"):
    print("⚠️  OPENROUTER_API_KEY not set! Get free key at https://openrouter.ai/keys")
    os.environ["OPENROUTER_API_KEY"] = "dummy-key-for-ui"

workspace = Path(os.getenv("OMNI_WORKSPACE", "./workspace"))
workspace.mkdir(parents=True, exist_ok=True)
for sub in ["memory", "skills", "transcripts", "sessions", "logs"]:
    (workspace / sub).mkdir(exist_ok=True)

try:
    from omni_agent.server.cli import app as cli_app
except ImportError as e:
    print(f"⚠️ Import failed: {e}")
    if ensure_deps():
        try:
            from omni_agent.server.cli import app as cli_app
        except ImportError as e2:
            print(f"❌ Still failing: {e2}")
            cli_app = None
    else:
        cli_app = None

if __name__ == "__main__":
    if cli_app is None:
        print("❌ Failed to import CLI, trying minimal web server...")
        try:
            from omni_agent.server.api import start_server
            port = int(os.getenv("PORT", 8000))
            start_server(host="0.0.0.0", port=port)
        except Exception as e:
            print(f"❌ Minimal server also failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        if len(sys.argv) == 1:
            from omni_agent.server.api import start_server
            port = int(os.getenv("PORT", 8000))
            print(f"🚀 Starting web server at http://0.0.0.0:{port}")
            start_server(host="0.0.0.0", port=port)
        else:
            cli_app()
