from specgate.observability import ObservabilityService


def test_observability_service_reads_status_from_durable_files(tmp_path):
    (tmp_path / "specgate.yaml").write_text(
        """
project_name: Demo
operation_mode: rapid
agent_settings:
  executor:
    budget_limit_usd: 2.0
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "SPEC.md").write_text(
        """
# Spec

- [x] Done: Finished task.
- [ ] Next: Pending task.
""".strip(),
        encoding="utf-8",
    )

    service = ObservabilityService(str(tmp_path))
    service.io.progress_path.write_text(
        "# Progress\n\nTotal tokens: 250\nTotal cost: $0.5000\n",
        encoding="utf-8",
    )

    status = service.status()

    assert status["project_name"] == "Demo"
    assert status["work_dir"] == "./workspace"
    assert status["operation_mode"] == "rapid"
    assert status["active_task"]["name"] == "Next"
    assert status["task_counts"]["completed"] == 1
    assert status["task_counts"]["pending"] == 1
    assert status["total_tokens"] == 250
    assert status["total_cost"] == 0.5
    assert status["budget_used_ratio"] == 0.25


def test_config_snapshot_excludes_api_key(tmp_path):
    (tmp_path / "specgate.yaml").write_text(
        """
agent_settings:
  executor:
    provider: openai
    api_key: secret
""".strip(),
        encoding="utf-8",
    )

    service = ObservabilityService(str(tmp_path))

    assert "api_key" not in service.config_snapshot()["executor"]


def test_graph_state_is_unavailable_without_graph(tmp_path):
    service = ObservabilityService(str(tmp_path))

    graph_state = service.graph_state()

    assert graph_state["available"] is False
    assert graph_state["next"] == []


def test_agents_are_loaded_from_dashboard_config(tmp_path):
    (tmp_path / "specgate.yaml").write_text(
        """
dashboard:
  agents:
    - name: Researcher
      node: research
      role: context gathering
""".strip(),
        encoding="utf-8",
    )
    service = ObservabilityService(str(tmp_path))

    agents = service.agents()

    assert agents == [
        {
            "name": "Researcher",
            "node": "research",
            "role": "context gathering",
            "status": "idle",
        }
    ]


def test_update_work_dir_persists_to_yaml(tmp_path):
    service = ObservabilityService(str(tmp_path))

    snapshot = service.update_work_dir("./generated")

    assert snapshot["work_dir"] == "./generated"
    assert "work_dir: ./generated" in (tmp_path / "specgate.yaml").read_text(encoding="utf-8")
    assert (tmp_path / "generated").exists()


def test_update_operation_mode_persists_to_yaml(tmp_path):
    service = ObservabilityService(str(tmp_path))

    snapshot = service.update_operation_mode("rapid")

    assert snapshot["operation_mode"] == "rapid"
    assert "operation_mode: rapid" in (tmp_path / "specgate.yaml").read_text(encoding="utf-8")


def test_update_operation_mode_rejects_invalid_mode(tmp_path):
    service = ObservabilityService(str(tmp_path))

    try:
        service.update_operation_mode("chaos")
    except ValueError as exc:
        assert "operation_mode must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_select_work_dir_persists_selected_path(monkeypatch, tmp_path):
    selected = tmp_path / "chosen"
    service = ObservabilityService(str(tmp_path))
    monkeypatch.setattr(service, "_ask_directory", lambda: str(selected))

    snapshot = service.select_work_dir()

    assert snapshot["selected"] is True
    assert snapshot["work_dir"] == "chosen"


def test_activity_events_include_workspace_file_metadata(tmp_path):
    service = ObservabilityService(str(tmp_path))
    service.io.journal_path.write_text(
        "## Task: Demo\n- Executed `create_file`: Success: Created specgate_demo.py\n",
        encoding="utf-8",
    )

    events = service.journal()["events"]

    assert events[-1]["type"] == "success"
    assert events[-1]["file"] == "specgate_demo.py"


def test_journal_includes_changed_file_artifacts(tmp_path):
    service = ObservabilityService(str(tmp_path))
    service.io.journal_path.write_text(
        "\n".join(
            [
                "## Task: Demo",
                "- Executed `replace_content_block`: Success: Modified specgate_demo.py",
                "- Executed `create_file`: Success: Created test_specgate_demo.py",
            ]
        ),
        encoding="utf-8",
    )

    artifacts = service.journal()["artifacts"]

    assert artifacts == [
        {"file": "specgate_demo.py", "action": "Modified"},
        {"file": "test_specgate_demo.py", "action": "Created"},
    ]


def test_activity_events_surface_changed_files_at_end(tmp_path):
    service = ObservabilityService(str(tmp_path))
    service.io.journal_path.write_text(
        "\n".join(
            [
                "## Task: Demo",
                "- Executed `replace_content_block`: Success: Modified specgate_demo.py",
                "## Task: Runner",
                "- Run completed.",
            ]
        ),
        encoding="utf-8",
    )

    events = service.journal()["events"]

    assert events[-1] == {
        "type": "success",
        "title": "Files changed",
        "detail": "Modified specgate_demo.py",
        "file": "specgate_demo.py",
    }


def test_open_workspace_path_rejects_escape(tmp_path):
    service = ObservabilityService(str(tmp_path))

    try:
        service.open_workspace_path("../escape.py")
    except ValueError as exc:
        assert "escapes configured work_dir" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_open_workspace_path_reveals_file_parent(monkeypatch, tmp_path):
    service = ObservabilityService(str(tmp_path))
    target = tmp_path / "workspace" / "demo.py"
    target.parent.mkdir()
    target.write_text("value = 1\n", encoding="utf-8")
    opened = []
    monkeypatch.setattr(service, "_reveal_path", lambda path: opened.append(path))

    result = service.open_workspace_path("demo.py", reveal=True)

    assert result["status"] == "opened"
    assert result["path"] == str(target.parent)
    assert opened == [target]
