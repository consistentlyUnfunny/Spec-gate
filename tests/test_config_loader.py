from specgate.state import OperationalMode
from specgate.utils.config_loader import load_config


def test_load_config_returns_defaults_when_yaml_is_missing(tmp_path):
    config = load_config(str(tmp_path))

    assert config.project_name == "default-project"
    assert config.work_dir == "./workspace"
    assert config.knowledge_base == "./docs"
    assert config.operation_mode == OperationalMode.SPEC_GATE
    assert config.agent_settings.executor.model == "qwen2.5-coder"
    assert config.agent_settings.executor.input_cost_per_million_tokens == 0.0
    assert config.agent_settings.executor.output_cost_per_million_tokens == 0.0
    assert config.qa_settings.test_runner == "pytest"
    assert config.dashboard.agents[0].name == "Planner"
    assert config.dashboard.agents[0].node == "planner"


def test_load_config_reads_yaml_settings(tmp_path):
    (tmp_path / "specgate.yaml").write_text(
        """
project_name: Demo
work_dir: ./generated
knowledge_base: ./notes
operation_mode: rapid
agent_settings:
  executor:
    provider: openai
    model: gpt-test
    temperature: 0.2
    input_cost_per_million_tokens: 1.25
    output_cost_per_million_tokens: 5.0
qa_settings:
  test_runner: "pytest tests"
  coverage_threshold: 90
dashboard:
  agents:
    - name: Researcher
      node: research
      role: context gathering
""".strip(),
        encoding="utf-8",
    )

    config = load_config(str(tmp_path))

    assert config.project_name == "Demo"
    assert config.work_dir == "./generated"
    assert config.knowledge_base == "./notes"
    assert config.operation_mode == OperationalMode.RAPID
    assert config.agent_settings.executor.provider == "openai"
    assert config.agent_settings.executor.model == "gpt-test"
    assert config.agent_settings.executor.max_retries == 3
    assert config.agent_settings.executor.input_cost_per_million_tokens == 1.25
    assert config.agent_settings.executor.output_cost_per_million_tokens == 5.0
    assert config.qa_settings.test_runner == "pytest tests"
    assert config.qa_settings.coverage_threshold == 90
    assert config.dashboard.agents[0].name == "Researcher"
    assert config.dashboard.agents[0].node == "research"
    assert config.dashboard.agents[0].role == "context gathering"


def test_openrouter_accepts_base_ur_env_alias(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    (tmp_path / "specgate.yaml").write_text(
        """
agent_settings:
  executor:
    provider: openrouter
    model: openai/gpt-4.1-mini
""".strip(),
        encoding="utf-8",
    )

    config = load_config(str(tmp_path))

    assert config.agent_settings.executor.base_url == "https://openrouter.ai/api/v1"
    assert config.agent_settings.executor.api_key == "test-key"
