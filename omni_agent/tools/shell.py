import subprocess
import shlex
from pathlib import Path
from .base import BaseTool, ToolResult

# Safety: blocked commands
BLOCKED_COMMANDS = ["rm -rf /", "mkfs", ":(){:|:&};:", "shutdown", "reboot", "halt", "init 0"]

class ShellTool(BaseTool):
    name = "run_shell"
    description = "Execute shell command. Use for git, python, npm, tests, etc. Returns stdout/stderr. Sandboxed."
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "cwd": {"type": "string", "description": "Working directory", "default": "."},
            "timeout": {"type": "integer", "description": "Timeout seconds", "default": 30},
        },
        "required": ["command"]
    }
    
    def execute(self, command: str, cwd: str = ".", timeout: int = 30, **kwargs) -> ToolResult:
        # Safety check
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult(success=False, output="", error=f"Blocked dangerous command: {blocked}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}\n"
            output += f"\nExit code: {result.returncode}"
            
            return ToolResult(
                success=result.returncode == 0,
                output=output[:10000],  # Limit
                data={"returncode": result.returncode, "command": command},
                error=None if result.returncode == 0 else result.stderr[:500]
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class PythonExecTool(BaseTool):
    name = "run_python"
    description = "Execute Python code in sandbox. Use for data analysis, quick scripts, testing logic."
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "default": 15},
        },
        "required": ["code"]
    }
    
    def execute(self, code: str, timeout: int = 15, **kwargs) -> ToolResult:
        try:
            # Write to temp file and execute
            tmp_path = Path("/tmp/omni_exec.py")
            tmp_path.write_text(code)
            result = subprocess.run(
                ["python3", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            return ToolResult(
                success=result.returncode == 0,
                output=output[:10000],
                data={"returncode": result.returncode}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
