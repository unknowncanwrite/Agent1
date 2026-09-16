from pathlib import Path
from typing import Dict, Any
import os
import shutil
from .base import BaseTool, ToolResult

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read content of a file. Use for code, docs, configs. Supports text files."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")
            if p.stat().st_size > 1_000_000:
                return ToolResult(success=False, output="", error="File too large (>1MB), use chunked reading")
            content = p.read_text(encoding='utf-8', errors='ignore')
            return ToolResult(success=True, output=content[:20000], data={"path": str(p), "size": len(content)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write or create a file with content. Creates parent dirs automatically. Use for code generation, docs."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"]
    }
    
    def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return ToolResult(success=True, output=f"Written {len(content)} chars to {path}", data={"path": str(p)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Edit file by replacing old_text with new_text. Precise edit, fails if old_text not found."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "old_text": {"type": "string", "description": "Text to find"},
            "new_text": {"type": "string", "description": "Replacement text"},
        },
        "required": ["path", "old_text", "new_text"]
    }
    
    def execute(self, path: str, old_text: str, new_text: str, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, output="", error="File not found")
            content = p.read_text(encoding='utf-8')
            if old_text not in content:
                return ToolResult(success=False, output="", error="old_text not found in file")
            new_content = content.replace(old_text, new_text, 1)
            p.write_text(new_content, encoding='utf-8')
            return ToolResult(success=True, output=f"Edited {path}: replaced 1 occurrence")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class ListFilesTool(BaseTool):
    name = "list_files"
    description = "List files and directories in a path. Use to explore codebase."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path", "default": "."},
            "recursive": {"type": "boolean", "description": "Recursive listing", "default": False},
        },
        "required": ["path"]
    }
    
    def execute(self, path: str = ".", recursive: bool = False, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, output="", error=f"Path not found: {path}")
            if recursive:
                files = [str(x) for x in p.rglob("*") if x.is_file()][:200]
            else:
                files = [str(x) for x in p.iterdir()][:200]
            output = "\n".join(files)
            return ToolResult(success=True, output=output, data={"count": len(files)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a file or directory. Use with caution."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to delete"},
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return ToolResult(success=True, output=f"Deleted {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
