import requests
from bs4 import BeautifulSoup
from typing import Optional
from .base import BaseTool, ToolResult

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web using DuckDuckGo. Use for research, docs, current info."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5, "description": "Max results"},
        },
        "required": ["query"]
    }
    
    def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        if not HAS_DDGS:
            return ToolResult(success=False, output="", error="duckduckgo-search not installed")
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
            output = "\n---\n".join(results)
            return ToolResult(success=True, output=output, data={"count": len(results)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract text from a URL. Use for reading docs, articles."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"]
    }
    
    def execute(self, url: str, **kwargs) -> ToolResult:
        try:
            headers = {"User-Agent": "OMNI-AGENT/1.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            # Try to parse HTML
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove script/style
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator='\n')
            # Clean
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned = "\n".join(lines)[:15000]
            
            return ToolResult(success=True, output=cleaned, data={"url": url, "status": resp.status_code})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class FetchPageTool(WebFetchTool):
    name = "fetch_page"
    description = "Alias for web_fetch - fetch page content"

class GitTool(BaseTool):
    name = "git_operations"
    description = "Perform git operations: status, log, diff, commit, branch."
    parameters = {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["status", "log", "diff", "branch", "commit"], "description": "Git operation"},
            "message": {"type": "string", "description": "Commit message if operation is commit"},
            "path": {"type": "string", "default": ".", "description": "Repo path"},
        },
        "required": ["operation"]
    }
    
    def execute(self, operation: str, message: str = "", path: str = ".", **kwargs) -> ToolResult:
        import subprocess
        try:
            if operation == "status":
                cmd = ["git", "status", "--porcelain", "-b"]
            elif operation == "log":
                cmd = ["git", "log", "--oneline", "-20"]
            elif operation == "diff":
                cmd = ["git", "diff", "HEAD"]
            elif operation == "branch":
                cmd = ["git", "branch", "-a"]
            elif operation == "commit":
                if not message:
                    return ToolResult(success=False, output="", error="Commit message required")
                # Add all and commit
                subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
                cmd = ["git", "commit", "-m", message]
            else:
                return ToolResult(success=False, output="", error="Invalid operation")
            
            result = subprocess.run(cmd, cwd=path, capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            return ToolResult(success=result.returncode == 0, output=output[:10000])
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
