from specgate import graph as graph_module
from specgate.state import OperationalMode


def state(exit_code=0, retry_counts=None, current_task_id=1):
    return {
        "project_root": ".",
        "spec_path": "SPEC.md",
        "tasks": [],
        "current_task_id": current_task_id,
        "last_spec_hash": "",
        "journal_tail": "",
        "last_test_output": "",
        "exit_code": exit_code,
        "last_execution_ok": True,
        "retry_counts": retry_counts or {},
        "active_context": [],
        "total_tokens": 0,
        "total_cost": 0.0,
        "is_approved": False,
    }


def test_route_after_planner_ends_when_no_task():
    assert graph_module.route_after_planner(state(current_task_id=-1)) == "end"


def test_route_after_executor_skips_tester_in_vibe_mode(monkeypatch):
    monkeypatch.setattr(graph_module.cfg, "operation_mode", OperationalMode.VIBE)

    assert graph_module.route_after_executor(state()) == "planner"


def test_route_after_executor_runs_tester_in_spec_gate_mode(monkeypatch):
    monkeypatch.setattr(graph_module.cfg, "operation_mode", OperationalMode.SPEC_GATE)

    assert graph_module.route_after_executor(state()) == "tester"


def test_route_after_tester_retries_failed_task_until_limit(monkeypatch):
    monkeypatch.setattr(graph_module.cfg, "operation_mode", OperationalMode.SPEC_GATE)
    monkeypatch.setattr(graph_module.exec_cfg, "max_retries", 3)

    assert graph_module.route_after_tester(state(exit_code=1, retry_counts={1: 2})) == "executor"


def test_route_after_tester_halts_when_retry_limit_is_reached(monkeypatch):
    monkeypatch.setattr(graph_module.cfg, "operation_mode", OperationalMode.SPEC_GATE)
    monkeypatch.setattr(graph_module.exec_cfg, "max_retries", 3)

    assert graph_module.route_after_tester(state(exit_code=1, retry_counts={1: 3})) == "end"


def test_route_after_tester_advances_in_rapid_mode(monkeypatch):
    monkeypatch.setattr(graph_module.cfg, "operation_mode", OperationalMode.RAPID)

    assert graph_module.route_after_tester(state(exit_code=1, retry_counts={1: 99})) == "planner"
