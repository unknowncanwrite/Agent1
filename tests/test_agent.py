"""
Tests for OMNI-AGENT
"""
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omni_agent.config import OmniConfig, FREE_MODELS_REGISTRY
from omni_agent.llm.router import ModelRouter
from omni_agent.tools import get_default_tools
from omni_agent.memory import FileMemory, HybridMemory
from omni_agent.multi_agent import PREDEFINED_ROLES, OmniCrew, CrewTask

def test_config():
    config = OmniConfig(api_key="dummy-test-key")
    assert config.default_model == "qwen/qwen3-coder:free"
    assert len(config.fallback_models) > 5
    print("✅ test_config passed")

def test_free_models_registry():
    assert "coder" in FREE_MODELS_REGISTRY
    assert "omni" in FREE_MODELS_REGISTRY
    assert len(FREE_MODELS_REGISTRY["omni"]) >= 10
    print("✅ test_free_models_registry passed")

def test_router():
    config = OmniConfig(api_key="dummy")
    router = ModelRouter(config)
    
    coding_task = "Write Python code to implement quicksort"
    models = router.route(coding_task)
    assert models[0] == "qwen/qwen3-coder:free"
    
    research_task = "Research latest AI papers"
    models = router.route(research_task)
    assert "nemotron" in models[0]
    
    print("✅ test_router passed")

def test_tools():
    registry = get_default_tools()
    tools = registry.list_tools()
    assert len(tools) >= 10
    
    # Test file tools
    from omni_agent.tools.filesystem import WriteFileTool, ReadFileTool
    write_tool = WriteFileTool()
    result = write_tool.execute(path="/tmp/omni_test.txt", content="hello omni")
    assert result.success
    
    read_tool = ReadFileTool()
    result = read_tool.execute(path="/tmp/omni_test.txt")
    assert result.success
    assert "hello omni" in result.output
    
    print("✅ test_tools passed")

def test_memory():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        fm = FileMemory(Path(tmpdir))
        fm.write("learnings", "test_key", "This is a test learning about omni agent")
        results = fm.search("omni agent")
        assert len(results) > 0
        print("✅ test_memory passed")

def test_roles():
    assert "senior_coder" in PREDEFINED_ROLES
    assert "researcher" in PREDEFINED_ROLES
    assert len(PREDEFINED_ROLES) >= 5
    print("✅ test_roles passed")

def test_crew_creation():
    config = OmniConfig(api_key="dummy")
    roles = [PREDEFINED_ROLES["senior_coder"], PREDEFINED_ROLES["researcher"]]
    crew = OmniCrew(roles, config=config)
    assert len(crew.roles) == 2
    print("✅ test_crew_creation passed")

if __name__ == "__main__":
    test_config()
    test_free_models_registry()
    test_router()
    test_tools()
    test_memory()
    test_roles()
    test_crew_creation()
    print("\n🎉 All tests passed! OMNI-AGENT is ready.")
