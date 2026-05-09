import os
from dotenv import load_dotenv
import yaml
from pathlib import Path
from pydantic import BaseModel, Field, model_validator

from specgate.state import OperationalMode

load_dotenv()

class DefaultAgentConfig(BaseModel):
    provider: str = "ollama"
    model: str = "qwen2.5-coder"
    temperature: float = 0.1
    max_retries: int = 3
    budget_limit_usd: float = 5.0
    input_cost_per_million_tokens: float = 0.0
    output_cost_per_million_tokens: float = 0.0
    base_url: str | None = None
    api_key: str | None = None

    @model_validator(mode = "after") # run this after base model is validated
    def resolve_credentials(self) -> "DefaultAgentConfig":
        """Fetch credentials based on provider name"""
        prefix = self.provider.upper()

        if not self.base_url:
            self.base_url = os.environ.get(f"{prefix}_BASE_URL")
            if not self.base_url and prefix == "OPENROUTER":
                self.base_url = os.environ.get("OPENROUTER_BASE_URL")

        if not self.api_key:
            self.api_key = os.environ.get(f"{prefix}_API_KEY")
        
        return self
    
class AgentSettings(BaseModel):
    planner: DefaultAgentConfig = Field(default_factory=DefaultAgentConfig)
    executor: DefaultAgentConfig = Field(default_factory=DefaultAgentConfig)
    reviewer: DefaultAgentConfig = Field(default_factory=DefaultAgentConfig)

class QASettings(BaseModel):
    test_runner: str = "pytest"
    coverage_threshold: int = 80

class DashboardAgent(BaseModel):
    name: str
    node: str
    role: str = "agent"

class DashboardSettings(BaseModel):
    agents: list[DashboardAgent] = Field(default_factory=lambda: [
        DashboardAgent(name="Planner", node="planner", role="planning"),
        DashboardAgent(name="Executor", node="executor", role="implementation"),
        DashboardAgent(name="Tester", node="tester", role="quality gate"),
        DashboardAgent(name="Librarian", node="librarian", role="summarization"),
    ])

class Config(BaseModel):
    project_name: str = "default-project"
    work_dir: str = "./workspace"
    knowledge_base: str = "./docs"
    operation_mode: OperationalMode = OperationalMode.SPEC_GATE
    agent_settings: AgentSettings = Field(default_factory=AgentSettings)
    qa_settings: QASettings = Field(default_factory=QASettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)

def load_config(project_root: str = ".") -> Config:
    yaml_path = Path(project_root) / "specgate.yaml"
    
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
            return Config(**yaml_data)

    return Config()

