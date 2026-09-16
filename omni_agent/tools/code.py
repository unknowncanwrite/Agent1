from .base import BaseTool, ToolResult
from pathlib import Path
import subprocess
import ast

class CodeAnalysisTool(BaseTool):
    name = "analyze_code"
    description = "Analyze Python code for errors, complexity, structure."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path or code string"},
            "is_file": {"type": "boolean", "default": True, "description": "Whether path is file"},
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, is_file: bool = True, **kwargs) -> ToolResult:
        try:
            if is_file:
                content = Path(path).read_text()
            else:
                content = path
            
            tree = ast.parse(content)
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            imports = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imports.extend([alias.name for alias in n.names])
                elif isinstance(n, ast.ImportFrom):
                    imports.append(n.module)
            
            output = f"Functions: {funcs}\nClasses: {classes}\nImports: {imports}\nLines: {len(content.splitlines())}"
            return ToolResult(success=True, output=output, data={"funcs": funcs, "classes": classes})
        except SyntaxError as e:
            return ToolResult(success=False, output="", error=f"Syntax error: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class TestRunnerTool(BaseTool):
    name = "run_tests"
    description = "Run tests using pytest or python. Use to verify code."
    parameters = {
        "type": "object",
        "properties": {
            "test_path": {"type": "string", "default": ".", "description": "Test file or directory"},
            "framework": {"type": "string", "enum": ["pytest", "unittest", "auto"], "default": "auto"},
        },
        "required": []
    }
    
    def execute(self, test_path: str = ".", framework: str = "auto", **kwargs) -> ToolResult:
        try:
            if framework == "auto":
                # Detect
                if Path(test_path).is_file() and "test" in test_path:
                    cmd = ["python3", "-m", "pytest", test_path, "-v"]
                else:
                    cmd = ["python3", "-m", "pytest", test_path, "-v"]
            elif framework == "pytest":
                cmd = ["python3", "-m", "pytest", test_path, "-v"]
            else:
                cmd = ["python3", "-m", "unittest", "discover", "-s", test_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout + "\n" + result.stderr
            return ToolResult(success=result.returncode == 0, output=output[:10000])
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
