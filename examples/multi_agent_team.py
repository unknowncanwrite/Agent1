"""
Example: Multi-Agent Team - Beats CrewAI, MetaGPT
"""
import os
from dotenv import load_dotenv
load_dotenv()

from omni_agent import OmniConfig
from omni_agent.multi_agent import OmniCrew, CrewTask, PREDEFINED_ROLES

config = OmniConfig.from_env()

# Create dev crew: PM, Coder, Reviewer, Tester, Writer
roles = [
    PREDEFINED_ROLES["project_manager"],
    PREDEFINED_ROLES["senior_coder"],
    PREDEFINED_ROLES["code_reviewer"],
    PREDEFINED_ROLES["qa_tester"],
    PREDEFINED_ROLES["tech_writer"],
]

crew = OmniCrew(roles, config=config, verbose=True)

tasks = [
    CrewTask(
        description="Plan a CLI tool that fetches GitHub repo stats (stars, forks, issues) and saves to CSV. Define requirements and architecture.",
        expected_output="Requirements doc and architecture plan",
        assigned_role=PREDEFINED_ROLES["project_manager"]
    ),
    CrewTask(
        description="Implement the GitHub stats CLI tool in Python using requests, typer, csv. Save to ./workspace/github_stats/. Include main.py, api.py, csv_export.py",
        expected_output="Working Python CLI tool with 3 files",
        assigned_role=PREDEFINED_ROLES["senior_coder"],
        dependencies=["Plan a CLI tool"]
    ),
    CrewTask(
        description="Review the implemented GitHub stats CLI for code quality, security, error handling. Suggest improvements.",
        expected_output="Code review report with improvements",
        assigned_role=PREDEFINED_ROLES["code_reviewer"],
        dependencies=["Implement the GitHub"]
    ),
    CrewTask(
        description="Write tests for GitHub stats CLI using pytest. Test API calls (mocked), CSV export, CLI args.",
        expected_output="Test file with at least 5 tests, run them",
        assigned_role=PREDEFINED_ROLES["qa_tester"],
        dependencies=["Implement the GitHub"]
    ),
    CrewTask(
        description="Write README.md documentation for GitHub stats CLI with usage examples, installation, features.",
        expected_output="Comprehensive README.md",
        assigned_role=PREDEFINED_ROLES["tech_writer"],
        dependencies=["Implement the GitHub", "Write tests for GitHub"]
    ),
]

result = crew.kickoff(tasks, parallel=False)

print("\n" + "="*80)
print("FINAL CREW OUTPUT:")
print("="*80)
print(result["final_output"])
print(f"\nElapsed: {result['elapsed_seconds']:.1f}s | Tokens: {result['total_tokens']}")
