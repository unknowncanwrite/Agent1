"""
FastAPI Server - Expose OMNI-AGENT as API + Manus-like Web Chat
Works on PC and Render
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import uvicorn
import os

from ..config import OmniConfig
from ..core.agent import OmniAgent
from ..multi_agent.crew import OmniCrew, CrewTask, PREDEFINED_ROLES
from ..multi_agent.roles import AgentRole

# Paths
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
WORKSPACE_DIR = Path(os.getenv("OMNI_WORKSPACE", "./workspace"))

app = FastAPI(
    title="OMNI-AGENT API",
    description="Ultimate Agent that overcomes all others - Free OpenRouter models + Manus-like Web UI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global config
try:
    config = OmniConfig.from_env()
except:
    config = OmniConfig(api_key=os.getenv("OPENROUTER_API_KEY", "dummy"))

class TaskRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    max_iterations: Optional[int] = 25
    model: Optional[str] = None

class CrewRequest(BaseModel):
    tasks: List[Dict[str, str]]
    roles: List[str]
    parallel: bool = False

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

# API Routes (must be before static mount)

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0", "mode": "manus-like web chat", "workspace": str(WORKSPACE_DIR)}

@app.get("/api")
def api_root():
    return {
        "name": "OMNI-AGENT",
        "version": "2.0.0",
        "description": "Ultimate agent + Manus-like web UI - Works on PC and Render",
        "web_ui": "/",
        "api_docs": "/docs",
        "features": [
            "Manus-like web chat interface",
            "Multi-agent crews (CrewAI++)",
            "Stateful graphs (LangGraph++)",
            "Coding superpowers (OpenHands++)",
            "Hybrid memory (Mem0 + OpenClaw)",
            "Free OpenRouter models with auto-failover",
            "Works on PC and Render",
            "30+ tools, skills, sub-agents"
        ],
        "endpoints": ["/api/run", "/api/chat", "/api/crew", "/api/models", "/api/files", "/api/sessions"]
    }

@app.post("/api/run")
def run_task(req: TaskRequest):
    try:
        agent = OmniAgent(config=config, session_id=req.session_id)
        # Override model if specified
        if req.model:
            agent.config.default_model = req.model
            agent.config.fallback_models = [req.model] + agent.config.fallback_models
        result = agent.run(req.task, max_iterations=req.max_iterations)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        agent = OmniAgent(config=config, session_id=req.session_id)
        answer = agent.chat(req.message)
        return {"answer": answer, "session_id": agent.session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew")
def run_crew(req: CrewRequest):
    try:
        roles = [PREDEFINED_ROLES[r] for r in req.roles if r in PREDEFINED_ROLES]
        if not roles:
            raise HTTPException(status_code=400, detail=f"Invalid roles. Available: {list(PREDEFINED_ROLES.keys())}")
        
        crew = OmniCrew(roles, config=config)
        crew_tasks = []
        for t in req.tasks:
            role = PREDEFINED_ROLES.get(t.get("role")) if t.get("role") else None
            crew_tasks.append(CrewTask(
                description=t["description"],
                expected_output=t.get("expected_output", "Complete the task"),
                assigned_role=role
            ))
        
        result = crew.kickoff(crew_tasks, parallel=req.parallel)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
def list_models():
    from ..config import FREE_MODELS_REGISTRY
    return {
        "free_models": FREE_MODELS_REGISTRY,
        "current_default": config.default_model,
        "fallbacks": config.fallback_models,
        "for_ui": [
            {"id": "qwen/qwen3-coder:free", "name": "Qwen3 Coder", "desc": "Best for coding, 1M context", "icon": "⚡"},
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "Nemotron Ultra", "desc": "550B MoE, 1M reasoning", "icon": "🧠"},
            {"id": "openai/gpt-oss-120b:free", "name": "GPT-OSS 120B", "desc": "Strong reasoning", "icon": "💡"},
            {"id": "google/gemma-4-31b-it:free", "name": "Gemma 4 31B", "desc": "Multimodal", "icon": "🌐"},
            {"id": "openrouter/free", "name": "Auto Router", "desc": "Auto picks best free", "icon": "🔀"},
        ]
    }

@app.get("/api/memory")
def list_memory():
    from ..memory import FileMemory
    fm = FileMemory(config.memory_dir)
    return {"memories": fm.list_all()}

@app.get("/api/skills")
def list_skills():
    from ..skills.loader import SkillLoader
    loader = SkillLoader(config.skills_dir)
    return {"skills": loader.list_skills()}

@app.get("/api/files")
def list_files(path: str = "."):
    """List workspace files - Manus-like computer"""
    try:
        base = WORKSPACE_DIR
        # Security: prevent path traversal outside workspace, but allow workspace itself
        target = (base / path).resolve() if path != "." else base.resolve()
        
        # Ensure target is within workspace or workspace itself
        if not str(target).startswith(str(base.resolve())) and str(target) != str(base.resolve()):
            target = base.resolve()
        
        if not target.exists():
            return {"files": [], "path": str(path)}
        
        files = []
        # List files in workspace recursively but limit depth
        for item in target.rglob("*"):
            if item.is_file():
                # Skip hidden and cache
                if any(part.startswith('.') for part in item.parts):
                    continue
                if '__pycache__' in str(item) or 'node_modules' in str(item):
                    continue
                # Relative to workspace
                try:
                    rel = item.relative_to(base)
                    files.append({
                        "name": item.name,
                        "path": str(rel),
                        "full_path": str(item),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime
                    })
                except:
                    continue
            if len(files) > 100:
                break
        
        # Sort by modified desc
        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"files": files[:100], "path": str(target), "count": len(files)}
    except Exception as e:
        return {"files": [], "error": str(e), "path": path}

@app.get("/api/files/read")
def read_file(path: str = Query(..., description="File path relative to workspace")):
    """Read a workspace file"""
    try:
        base = WORKSPACE_DIR.resolve()
        target = (base / path).resolve()
        
        # Security check
        if not str(target).startswith(str(base)):
            raise HTTPException(status_code=403, detail="Access denied - outside workspace")
        
        if not target.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if target.stat().st_size > 500_000:
            raise HTTPException(status_code=413, detail="File too large")
        
        content = target.read_text(encoding='utf-8', errors='ignore')
        return {"path": path, "content": content[:10000], "size": len(content)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
def list_sessions():
    """List chat sessions"""
    try:
        sessions_dir = WORKSPACE_DIR / "sessions"
        if not sessions_dir.exists():
            return {"sessions": []}
        
        sessions = []
        for f in sessions_dir.glob("*.json"):
            try:
                import json
                data = json.loads(f.read_text())
                sessions.append({
                    "id": data.get("id", f.stem),
                    "created_at": data.get("created_at", ""),
                    "message_count": len(data.get("messages", [])),
                    "task": data.get("metadata", {}).get("task", "")[:100]
                })
            except:
                continue
        
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        return {"sessions": sessions[:20]}
    except Exception as e:
        return {"sessions": [], "error": str(e)}

@app.get("/api/tools")
def list_tools():
    from ..tools import get_default_tools
    registry = get_default_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in registry.list_tools()
        ]
    }

# Serve static files and frontend (must be last)
# Create static dir if not exists
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for JS, CSS, etc.
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_frontend():
    """Serve Manus-like web UI"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        # Fallback if no UI yet
        return JSONResponse({
            "message": "OMNI-AGENT API is running. Web UI not found.",
            "api_docs": "/docs",
            "health": "/api/health",
            "frontend_expected_at": str(index_path)
        })

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """SPA fallback - serve index.html for frontend routing, but not for api"""
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Not found")

def start_server(host: str = "0.0.0.0", port: int = 8000):
    # Get port from env for Render
    port = int(os.getenv("PORT", port))
    print(f"🚀 OMNI-AGENT starting at http://{host}:{port}")
    print(f"📁 Workspace: {WORKSPACE_DIR}")
    print(f"🌐 Web UI: http://{host}:{port}/")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"💾 Static: {STATIC_DIR}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()
