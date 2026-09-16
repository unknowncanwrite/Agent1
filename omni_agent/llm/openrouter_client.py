"""
OpenRouter Client - Free-first LLM gateway
Handles failover, retries, rate limits, cost tracking
"""
import os
import time
import json
import httpx
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
from ..config import OmniConfig, FREE_MODELS_REGISTRY

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    raw: Dict[str, Any]

class OpenRouterClient:
    def __init__(self, config: OmniConfig):
        self.config = config
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.client = httpx.Client(timeout=120.0)
        self.total_tokens = 0
        self.total_cost = 0.0  # Free = 0
        
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/unknowncanwrite/Agent1",
            "X-Title": "OMNI-AGENT Ultimate",
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        retries: int = 3,
    ) -> LLMResponse:
        """
        Chat completion with automatic free model failover
        """
        models_to_try = []
        if model:
            models_to_try.append(model)
        models_to_try.extend(self.config.fallback_models)
        # Deduplicate
        seen = set()
        deduped = []
        for m in models_to_try:
            if m not in seen:
                deduped.append(m)
                seen.add(m)
        models_to_try = deduped
        
        last_error = None
        for attempt_model in models_to_try:
            for retry in range(retries):
                try:
                    payload = {
                        "model": attempt_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    if tools:
                        payload["tools"] = tools
                        payload["tool_choice"] = tool_choice
                    
                    resp = self.client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                    )
                    
                    if resp.status_code == 429:
                        # Rate limit - wait and try next model
                        wait = 2 ** retry
                        print(f"⚠️ Rate limited on {attempt_model}, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    
                    if resp.status_code != 200:
                        err = resp.text[:500]
                        print(f"⚠️ Model {attempt_model} failed {resp.status_code}: {err}")
                        last_error = f"{attempt_model}: {err}"
                        break  # Try next model
                    
                    data = resp.json()
                    choice = data["choices"][0]
                    usage = data.get("usage", {})
                    
                    self.total_tokens += usage.get("total_tokens", 0)
                    
                    content = ""
                    if choice["message"].get("content"):
                        content = choice["message"]["content"]
                    # Handle tool calls as content if needed
                    if choice["message"].get("tool_calls"):
                        # Return raw tool calls in content for parsing
                        content += "\n" + json.dumps(choice["message"]["tool_calls"])
                    
                    return LLMResponse(
                        content=content,
                        model=data.get("model", attempt_model),
                        usage=usage,
                        finish_reason=choice.get("finish_reason", "stop"),
                        raw=data,
                    )
                    
                except Exception as e:
                    last_error = str(e)
                    print(f"⚠️ Error with {attempt_model}: {e}, retry {retry+1}/{retries}")
                    time.sleep(1)
                    continue
            
            print(f"🔄 Trying next model after {attempt_model} failed...")
        
        raise RuntimeError(f"All models failed. Last error: {last_error}")
    
    def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full tool-calling support with fallback"""
        models_to_try = [model] + self.config.fallback_models if model else self.config.fallback_models
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
        
        for m in models_to_try:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }
                resp = self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code == 429:
                    time.sleep(2)
                    continue
                if resp.status_code != 200:
                    print(f"⚠️ {m} failed: {resp.status_code} {resp.text[:300]}")
                    continue
                data = resp.json()
                msg = data["choices"][0]["message"]
                usage = data.get("usage", {})
                self.total_tokens += usage.get("total_tokens", 0)
                return {
                    "message": msg,
                    "model": m,
                    "usage": usage,
                    "raw": data,
                }
            except Exception as e:
                print(f"⚠️ {m} exception: {e}")
                continue
        
        raise RuntimeError("All models failed for tool calling")
    
    def list_free_models(self) -> List[Dict]:
        """Fetch live free models from OpenRouter"""
        try:
            resp = self.client.get(
                f"{self.base_url}/models",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                free = [m for m in data.get("data", []) if ":free" in m.get("id", "") or m.get("pricing", {}).get("prompt") == "0"]
                return free
        except Exception as e:
            print(f"Failed to list models: {e}")
        # Return registry as fallback
        return [{"id": mid} for mid in FREE_MODELS_REGISTRY["omni"]]

# Singleton for easy use
_client_instance = None

def get_client(config: Optional[OmniConfig] = None) -> OpenRouterClient:
    global _client_instance
    if _client_instance is None:
        if config is None:
            from ..config import OmniConfig
            try:
                config = OmniConfig.from_env()
            except:
                # For testing without key, use dummy
                import os
                config = OmniConfig(api_key=os.getenv("OPENROUTER_API_KEY", "dummy"))
        _client_instance = OpenRouterClient(config)
    return _client_instance
