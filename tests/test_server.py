from fastapi.testclient import TestClient

from specgate.server import create_app


def test_status_endpoint_returns_dashboard_data(tmp_path):
    (tmp_path / "SPEC.md").write_text("- [ ] Build API: Add endpoints.\n", encoding="utf-8")
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["task_counts"]["pending"] == 1


def test_dashboard_endpoint_serves_html(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "<html" in response.text


def test_run_status_endpoint_reports_idle_without_graph(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/run-status")

    assert response.status_code == 200
    assert response.json()["status"] == "idle"
    assert response.json()["current_step"] == "Idle"


def test_run_endpoint_returns_503_without_graph(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/run")

    assert response.status_code == 503


def test_stop_endpoint_reports_stopped(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/stop")

    assert response.status_code == 200
    assert response.json()["status"] == "stopped"


def test_workdir_endpoint_updates_config(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/workdir", json={"work_dir": "./generated"})

    assert response.status_code == 200
    assert response.json()["work_dir"] == "./generated"


def test_operation_mode_endpoint_updates_config(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/operation-mode", json={"operation_mode": "vibe"})

    assert response.status_code == 200
    assert response.json()["operation_mode"] == "vibe"


def test_operation_mode_endpoint_rejects_invalid_mode(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/operation-mode", json={"operation_mode": "chaos"})

    assert response.status_code == 400


def test_agents_endpoint_returns_agent_cards(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/agents")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Planner"


def test_reset_metrics_endpoint_zeros_usage(tmp_path):
    (tmp_path / "SPEC.md").write_text("- [x] Done: Finished.\n", encoding="utf-8")
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/reset-metrics")

    assert response.status_code == 200
    assert response.json()["total_tokens"] == 0
    assert response.json()["total_cost"] == 0.0


def test_reset_activity_endpoint_clears_journal_events(tmp_path):
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)
    journal_path = tmp_path / ".specgate" / "JOURNAL.md"
    journal_path.write_text("## Task: Demo\n- Success: Created file\n", encoding="utf-8")

    response = client.post("/api/reset-activity")

    assert response.status_code == 200
    assert response.json()["events"] == []
    assert journal_path.read_text(encoding="utf-8") == ""


def test_open_workdir_endpoint_uses_service(monkeypatch, tmp_path):
    from specgate import server as server_module

    monkeypatch.setattr(
        server_module.ObservabilityService,
        "open_work_dir",
        lambda self: {"path": str(tmp_path), "status": "opened"},
    )
    app = server_module.create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/open-workdir")

    assert response.status_code == 200
    assert response.json()["status"] == "opened"


def test_open_workspace_path_endpoint_uses_service(monkeypatch, tmp_path):
    from specgate import server as server_module

    monkeypatch.setattr(
        server_module.ObservabilityService,
        "open_workspace_path",
        lambda self, filepath, reveal=False: {"path": filepath, "status": "opened"},
    )
    app = server_module.create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/open-workspace-path", json={"filepath": "demo.py"})

    assert response.status_code == 200
    assert response.json()["status"] == "opened"


def test_select_workdir_endpoint_uses_service(monkeypatch, tmp_path):
    from specgate import server as server_module

    monkeypatch.setattr(
        server_module.ObservabilityService,
        "select_work_dir",
        lambda self: {"work_dir": str(tmp_path), "selected": True},
    )
    app = server_module.create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.post("/api/select-workdir")

    assert response.status_code == 200
    assert response.json()["selected"] is True


def test_help_endpoint_returns_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Help\n\nUse SPEC.md.", encoding="utf-8")
    app = create_app(project_root=str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/help")

    assert response.status_code == 200
    assert "Use SPEC.md." in response.json()["content"]
