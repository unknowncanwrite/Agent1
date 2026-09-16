"""
Sub-agent system - Parallel workers that don't block main agent
Like OpenClaw's sub-agents
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

@dataclass
class SubAgentTask:
    id: str
    task: str
    parent_session: str
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None

class SubAgentManager:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.tasks: Dict[str, SubAgentTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
    
    def spawn(self, task: str, parent_session: str) -> str:
        task_id = f"sub_{str(uuid.uuid4())[:8]}"
        sub_task = SubAgentTask(id=task_id, task=task, parent_session=parent_session)
        
        with self.lock:
            self.tasks[task_id] = sub_task
        
        # Submit to executor
        self.executor.submit(self._run_subagent, task_id)
        
        return task_id
    
    def _run_subagent(self, task_id: str):
        from ..config import OmniConfig
        from ..core.agent import OmniAgent
        
        with self.lock:
            task = self.tasks[task_id]
            task.status = "running"
        
        try:
            # Create isolated agent
            config = OmniConfig.from_env()
            agent = OmniAgent(config=config, session_id=task_id)
            result = agent.run(task.task, max_iterations=10)
            
            with self.lock:
                self.tasks[task_id].status = "completed"
                self.tasks[task_id].result = result
                
        except Exception as e:
            with self.lock:
                self.tasks[task_id].status = "failed"
                self.tasks[task_id].result = {"error": str(e)}
    
    def get_status(self, task_id: str) -> Optional[SubAgentTask]:
        return self.tasks.get(task_id)
    
    def list_tasks(self, parent_session: str = None) -> List[SubAgentTask]:
        if parent_session:
            return [t for t in self.tasks.values() if t.parent_session == parent_session]
        return list(self.tasks.values())
    
    def wait_for(self, task_id: str, timeout: int = 60) -> Optional[Dict]:
        import time
        start = time.time()
        while time.time() - start < timeout:
            task = self.get_status(task_id)
            if task and task.status in ["completed", "failed"]:
                return task.result
            time.sleep(1)
        return None

# Global manager
global_subagent_manager = SubAgentManager()
