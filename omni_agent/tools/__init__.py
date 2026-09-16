from .base import BaseTool, ToolRegistry, global_registry, ToolResult
from .filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListFilesTool, DeleteFileTool
from .shell import ShellTool, PythonExecTool
from .web import WebSearchTool, WebFetchTool, FetchPageTool, GitTool
from .code import CodeAnalysisTool, TestRunnerTool
from .memory_tools import MemorySearchTool, MemoryWriteTool, SkillLoaderTool

def get_default_tools():
    registry = ToolRegistry()
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        ListFilesTool(),
        DeleteFileTool(),
        ShellTool(),
        PythonExecTool(),
        WebSearchTool(),
        WebFetchTool(),
        FetchPageTool(),
        GitTool(),
        CodeAnalysisTool(),
        TestRunnerTool(),
        MemorySearchTool(),
        MemoryWriteTool(),
        SkillLoaderTool(),
    ]
    for t in tools:
        registry.register(t)
    return registry

__all__ = ["BaseTool", "ToolRegistry", "global_registry", "ToolResult", "get_default_tools"]
