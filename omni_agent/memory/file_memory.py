"""
File-based memory - Git-backable, human-readable
Inspired by OpenClaw's markdown memory
"""
from pathlib import Path
from typing import List, Dict, Optional
import datetime

class FileMemory:
    def __init__(self, memory_dir: Path):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        # Subdirs
        for sub in ["learnings", "facts", "preferences", "skills", "sessions"]:
            (self.memory_dir / sub).mkdir(exist_ok=True)
    
    def write(self, category: str, key: str, content: str, append: bool = True):
        dir_path = self.memory_dir / category
        dir_path.mkdir(exist_ok=True)
        file_path = dir_path / f"{key}.md"
        
        timestamp = datetime.datetime.now().isoformat()
        entry = f"\n## {timestamp}\n{content}\n"
        
        if append and file_path.exists():
            existing = file_path.read_text()
            file_path.write_text(existing + entry)
        else:
            header = f"# {key}\nCategory: {category}\nCreated: {timestamp}\n\n"
            file_path.write_text(header + content)
        
        return file_path
    
    def read(self, category: str, key: str) -> Optional[str]:
        file_path = self.memory_dir / category / f"{key}.md"
        if file_path.exists():
            return file_path.read_text()
        return None
    
    def search(self, query: str, category: Optional[str] = None) -> List[Dict]:
        results = []
        search_dirs = [self.memory_dir / category] if category else list(self.memory_dir.iterdir())
        
        for dir_path in search_dirs:
            if not dir_path.is_dir():
                continue
            for file_path in dir_path.glob("*.md"):
                try:
                    content = file_path.read_text()
                    if query.lower() in content.lower():
                        # Score by relevance
                        score = content.lower().count(query.lower())
                        results.append({
                            "file": str(file_path),
                            "category": dir_path.name,
                            "key": file_path.stem,
                            "snippet": content[:500],
                            "score": score
                        })
                except:
                    continue
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:10]
    
    def list_all(self) -> List[Dict]:
        all_mem = []
        for cat_dir in self.memory_dir.iterdir():
            if cat_dir.is_dir():
                for f in cat_dir.glob("*.md"):
                    all_mem.append({
                        "category": cat_dir.name,
                        "key": f.stem,
                        "path": str(f),
                        "size": f.stat().st_size
                    })
        return all_mem
    
    def get_context_prompt(self, query: str, max_tokens: int = 2000) -> str:
        """Get relevant memory for prompt injection"""
        results = self.search(query)
        if not results:
            return ""
        
        context = "## Relevant Memory:\n"
        total_chars = 0
        for r in results:
            snippet = f"\n### {r['category']}/{r['key']}\n{r['snippet']}\n"
            if total_chars + len(snippet) > max_tokens * 4:  # Rough char->token
                break
            context += snippet
            total_chars += len(snippet)
        
        return context
