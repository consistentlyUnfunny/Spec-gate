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


def test_reset_metrics_preserves_tasks_and_zeros_usage(tmp_path):
    io = IOManager(str(tmp_path))
    io.spec_path.write_text("- [x] Done: Complete setup.\n", encoding="utf-8")
    io.sync_progress(io.parse_tasks_from_spec(), total_tokens=123, total_cost=0.45)

    io.reset_metrics()

    progress = io.progress_path.read_text(encoding="utf-8")
    assert "Total tokens: 0" in progress
    assert "Total cost: $0.0000" in progress
    assert "- [x] Task 1: Done - completed" in progress


def test_reset_activity_clears_journal_and_summary(tmp_path):
    io = IOManager(str(tmp_path))
    io.journal_path.write_text("## Task: Demo\n- Ran once\n", encoding="utf-8")
    io.summary_path.write_text("old summary", encoding="utf-8")

    io.reset_activity()

    assert io.journal_path.read_text(encoding="utf-8") == ""
    assert io.summary_path.read_text(encoding="utf-8") == ""


def test_append_activity_groups_repeated_events_by_title(tmp_path):
    io = IOManager(str(tmp_path))

    io.append_activity("Runner", "Run requested.")
    io.append_activity("Runner", "Loading checkpoint.")

    journal = io.journal_path.read_text(encoding="utf-8")
    assert journal.count("## Task: Runner") == 1
    assert "- Run requested." in journal
    assert "- Loading checkpoint." in journal


def test_snapshot_state_skips_when_not_inside_git_repo(tmp_path):
    io = IOManager(str(tmp_path))

    result = io.snapshot_state("Spec-Gate state: test")

    assert result.startswith("Git snapshot skipped:")


def test_compact_journal_writes_summary_and_retains_tail(tmp_path):
    io = IOManager(str(tmp_path))
    io.journal_path.write_text("a" * 120, encoding="utf-8")

    compacted = io.compact_journal(max_chars=100, tail_chars=20)

    assert compacted is True
    assert "Compacted journal length: 120 characters" in io.summary_path.read_text(encoding="utf-8")
    assert "Previous entries were compacted" in io.journal_path.read_text(encoding="utf-8")
    assert "a" * 20 in io.journal_path.read_text(encoding="utf-8")


def test_compact_journal_skips_small_journal(tmp_path):
    io = IOManager(str(tmp_path))
    io.journal_path.write_text("short", encoding="utf-8")

    assert io.compact_journal(max_chars=100, tail_chars=20) is False
