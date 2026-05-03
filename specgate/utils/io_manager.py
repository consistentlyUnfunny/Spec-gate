import hashlib
import re
import subprocess
from pathlib import Path
from datetime import datetime
from ..state import Task, TaskStatus


class IOManager:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.spec_path = self.root / "SPEC.md"
        self.specgate_dir = self.root / ".specgate"
        self.journal_path = self.specgate_dir / "JOURNAL.md"
        self.progress_path = self.specgate_dir / "PROGRESS.md"

        self._initialize_files()

    def _initialize_files(self):
        """
        Creates markdown files in their respective diorectory
        """
        self.specgate_dir.mkdir(parents = True, exist_ok = True)

        for path in [self.spec_path, self.journal_path, self.progress_path]:
            if not path.exists():
                path.touch()

        # Seed SPEC.md (Optional)
        if self.spec_path.stat().st_size == 0:
            self.spec_path.write_text("#Project Specification\n\n## Tasks\n", encoding = "utf-8")

    def get_spec_hash(self) -> str:
        """
        Calculates SHA-256 hash of SPEC.md to detech external edits (especially while running tasks)
        """
        if not self.spec_path.exists():
            return ""
        return hashlib.sha256(self.spec_path.read_bytes()).hexdigest() # hash the byte using sha256 then convert to hex string
    
    def parse_tasks_from_spec(self) -> list[Task]:
        """
        Extracts and return task from SPEC.md using Regex, save tokens
        """
        if not self.spec_path.exists():
            return []
        content = self.spec_path.read_text(encoding = "utf-8")
        tasks = []

        # Matches "- [] Task Name: Description"
        pattern = re.compile(r"^\s*-\s+\[( |x|X)\]\s+([^:]+):\s*(.*)", re.MULTILINE)

        for index, match in enumerate(pattern.finditer(content)):
            is_checked = match.group(1).lower() == 'x'

            tasks.append(
                Task(
                    id=index + 1,
                    name = match.group(2).strip(),
                    description = match.group(3).strip(),
                    status = TaskStatus.COMPLETED if is_checked else TaskStatus.PENDING
                )
            )

        return tasks

    def mark_task_completed(self, task_id: int) -> bool:
        """
        Marks the task checkbox in SPEC.md as completed.
        """
        if not self.spec_path.exists():
            return False

        content = self.spec_path.read_text(encoding="utf-8")
        pattern = re.compile(r"^(\s*-\s+\[)( |x|X)(\]\s+[^:]+:\s*.*)$", re.MULTILINE)
        seen = 0

        def replace_match(match: re.Match[str]) -> str:
            nonlocal seen
            seen += 1
            if seen == task_id:
                return f"{match.group(1)}x{match.group(3)}"
            return match.group(0)

        updated = pattern.sub(replace_match, content)
        if seen < task_id or updated == content:
            return False

        self.spec_path.write_text(updated, encoding="utf-8")
        return True

    def sync_progress(self, tasks: list[Task], total_tokens: int = 0, total_cost: float = 0.0) -> None:
        """
        Writes a human-readable task snapshot for recovery and review.
        """
        lines = [
            "# Progress",
            "",
            f"Last updated: {datetime.now().isoformat(timespec='seconds')}",
            f"Total tokens: {total_tokens}",
            f"Total cost: ${total_cost:.4f}",
            "",
            "## Tasks",
            "",
        ]

        for task in tasks:
            checkbox = "x" if task.status == TaskStatus.COMPLETED else " "
            lines.append(f"- [{checkbox}] Task {task.id}: {task.name} - {task.status.value}")

        self.progress_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def snapshot_state(self, message: str) -> str:
        """
        Commits the durable markdown state when the project is inside a Git repo.
        """
        tracked_paths = [self.spec_path, self.journal_path, self.progress_path]
        existing_paths = [str(path.relative_to(self.root)) for path in tracked_paths if path.exists()]

        if not existing_paths:
            return "No durable state files exist to snapshot."

        try:
            repo_result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=True,
            )
            root_result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=True,
            )
            repo_root = Path(root_result.stdout.strip()).resolve()
            if repo_result.stdout.strip().lower() != "true" or repo_root != self.root.resolve():
                return "Git snapshot skipped: project root is not the Git worktree root."

            subprocess.run(["git", "add", *existing_paths], cwd=self.root, check=True)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            return f"Git snapshot skipped: {exc}"

        if result.returncode == 0:
            return "Git snapshot committed."

        output = (result.stdout + "\n" + result.stderr).strip()
        if "nothing to commit" in output.lower():
            return "Git snapshot skipped: nothing to commit."

        return f"Git snapshot failed: {output}"

