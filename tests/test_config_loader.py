from specgate.state import OperationalMode
from specgate.utils.config_loader import load_config


def test_load_config_returns_defaults_when_yaml_is_missing(tmp_path):
    config = load_config(str(tmp_path))

    assert config.project_name == "default-project"
    assert config.operation_mode == OperationalMode.SPEC_GATE
    assert config.agent_settings.executor.model == "qwen2.5-coder"
    assert config.qa_settings.test_runner == "pytest"


def test_load_config_reads_yaml_settings(tmp_path):
    (tmp_path / "specgate.yaml").write_text(
        """
project_name: Demo
operation_mode: rapid
agent_settings:
  executor:
    provider: openai
    model: gpt-test
    temperature: 0.2
qa_settings:
  test_runner: "pytest tests"
  coverage_threshold: 90
""".strip(),
        encoding="utf-8",
    )

    config = load_config(str(tmp_path))

    assert config.project_name == "Demo"
    assert config.operation_mode == OperationalMode.RAPID
    assert config.agent_settings.executor.provider == "openai"
    assert config.agent_settings.executor.model == "gpt-test"
    assert config.agent_settings.executor.max_retries == 3
    assert config.qa_settings.test_runner == "pytest tests"
    assert config.qa_settings.coverage_threshold == 90
