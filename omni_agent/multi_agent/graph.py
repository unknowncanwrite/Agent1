"""
Stateful Graph - LangGraph-inspired but simpler and more powerful
Directed graph with nodes = agents/tools, edges = transitions
Supports human-in-the-loop, checkpointing, branching
"""
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

class NodeType(Enum):
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    HUMAN = "human"
    END = "end"

@dataclass
class GraphNode:
    id: str
    type: NodeType
    func: Optional[Callable] = None
    agent_role: Optional[str] = None
    next_nodes: List[str] = field(default_factory=list)
    condition: Optional[Callable] = None  # For conditional edges
    metadata: Dict = field(default_factory=dict)

@dataclass
class GraphState:
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    current_node: Optional[str] = None
    completed: bool = False
    
    def update(self, key: str, value: Any):
        self.data[key] = value
        self.history.append({"key": key, "value": str(value)[:500], "node": self.current_node})
    
    def get(self, key: str, default=None):
        return self.data.get(key, default)

class OmniGraph:
    """
    Stateful workflow graph - more explicit control than CrewAI
    """
    def __init__(self, name: str = "omni_graph"):
        self.name = name
        self.nodes: Dict[str, GraphNode] = {}
        self.start_node: Optional[str] = None
        self.state = GraphState()
        self.checkpoint_dir = Path("./workspace/graph_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def add_node(self, node: GraphNode):
        self.nodes[node.id] = node
        if not self.start_node:
            self.start_node = node.id
    
    def add_edge(self, from_node: str, to_node: str, condition: Callable = None):
        if from_node in self.nodes:
            if condition:
                # Conditional edge
                self.nodes[from_node].next_nodes.append(to_node)
                # Store condition separately for evaluation
                if "conditions" not in self.nodes[from_node].metadata:
                    self.nodes[from_node].metadata["conditions"] = {}
                self.nodes[from_node].metadata["conditions"][to_node] = condition
            else:
                self.nodes[from_node].next_nodes.append(to_node)
    
    def set_start(self, node_id: str):
        self.start_node = node_id
    
    def _evaluate_next(self, current_node: GraphNode) -> Optional[str]:
        """Evaluate which next node to go to"""
        if not current_node.next_nodes:
            return None
        
        if len(current_node.next_nodes) == 1:
            return current_node.next_nodes[0]
        
        # Multiple next nodes - check conditions
        conditions = current_node.metadata.get("conditions", {})
        for next_id in current_node.next_nodes:
            cond = conditions.get(next_id)
            if cond:
                try:
                    if cond(self.state):
                        return next_id
                except:
                    continue
            else:
                # No condition, fallback
                return next_id
        
        # Default to first
        return current_node.next_nodes[0]
    
    def run(self, initial_state: Dict = None, max_steps: int = 20) -> GraphState:
        if initial_state:
            self.state.data.update(initial_state)
        
        current_id = self.start_node
        steps = 0
        
        print(f"🕸️ Graph {self.name} starting at {current_id}")
        
        while current_id and steps < max_steps and not self.state.completed:
            steps += 1
            node = self.nodes.get(current_id)
            if not node:
                print(f"❌ Node {current_id} not found")
                break
            
            self.state.current_node = current_id
            print(f"  → Step {steps}: {node.id} ({node.type.value})")
            
            try:
                if node.type == NodeType.AGENT and node.func:
                    result = node.func(self.state)
                    self.state.update(f"{node.id}_output", result)
                
                elif node.type == NodeType.TOOL and node.func:
                    result = node.func(self.state)
                    self.state.update(f"{node.id}_result", result)
                
                elif node.type == NodeType.CONDITION and node.condition:
                    result = node.condition(self.state)
                    self.state.update(f"{node.id}_condition", result)
                
                elif node.type == NodeType.HUMAN:
                    # Human-in-the-loop checkpoint
                    print(f"👤 Human input required at {node.id}")
                    print(f"Current state: {json.dumps(self.state.data, indent=2)[:1000]}")
                    # In real use, would wait for human
                    # For now, auto-continue
                    self.state.update(f"{node.id}_human", "auto-approved")
                
                elif node.type == NodeType.END:
                    self.state.completed = True
                    print(f"🏁 Graph completed at {node.id}")
                    break
                
                # Checkpoint
                self._checkpoint()
                
                # Next node
                next_id = self._evaluate_next(node)
                if not next_id:
                    print(f"🏁 No next node from {node.id}, ending")
                    self.state.completed = True
                    break
                
                current_id = next_id
                
            except Exception as e:
                print(f"❌ Node {node.id} failed: {e}")
                self.state.update(f"{node.id}_error", str(e))
                # Try to continue to next, or fail
                next_id = self._evaluate_next(node)
                if next_id:
                    current_id = next_id
                else:
                    break
        
        print(f"✅ Graph {self.name} finished in {steps} steps")
        return self.state
    
    def _checkpoint(self):
        """Save state for resumability"""
        try:
            checkpoint_path = self.checkpoint_dir / f"{self.name}_{self.state.current_node}.json"
            checkpoint_path.write_text(json.dumps({
                "data": self.state.data,
                "history": self.state.history[-10:],  # Last 10
                "current_node": self.state.current_node
            }, indent=2))
        except Exception as e:
            print(f"Checkpoint failed: {e}")
    
    def visualize(self) -> str:
        """Mermaid diagram"""
        mermaid = f"graph TD\n"
        for node_id, node in self.nodes.items():
            shape = "([%s])" % node_id if node.type == NodeType.END else "[%s]" % node_id
            mermaid += f"  {node_id}{shape}\n"
            for next_id in node.next_nodes:
                mermaid += f"  {node_id} --> {next_id}\n"
        return mermaid

# Example builder
def create_coding_workflow():
    """Example: Full coding workflow graph"""
    from ..config import OmniConfig
    from ..core.agent import OmniAgent
    
    config = OmniConfig.from_env() if False else OmniConfig(api_key="dummy")
    
    graph = OmniGraph("coding_workflow")
    
    def planner(state: GraphState):
        # Use agent to plan
        task = state.get("task", "Build a feature")
        return f"Plan for: {task} - Break into 3 steps"
    
    def coder(state: GraphState):
        plan = state.get("planner_output", "")
        return f"Code based on plan: {plan}"
    
    def tester(state: GraphState):
        code = state.get("coder_result", "")
        return f"Tests for code: {code[:100]}"
    
    def reviewer(state: GraphState):
        code = state.get("coder_result", "")
        tests = state.get("tester_result", "")
        # Simple condition: if tests pass, approve
        if "pass" in tests.lower() or "ok" in tests.lower():
            return "approved"
        return "needs_fix"
    
    def should_fix(state: GraphState) -> bool:
        return state.get("reviewer_output") == "needs_fix"
    
    def should_finish(state: GraphState) -> bool:
        return state.get("reviewer_output") == "approved"
    
    graph.add_node(GraphNode(id="planner", type=NodeType.AGENT, func=planner, next_nodes=["coder"]))
    graph.add_node(GraphNode(id="coder", type=NodeType.AGENT, func=coder, next_nodes=["tester"]))
    graph.add_node(GraphNode(id="tester", type=NodeType.TOOL, func=tester, next_nodes=["reviewer"]))
    graph.add_node(GraphNode(id="reviewer", type=NodeType.CONDITION, func=reviewer, next_nodes=["coder", "end"]))
    graph.add_node(GraphNode(id="end", type=NodeType.END))
    
    # Conditional edges
    graph.add_edge("reviewer", "coder", condition=should_fix)
    graph.add_edge("reviewer", "end", condition=should_finish)
    
    graph.set_start("planner")
    return graph
