from specgate.state import TaskStatus
from specgate.utils.io_manager import IOManager


def test_parse_tasks_from_spec_reads_checkbox_tasks(tmp_path):
    (tmp_path / "SPEC.md").write_text(
        """
# Project Specification

- [ ] Build core graph: Create LangGraph flow.
- [x] Add governance: Load specgate.yaml.
""".strip(),
        encoding="utf-8",
    )

    io = IOManager(str(tmp_path))
    tasks = io.parse_tasks_from_spec()

    assert len(tasks) == 2
    assert tasks[0].id == 1
    assert tasks[0].name == "Build core graph"
    assert tasks[0].status == TaskStatus.PENDING
    assert tasks[1].status == TaskStatus.COMPLETED


def test_mark_task_completed_updates_spec_checkbox(tmp_path):
    spec_path = tmp_path / "SPEC.md"
    spec_path.write_text(
        """
# Project Specification

- [ ] First task: Do one thing.
- [ ] Second task: Do another thing.
""".strip(),
        encoding="utf-8",
    )

    io = IOManager(str(tmp_path))

    assert io.mark_task_completed(2) is True
    assert "- [ ] First task: Do one thing." in spec_path.read_text(encoding="utf-8")
    assert "- [x] Second task: Do another thing." in spec_path.read_text(encoding="utf-8")


def test_sync_progress_writes_task_snapshot(tmp_path):
    io = IOManager(str(tmp_path))
    io.spec_path.write_text("- [x] Done: Complete setup.\n", encoding="utf-8")
    tasks = io.parse_tasks_from_spec()

    io.sync_progress(tasks, total_tokens=123, total_cost=0.45)

    progress = io.progress_path.read_text(encoding="utf-8")
    assert "Total tokens: 123" in progress
    assert "Total cost: $0.4500" in progress
    assert "- [x] Task 1: Done - completed" in progress


def test_snapshot_state_skips_when_not_inside_git_repo(tmp_path):
    io = IOManager(str(tmp_path))

    result = io.snapshot_state("Spec-Gate state: test")

    assert result.startswith("Git snapshot skipped:")
