"""
Transcript - JSONL logging for observability
Inspired by OpenClaw's JSONL transcripts
"""
from pathlib import Path
from typing import Dict, Any, List
import json
import datetime

class Transcript:
    def __init__(self, transcript_dir: Path, session_id: str):
        self.transcript_dir = Path(transcript_dir)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.file_path = self.transcript_dir / f"{session_id}.jsonl"
        self.events: List[Dict] = []
    
    def log(self, event_type: str, data: Dict[str, Any]):
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "type": event_type,
            "data": data
        }
        self.events.append(event)
        # Append to file
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    def log_message(self, role: str, content: str, model: str = None):
        self.log("message", {"role": role, "content": content[:5000], "model": model})
    
    def log_tool_call(self, tool_name: str, args: Dict, result: Dict):
        self.log("tool_call", {"tool": tool_name, "args": args, "result": result})
    
    def log_thinking(self, thought: str):
        self.log("thinking", {"thought": thought})
    
    def get_history(self) -> List[Dict]:
        return self.events
    
    def replay(self) -> str:
        """Human-readable replay"""
        output = f"# Transcript: {self.session_id}\n\n"
        for e in self.events:
            if e["type"] == "message":
                output += f"**{e['data']['role']}**: {e['data']['content'][:500]}\n\n"
            elif e["type"] == "tool_call":
                output += f"🔧 {e['data']['tool']}({e['data']['args']}) -> {str(e['data']['result'])[:200]}\n\n"
        return output
