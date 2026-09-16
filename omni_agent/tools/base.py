"""
Tool Base - All tools inherit from this
Supports OpenAI function calling format + MCP + A2A
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

@dataclass
class ToolResult:
    success: bool
    output: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base tool"
    parameters: Dict[str, Any] = {}
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
    
    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def to_mcp_tool(self) -> Dict[str, Any]:
        """Convert to MCP format"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters
        }

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        return list(self.tools.values())
    
    def to_openai_tools(self) -> List[Dict]:
        return [t.to_openai_tool() for t in self.tools.values()]
    
    def execute(self, name: str, arguments: Dict) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Tool {name} not found")
        try:
            # Handle JSON string args
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Tool execution failed: {str(e)}")

# Global registry
global_registry = ToolRegistry()
