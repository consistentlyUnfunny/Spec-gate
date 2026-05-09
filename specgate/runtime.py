from .state import SpecGateState


THREAD_CONFIG = {"configurable": {"thread_id": "project-specgate-dev"}}


def create_initial_state() -> SpecGateState:
    return SpecGateState(
        project_root=".",
        spec_path="SPEC.md",
        tasks=[],
        current_task_id=-1,
        last_spec_hash="",
        journal_tail="",
        last_test_output="",
        exit_code=0,
        last_execution_ok=False,
        retry_counts={},
        active_context=[],
        total_tokens=0,
        total_cost=0.0,
        is_approved=False,
    )
