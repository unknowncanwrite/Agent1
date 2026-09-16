"""
OMNI-AGENT - Main Entry Point - Works on PC and Render
Auto-installs deps if missing (fixes PEP 668 + venv issues)
"""
import os
import sys
from pathlib import Path
import subprocess

def ensure_deps():
    try:
        import fastapi
        import httpx
        import uvicorn
        return True
    except ImportError as e:
        print(f"⚠️ Missing dependency: {e}")
        print("📦 Auto-installing minimal requirements (PEP 668 fix)...")
        req_file = "requirements-render.txt" if Path("requirements-render.txt").exists() else "requirements.txt"
        if not Path(req_file).exists():
            req_file = "requirements.txt"
        # Set env to bypass PEP 668
        env = os.environ.copy()
        env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--break-system-packages", "--quiet"], env=env)
            print(f"✅ Installed {req_file}")
            return True
        except:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"], env=env)
                print(f"✅ Installed {req_file}")
                return True
            except Exception as e2:
                print(f"⚠️ Auto-install failed: {e2}")
                return False

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
    ensure_deps()
    try:
        from omni_agent.server.cli import app as cli_app
    except ImportError as e2:
        print(f"❌ Still failing: {e2}")
        cli_app = None

if __name__ == "__main__":
    if cli_app is None:
        print("❌ Failed to import - trying minimal server...")
        try:
            from omni_agent.server.api import start_server
            port = int(os.getenv("PORT", 8000))
            start_server(host="0.0.0.0", port=port)
        except Exception as e:
            print(f"❌ Minimal server also failed: {e}")
            sys.exit(1)
    else:
        if len(sys.argv) == 1:
            from omni_agent.server.api import start_server
            port = int(os.getenv("PORT", 8000))
            print(f"🚀 Starting web server at http://0.0.0.0:{port}")
            start_server(host="0.0.0.0", port=port)
        else:
            cli_app()
