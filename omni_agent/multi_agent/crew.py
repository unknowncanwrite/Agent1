"""
OmniCrew - Multi-agent orchestration that beats CrewAI
- Role-based (like CrewAI)
- Graph-based state (like LangGraph)
- Parallel execution
- Shared memory
- Self-correction
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import OmniConfig
from ..core.agent import OmniAgent
from .roles import AgentRole, PREDEFINED_ROLES

@dataclass
class CrewTask:
    description: str
    expected_output: str
    assigned_role: Optional[AgentRole] = None
    dependencies: List[str] = None  # Task IDs this depends on
    context: Dict = None

class OmniCrew:
    def __init__(
        self,
        roles: List[AgentRole],
        config: Optional[OmniConfig] = None,
        verbose: bool = True
    ):
        self.roles = roles
        self.config = config or OmniConfig.from_env()
        self.verbose = verbose
        self.agents: Dict[str, OmniAgent] = {}
        self.task_results: Dict[str, Any] = {}
        
        # Create an agent per role
        for role in roles:
            agent = OmniAgent(config=self.config)
            self.agents[role.name] = agent
    
    def _execute_single_task(self, task: CrewTask, context_from_deps: str = "") -> Dict:
        role = task.assigned_role
        if not role:
            # Auto-assign based on task analysis
            from ..llm.router import ModelRouter
            router = ModelRouter(self.config)
            profile = router.analyze_task(task.description)
            # Map task type to role
            mapping = {
                "coding": "senior_coder",
                "research": "researcher",
                "reasoning": "project_manager",
                "general": "senior_coder"
            }
            role_key = mapping.get(profile.task_type, "senior_coder")
            role = PREDEFINED_ROLES.get(role_key)
        
        agent = self.agents.get(role.name)
        if not agent:
            agent = OmniAgent(config=self.config)
            self.agents[role.name] = agent
        
        # Build prompt with role + dependencies context
        full_task = f"""
        ROLE: {role.to_prompt()}
        
        TASK: {task.description}
        EXPECTED OUTPUT: {task.expected_output}
        
        CONTEXT FROM PREVIOUS TASKS:
        {context_from_deps}
        
        Execute as {role.name}. Focus on your expertise.
        """
        
        if self.verbose:
            print(f"\n{'='*60}\n🤖 {role.name} working on: {task.description[:80]}...\n{'='*60}")
        
        result = agent.run(full_task, max_iterations=role.max_iterations)
        
        if self.verbose:
            print(f"✅ {role.name} completed: {result['answer'][:200]}...")
        
        return {
            "role": role.name,
            "task": task.description,
            "result": result,
            "output": result["answer"]
        }
    
    def kickoff(self, tasks: List[CrewTask], parallel: bool = False) -> Dict[str, Any]:
        """
        Execute crew tasks - sequential or parallel with dependencies
        This beats CrewAI by handling dependencies and parallel execution intelligently
        """
        print(f"🚀 Crew kickoff: {len(tasks)} tasks, {len(self.roles)} agents, parallel={parallel}")
        start_time = time.time()
        
        # Topological sort for dependencies (simple)
        executed = {}
        pending = tasks.copy()
        
        if parallel:
            # Parallel execution respecting dependencies
            with ThreadPoolExecutor(max_workers=len(self.roles)) as executor:
                while pending:
                    # Find ready tasks (deps satisfied)
                    ready = []
                    remaining = []
                    for t in pending:
                        if not t.dependencies or all(dep in executed for dep in t.dependencies):
                            ready.append(t)
                        else:
                            remaining.append(t)
                    
                    if not ready and remaining:
                        # Circular or missing dep - force execute
                        ready = remaining[:1]
                        remaining = remaining[1:]
                    
                    # Execute ready in parallel
                    futures = {}
                    for task in ready:
                        dep_context = "\n".join([f"{dep}: {executed[dep]['output'][:500]}" for dep in (task.dependencies or []) if dep in executed])
                        future = executor.submit(self._execute_single_task, task, dep_context)
                        futures[future] = task
                    
                    for future in as_completed(futures):
                        task = futures[future]
                        try:
                            result = future.result()
                            task_id = task.description[:30]  # Use desc as ID
                            executed[task_id] = result
                            self.task_results[task_id] = result
                        except Exception as e:
                            print(f"❌ Task failed: {e}")
                    
                    pending = remaining
        else:
            # Sequential
            for task in tasks:
                dep_context = "\n".join([f"{dep}: {executed[dep]['output'][:500]}" for dep in (task.dependencies or []) if dep in executed])
                result = self._execute_single_task(task, dep_context)
                task_id = task.description[:30]
                executed[task_id] = result
                self.task_results[task_id] = result
        
        elapsed = time.time() - start_time
        
        # Final synthesis by manager if exists
        final_output = "\n\n".join([f"## {r['role']}: {r['task'][:50]}\n{r['output']}" for r in executed.values()])
        
        # If we have a manager role, let it synthesize
        manager_roles = [r for r in self.roles if r.role_type.value == "manager"]
        if manager_roles:
            synthesis_agent = self.agents[manager_roles[0].name]
            synthesis = synthesis_agent.chat(f"""
            You are the crew manager. Synthesize these results into final output:
            
            {final_output}
            
            Provide executive summary and final deliverable.
            """)
            final_output = synthesis + "\n\n---\n\n" + final_output
        
        return {
            "crew_results": executed,
            "final_output": final_output,
            "elapsed_seconds": elapsed,
            "tasks_completed": len(executed),
            "total_tokens": sum([r["result"].get("total_tokens", 0) for r in executed.values()])
        }
    
    @classmethod
    def from_role_names(cls, role_names: List[str], config: Optional[OmniConfig] = None) -> "OmniCrew":
        roles = [PREDEFINED_ROLES[name] for name in role_names if name in PREDEFINED_ROLES]
        return cls(roles, config=config)

# Quick factory for common crews
def create_dev_crew(config: Optional[OmniConfig] = None) -> OmniCrew:
    """Full dev team: PM, Coder, Reviewer, Tester, Writer"""
    return OmniCrew.from_role_names(
        ["project_manager", "senior_coder", "code_reviewer", "qa_tester", "tech_writer"],
        config=config
    )

def create_research_crew(config: Optional[OmniConfig] = None) -> OmniCrew:
    """Research team"""
    return OmniCrew.from_role_names(
        ["researcher", "analyst", "tech_writer"],
        config=config
    )
