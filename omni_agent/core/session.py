"""
Session Management - Per-agent isolation, persistence
"""
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
import uuid
import datetime

@dataclass
class Session:
    id: str
    created_at: str
    workspace: Path
    messages: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, tool_calls: List = None):
        msg = {"role": role, "content": content, "timestamp": datetime.datetime.now().isoformat()}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)
    
    def get_messages_for_llm(self) -> List[Dict]:
        """Get messages in OpenAI format"""
        llm_messages = []
        for m in self.messages:
            # Only role and content/tool_calls
            out = {"role": m["role"], "content": m["content"]}
            if "tool_calls" in m:
                out["tool_calls"] = m["tool_calls"]
            llm_messages.append(out)
        return llm_messages
    
    def save(self, sessions_dir: Path):
        sessions_dir.mkdir(parents=True, exist_ok=True)
        file_path = sessions_dir / f"{self.id}.json"
        data = {
            "id": self.id,
            "created_at": self.created_at,
            "workspace": str(self.workspace),
            "messages": self.messages,
            "metadata": self.metadata
        }
        file_path.write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, session_id: str, sessions_dir: Path) -> Optional["Session"]:
        file_path = sessions_dir / f"{session_id}.json"
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text())
        return cls(
            id=data["id"],
            created_at=data["created_at"],
            workspace=Path(data["workspace"]),
            messages=data.get("messages", []),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def create(cls, workspace: Path, session_id: Optional[str] = None) -> "Session":
        sid = session_id or str(uuid.uuid4())
        return cls(
            id=sid,
            created_at=datetime.datetime.now().isoformat(),
            workspace=workspace,
            messages=[],
            metadata={}
        )

class SessionManager:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Session] = {}
    
    def create_session(self, workspace: Path = None, session_id: str = None) -> Session:
        workspace = workspace or self.base_dir
        session = Session.create(workspace, session_id)
        self.sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        if session_id in self.sessions:
            return self.sessions[session_id]
        # Try load from disk
        loaded = Session.load(session_id, self.base_dir)
        if loaded:
            self.sessions[session_id] = loaded
        return loaded
    
    def save_all(self):
        for session in self.sessions.values():
            session.save(self.base_dir)
    
    def list_sessions(self) -> List[Dict]:
        sessions = []
        for f in self.base_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                sessions.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "message_count": len(data.get("messages", []))
                })
            except:
                continue
        return sessions
