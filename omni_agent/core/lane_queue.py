"""
Lane Queue - Prevents race conditions, ensures serial execution per session
Core innovation from OpenClaw
"""
import threading
import queue
from typing import Dict, Callable, Any
from dataclasses import dataclass
import time

@dataclass
class Task:
    id: str
    session_key: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 0

class LaneQueue:
    """
    Serial execution by default, explicit parallel for low-risk tasks
    Each session has its own lane
    """
    def __init__(self):
        self.lanes: Dict[str, queue.Queue] = {}
        self.workers: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        self.global_queue = queue.Queue()
    
    def _ensure_lane(self, session_key: str):
        with self.lock:
            if session_key not in self.lanes:
                self.lanes[session_key] = queue.Queue()
                # Start worker for this lane
                worker = threading.Thread(
                    target=self._lane_worker,
                    args=(session_key,),
                    daemon=True,
                    name=f"lane-{session_key}"
                )
                worker.start()
                self.workers[session_key] = worker
    
    def _lane_worker(self, session_key: str):
        """Worker that processes tasks serially for a lane"""
        lane_queue = self.lanes[session_key]
        while True:
            try:
                task: Task = lane_queue.get(timeout=1)
                try:
                    print(f"🔄 [Lane {session_key}] Executing task {task.id}")
                    task.func(*task.args, **task.kwargs)
                except Exception as e:
                    print(f"❌ [Lane {session_key}] Task {task.id} failed: {e}")
                finally:
                    lane_queue.task_done()
            except queue.Empty:
                # Check if lane should be cleaned up? Keep alive for now
                time.sleep(0.1)
    
    def submit(self, session_key: str, func: Callable, *args, **kwargs) -> str:
        """Submit task to a lane (serial per session)"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        task = Task(id=task_id, session_key=session_key, func=func, args=args, kwargs=kwargs)
        
        self._ensure_lane(session_key)
        self.lanes[session_key].put(task)
        return task_id
    
    def submit_parallel(self, func: Callable, *args, **kwargs) -> str:
        """Submit to global parallel lane (for low-risk, idempotent tasks)"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        def wrapper():
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"Parallel task {task_id} failed: {e}")
        
        # Use global thread pool
        threading.Thread(target=wrapper, daemon=True).start()
        return task_id
    
    def wait_for_lane(self, session_key: str):
        """Wait for all tasks in lane to complete"""
        if session_key in self.lanes:
            self.lanes[session_key].join()

# Global instance
global_lane_queue = LaneQueue()
