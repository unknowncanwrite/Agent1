"""
Logger with rich output
"""
from pathlib import Path
from typing import Any
import datetime
from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()

class OmniLogger:
    def __init__(self, log_dir: Path = Path("./workspace/logs")):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup python logging with rich
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True)]
        )
        self.logger = logging.getLogger("omni")
    
    def info(self, msg: str):
        console.print(f"[cyan]ℹ️ {msg}[/cyan]")
        self.logger.info(msg)
        self._write_file("info", msg)
    
    def error(self, msg: str):
        console.print(f"[red]❌ {msg}[/red]")
        self.logger.error(msg)
        self._write_file("error", msg)
    
    def success(self, msg: str):
        console.print(f"[green]✅ {msg}[/green]")
        self.logger.info(f"SUCCESS: {msg}")
        self._write_file("success", msg)
    
    def warning(self, msg: str):
        console.print(f"[yellow]⚠️ {msg}[/yellow]")
        self.logger.warning(msg)
        self._write_file("warning", msg)
    
    def tool(self, tool_name: str, args: Any, result: Any = None):
        console.print(f"[magenta]🔧 {tool_name}({args})[/magenta]")
        if result:
            console.print(f"   → {str(result)[:200]}")
    
    def _write_file(self, level: str, msg: str):
        try:
            log_file = self.log_dir / f"{datetime.datetime.now().date()}.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().isoformat()} [{level}] {msg}\n")
        except:
            pass
