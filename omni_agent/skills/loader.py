"""
Skill Loader - Markdown-based skills that extend agent
Hot-reloadable, agent can create its own skills
"""
from pathlib import Path
from typing import List, Dict, Optional
import yaml

class Skill:
    def __init__(self, name: str, content: str, path: Path):
        self.name = name
        self.content = content
        self.path = path
        self.metadata = self._parse_metadata()
    
    def _parse_metadata(self) -> Dict:
        # Try to parse YAML frontmatter
        if self.content.startswith("---"):
            try:
                end = self.content.find("---", 3)
                if end != -1:
                    frontmatter = self.content[3:end]
                    return yaml.safe_load(frontmatter) or {}
            except:
                pass
        return {}
    
    def get_prompt(self) -> str:
        # Remove frontmatter for prompt
        if self.content.startswith("---"):
            end = self.content.find("---", 3)
            if end != -1:
                return self.content[end+3:].strip()
        return self.content

class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills: Dict[str, Skill] = {}
        self.load_all()
    
    def load_all(self):
        self.skills.clear()
        for file_path in self.skills_dir.rglob("*.md"):
            try:
                content = file_path.read_text()
                name = file_path.stem
                self.skills[name] = Skill(name, content, file_path)
            except Exception as e:
                print(f"Failed to load skill {file_path}: {e}")
        
        # Also check builtin
        builtin_dir = Path(__file__).parent / "examples"
        if builtin_dir.exists():
            for file_path in builtin_dir.glob("*.md"):
                try:
                    content = file_path.read_text()
                    name = file_path.stem
                    if name not in self.skills:
                        self.skills[name] = Skill(name, content, file_path)
                except:
                    continue
    
    def get_skill(self, name: str) -> Optional[Skill]:
        # Hot reload check
        if name not in self.skills:
            self.load_all()
        return self.skills.get(name)
    
    def list_skills(self) -> List[str]:
        return list(self.skills.keys())
    
    def create_skill(self, name: str, content: str, metadata: Dict = None) -> Path:
        """Agent can create its own skills - self-improvement"""
        file_path = self.skills_dir / f"{name}.md"
        
        full_content = ""
        if metadata:
            import yaml
            full_content += "---\n"
            full_content += yaml.dump(metadata)
            full_content += "---\n\n"
        full_content += content
        
        file_path.write_text(full_content)
        self.skills[name] = Skill(name, full_content, file_path)
        return file_path
    
    def get_skills_prompt(self, skill_names: List[str] = None) -> str:
        """Get combined prompt for selected skills"""
        if not skill_names:
            skill_names = self.list_skills()
        
        prompt = ""
        for name in skill_names:
            skill = self.get_skill(name)
            if skill:
                prompt += f"\n## Skill: {name}\n{skill.get_prompt()}\n\n"
        
        return prompt
