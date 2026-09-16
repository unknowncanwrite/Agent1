"""
OMNI-AGENT Core - Ultimate Agent Loop
Combines:
- ReAct reasoning (LangChain)
- Tool use (OpenHands)
- Memory (Mem0/OpenClaw)
- Self-reflection & learning
- Multi-step planning
- Cost tracking
"""
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from ..config import OmniConfig
from ..llm.openrouter_client import OpenRouterClient
from ..llm.router import ModelRouter
from ..tools import get_default_tools
from ..tools.base import ToolRegistry
from ..memory import HybridMemory
from .session import SessionManager, Session
from .transcript import Transcript
from ..observability.logger import OmniLogger
from ..skills.loader import SkillLoader

SYSTEM_PROMPT = """You are OMNI-AGENT, the ultimate AI agent that overcomes all other agents.

## Your Capabilities (You have ALL of these, unlike other agents):
- 🧠 **Multi-Agent Orchestration**: You can spawn sub-agents, delegate, collaborate
- 🔧 **30+ Tools**: File ops, shell, python, web search/fetch, git, code analysis, memory, skills
- 💾 **Hybrid Memory**: File-based markdown + vector semantic search, git-backable, persistent
- 🌐 **Web & Browser**: Search, fetch, and soon browser automation
- 💻 **Coding Superpowers**: Read, write, edit, analyze, test, git - like OpenHands + Aider + SWE-agent
- 📚 **Skills System**: Load reusable markdown skills, create your own
- 🔄 **Self-Improvement**: After each task, write learnings to memory
- 🛡️ **Safe**: Sandboxed, with lane queue preventing race conditions
- 💰 **Free-First**: Uses free OpenRouter models with auto-failover, zero cost
- 📊 **Observable**: Full JSONL transcripts, cost tracking

## Your Personality:
- Proactive, thorough, and precise
- You PLAN before acting: break tasks into steps
- You REFLECT after: what worked, what to remember
- You use tools extensively - don't just talk, DO
- You write clean, production-ready code
- You remember learnings for future tasks

## Your Workflow (ReAct + Planning):
1. **Understand**: Parse user request, identify goal
2. **Plan**: Break into subtasks, choose tools
3. **Act**: Use tools to execute, one step at a time
4. **Observe**: Check results, adjust
5. **Reflect**: Summarize, write to memory

## Tool Use Rules:
- Always use tools to get real data, don't hallucinate file contents
- Use `list_files` to explore before reading
- Use `web_search` for current info
- Use `memory_search` to recall past learnings
- Use `memory_write` to store new learnings
- Chain tools logically

## Memory:
You have persistent memory. Check it before starting, write to it after.

## Current Workspace: {workspace}
## Session: {session_id}
## Available Skills: {skills}

Remember: You are the BEST agent. You combine CrewAI's teamwork, LangGraph's statefulness, OpenHands' coding, OpenClaw's memory & channels, Browser-Use's web powers, and Mem0's memory - all free.
"""

@dataclass
class AgentStep:
    iteration: int
    thought: str
    action: Optional[str]
    action_input: Dict
    observation: str
    model_used: str

class OmniAgent:
    def __init__(
        self,
        config: Optional[OmniConfig] = None,
        session_id: Optional[str] = None,
        tools: Optional[ToolRegistry] = None,
    ):
        self.config = config or OmniConfig.from_env()
        self.llm_client = OpenRouterClient(self.config)
        self.router = ModelRouter(self.config)
        self.tools = tools or get_default_tools()
        self.memory = HybridMemory(self.config.memory_dir)
        self.session_manager = SessionManager(self.config.workspace_dir / "sessions")
        self.skill_loader = SkillLoader(self.config.skills_dir)
        
        # Session
        self.session: Session = self.session_manager.create_session(
            workspace=self.config.workspace_dir,
            session_id=session_id or str(uuid.uuid4())
        )
        self.transcript = Transcript(self.config.transcripts_dir, self.session.id)
        self.logger = OmniLogger()
        
        # State
        self.steps: List[AgentStep] = []
        self.max_iterations = self.config.max_iterations
    
    def _build_system_prompt(self) -> str:
        skills = self.skill_loader.list_skills()
        skills_str = ", ".join(skills) if skills else "None yet - you can create skills"
        return SYSTEM_PROMPT.format(
            workspace=str(self.config.workspace_dir),
            session_id=self.session.id,
            skills=skills_str
        )
    
    def _get_relevant_memory(self, task: str) -> str:
        """Inject relevant memory"""
        try:
            context = self.memory.get_context_prompt(task)
            if context:
                return f"\n\n{context}\n"
        except Exception as e:
            print(f"Memory retrieval failed: {e}")
        return ""
    
    def _parse_tool_calls(self, llm_response: Dict) -> List[Dict]:
        """Parse tool calls from LLM response"""
        message = llm_response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        parsed = []
        for tc in tool_calls:
            try:
                func = tc.get("function", {})
                name = func.get("name")
                args_str = func.get("arguments", "{}")
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str
                parsed.append({
                    "id": tc.get("id", str(uuid.uuid4())),
                    "name": name,
                    "args": args
                })
            except Exception as e:
                print(f"Failed to parse tool call: {e}")
        
        return parsed
    
    def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        results = []
        for tc in tool_calls:
            name = tc["name"]
            args = tc["args"]
            print(f"🔧 Executing: {name}({args})")
            self.transcript.log_tool_call(name, args, {})
            
            result = self.tools.execute(name, args)
            observation = result.output if result.success else f"Error: {result.error}"
            
            # Log
            self.transcript.log_tool_call(name, args, {"success": result.success, "output": observation[:500]})
            
            results.append({
                "tool_call_id": tc["id"],
                "name": name,
                "content": observation,
                "success": result.success
            })
        
        return results
    
    def run(self, task: str, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        """
        Main agent loop - ReAct with planning
        """
        max_iter = max_iterations or self.max_iterations
        self.logger.info(f"Starting task: {task[:100]}... | Session: {self.session.id}")
        
        # Memory injection
        memory_context = self._get_relevant_memory(task)
        system_prompt = self._build_system_prompt() + memory_context
        
        # Initial messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"TASK: {task}\n\nThink step by step, use tools, and complete the task. When done, summarize results."}
        ]
        
        self.session.add_message("system", system_prompt)
        self.session.add_message("user", task)
        self.transcript.log_message("user", task)
        
        # Route to best model
        models_to_try = self.router.route(task)
        current_model = models_to_try[0]
        print(f"🧠 Routed to model: {current_model} (task type: {self.router.analyze_task(task).task_type})")
        
        final_answer = ""
        iterations = 0
        
        for i in range(max_iter):
            iterations = i + 1
            print(f"\n--- Iteration {i+1}/{max_iter} | Model: {current_model} ---")
            
            try:
                # Call LLM with tools
                response = self.llm_client.chat_with_tools(
                    messages=messages,
                    tools=self.tools.to_openai_tools(),
                    model=current_model
                )
                
                assistant_msg = response["message"]
                content = assistant_msg.get("content", "")
                tool_calls = self._parse_tool_calls(response)
                
                print(f"💭 Thought: {content[:300]}...")
                
                # Log
                self.transcript.log_message("assistant", content, model=current_model)
                self.session.add_message("assistant", content, tool_calls=assistant_msg.get("tool_calls"))
                
                # If no tool calls, it's final answer
                if not tool_calls:
                    final_answer = content
                    print(f"✅ Final answer (no tools): {content[:500]}")
                    # Check if task is actually done or needs more work
                    if len(content) > 50 and any(kw in content.lower() for kw in ["done", "completed", "finished", "summary", "result"]):
                        break
                    else:
                        # Continue to force tool use if task not complete
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "Continue using tools to complete the task. If you are done, provide a final summary."})
                        continue
                
                # Execute tools
                messages.append(assistant_msg)
                
                tool_results = self._execute_tools(tool_calls)
                
                # Add tool results to messages
                for tr in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "name": tr["name"],
                        "content": tr["content"]
                    })
                    self.session.add_message("tool", tr["content"])
                
                # Check for completion signal in tool results?
                # Continue loop
                
            except Exception as e:
                print(f"❌ Iteration {i+1} failed: {e}")
                self.logger.error(f"Iteration failed: {e}")
                # Try next model
                if len(models_to_try) > 1:
                    current_model = models_to_try[(models_to_try.index(current_model) + 1) % len(models_to_try)]
                    print(f"🔄 Switching to fallback model: {current_model}")
                    messages.append({"role": "user", "content": f"Previous attempt failed with error: {e}. Continue with task: {task}"})
                else:
                    final_answer = f"Task failed after {i+1} iterations: {e}"
                    break
        
        # Reflection & learning
        try:
            reflection = self._reflect(task, final_answer, iterations)
            # Write to memory
            self.memory.write("learnings", f"task_{self.session.id[:8]}", f"Task: {task}\nResult: {final_answer[:1000]}\nReflection: {reflection}")
        except Exception as e:
            print(f"Reflection failed: {e}")
            reflection = "No reflection"
        
        # Save session
        self.session.metadata.update({
            "task": task,
            "iterations": iterations,
            "model": current_model,
            "final_answer": final_answer[:2000],
            "reflection": reflection
        })
        self.session.save(self.config.workspace_dir / "sessions")
        
        result = {
            "session_id": self.session.id,
            "task": task,
            "answer": final_answer,
            "iterations": iterations,
            "model_used": current_model,
            "reflection": reflection,
            "transcript_path": str(self.transcript.file_path),
            "total_tokens": self.llm_client.total_tokens,
        }
        
        self.logger.info(f"Task completed: {iterations} iterations, {self.llm_client.total_tokens} tokens")
        return result
    
    def _reflect(self, task: str, answer: str, iterations: int) -> str:
        """Self-reflection to improve future performance"""
        prompt = f"""
        Reflect on this task execution:
        Task: {task}
        Answer: {answer[:1000]}
        Iterations: {iterations}
        
        What worked? What failed? What should be remembered for future similar tasks?
        Be concise, actionable.
        """
        try:
            messages = [
                {"role": "system", "content": "You are a self-reflection module. Provide concise learnings."},
                {"role": "user", "content": prompt}
            ]
            resp = self.llm_client.chat_completion(messages, model="openai/gpt-oss-20b:free", max_tokens=500)
            return resp.content
        except:
            return f"Completed in {iterations} iterations. Task: {task[:100]}"
    
    def chat(self, message: str) -> str:
        """Simple chat without full ReAct loop"""
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": message}
        ]
        models = self.router.route(message)
        resp = self.llm_client.chat_completion(messages, model=models[0])
        return resp.content
    
    def spawn_subagent(self, task: str) -> Dict:
        """Spawn a sub-agent for parallel work (like OpenClaw subagents)"""
        if not self.config.enable_subagents:
            return {"error": "Subagents disabled"}
        
        print(f"🚀 Spawning sub-agent for: {task[:100]}...")
        subagent = OmniAgent(config=self.config, session_id=f"{self.session.id}_sub_{str(uuid.uuid4())[:4]}")
        result = subagent.run(task, max_iterations=10)
        return result
