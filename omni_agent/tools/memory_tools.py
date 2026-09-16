from .base import BaseTool, ToolResult
from pathlib import Path
import json

class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "Search agent's long-term memory (markdown files, previous learnings)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for memory"},
        },
        "required": ["query"]
    }
    
    def execute(self, query: str, **kwargs) -> ToolResult:
        try:
            memory_dir = Path("./workspace/memory")
            if not memory_dir.exists():
                return ToolResult(success=True, output="No memory yet", data={"results": []})
            
            results = []
            for f in memory_dir.rglob("*.md"):
                try:
                    content = f.read_text()[:5000]
                    if query.lower() in content.lower():
                        results.append(f"{f.name}: {content[:500]}...")
                except:
                    continue
            
            output = "\n---\n".join(results) if results else f"No memory found for '{query}'"
            return ToolResult(success=True, output=output, data={"count": len(results)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class MemoryWriteTool(BaseTool):
    name = "memory_write"
    description = "Write to long-term memory. Use to store learnings, preferences, facts for future."
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Memory key / filename"},
            "content": {"type": "string", "description": "Content to remember"},
            "category": {"type": "string", "default": "general", "description": "Category: learnings, preferences, facts, skills"},
        },
        "required": ["key", "content"]
    }
    
    def execute(self, key: str, content: str, category: str = "general", **kwargs) -> ToolResult:
        try:
            memory_dir = Path(f"./workspace/memory/{category}")
            memory_dir.mkdir(parents=True, exist_ok=True)
            file_path = memory_dir / f"{key}.md"
            existing = ""
            if file_path.exists():
                existing = file_path.read_text() + "\n\n---\n\n"
            file_path.write_text(existing + content)
            return ToolResult(success=True, output=f"Memory written to {file_path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class SkillLoaderTool(BaseTool):
    name = "load_skill"
    description = "Load a skill (markdown prompt) to extend agent capabilities. Skills are reusable workflows."
    parameters = {
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "Skill name to load"},
        },
        "required": ["skill_name"]
    }
    
    def execute(self, skill_name: str, **kwargs) -> ToolResult:
        try:
            skills_dir = Path("./workspace/skills")
            for ext in [".md", ".txt", ""]:
                p = skills_dir / f"{skill_name}{ext}"
                if p.exists():
                    content = p.read_text()
                    return ToolResult(success=True, output=content, data={"skill": skill_name})
            
            # Check builtin skills
            builtin = Path(f"./omni_agent/skills/examples/{skill_name}.md")
            if builtin.exists():
                content = builtin.read_text()
                return ToolResult(success=True, output=content)
            
            return ToolResult(success=False, output="", error=f"Skill {skill_name} not found")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
