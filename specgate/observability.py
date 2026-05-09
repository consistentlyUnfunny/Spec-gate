import re
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from .state import OperationalMode
from .utils.config_loader import Config, load_config
from .utils.io_manager import IOManager


class ObservabilityService:
    """
    Reads Spec-Gate's durable state files for API/dashboard consumers.
    """

    def __init__(self, project_root: str = ".", graph: Any | None = None, thread_id: str = "project-specgate-dev"):
        self.project_root = Path(project_root)
        self.io = IOManager(project_root)
        self.config = load_config(project_root)
        self.graph = graph
        self.thread_config = {"configurable": {"thread_id": thread_id}}

    def status(self) -> dict[str, Any]:
        graph_state = self.graph_state()
        tasks = self.tasks()
        progress = self.progress()
        active_task = next((task for task in tasks if task["status"] == "pending"), None)

        return {
            "project_name": self.config.project_name,
            "operation_mode": self.config.operation_mode.value,
            "work_dir": self.config.work_dir,
            "active_node": graph_state.get("next_node"),
            "active_task": active_task,
            "task_counts": self._task_counts(tasks),
            "total_tokens": progress.get("total_tokens", 0),
            "total_cost": progress.get("total_cost", 0.0),
            "budget_limit_usd": self.config.agent_settings.executor.budget_limit_usd,
            "budget_used_ratio": self._budget_ratio(progress.get("total_cost", 0.0), self.config),
        }

    def tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "status": task.status.value,
                "test_cmd": task.test_cmd,
                "source_file": task.source_file,
            }
            for task in self.io.parse_tasks_from_spec()
        ]

    def progress(self) -> dict[str, Any]:
        progress_text = self._read_text(self.io.progress_path)

        return {
            "total_tokens": self._read_int(progress_text, r"Total tokens:\s*(\d+)"),
            "total_cost": self._read_float(progress_text, r"Total cost:\s*\$?([0-9.]+)"),
            "raw": progress_text,
        }

    def config_snapshot(self) -> dict[str, Any]:
        return {
            "project_name": self.config.project_name,
            "knowledge_base": self.config.knowledge_base,
            "work_dir": self.config.work_dir,
            "operation_mode": self.config.operation_mode.value,
            "executor": self.config.agent_settings.executor.model_dump(exclude={"api_key"}),
            "qa_settings": self.config.qa_settings.model_dump(),
            "dashboard": self.config.dashboard.model_dump(),
        }

    def journal(self, tail_chars: int = 6000) -> dict[str, Any]:
        journal = self._read_text(self.io.journal_path)
        summary = self._read_text(self.io.summary_path)

        return {
            "journal_tail": journal[-tail_chars:],
            "summary_tail": summary[-tail_chars:],
            "events": self.activity_events(journal),
            "artifacts": self.activity_artifacts(journal),
        }

    def activity_events(self, journal: str | None = None) -> list[dict[str, str]]:
        journal = journal if journal is not None else self._read_text(self.io.journal_path)
        events: list[dict[str, Any]] = []
        current_title = "General"

        for line in journal.splitlines():
            if line.startswith("## Task:"):
                current_title = line.replace("## Task:", "", 1).strip()
                events.append({"type": "task", "title": current_title, "detail": "Task execution started."})
            elif line.startswith("- "):
                detail = line[2:].strip()
                event_type = "info"
                if "FAILED" in detail or "Error:" in detail:
                    event_type = "error"
                elif any(marker in detail for marker in ["Calling ", "Running ", "waiting", "Resuming graph", "Run requested"]):
                    event_type = "active"
                elif "Success:" in detail or "Usage:" in detail:
                    event_type = "success"
                event = {"type": event_type, "title": current_title, "detail": detail}
                file_path = self._file_path_from_activity(detail)
                if file_path:
                    event["file"] = file_path
                events.append(event)

        for artifact in self.activity_artifacts(journal):
            events.append(
                {
                    "type": "success",
                    "title": "Files changed",
                    "detail": f"{artifact['action']} {artifact['file']}",
                    "file": artifact["file"],
                }
            )

        return events[-40:]

    def activity_artifacts(self, journal: str | None = None) -> list[dict[str, str]]:
        journal = journal if journal is not None else self._read_text(self.io.journal_path)
        artifacts: dict[str, dict[str, str]] = {}

        for line in journal.splitlines():
            if not line.startswith("- "):
                continue

            detail = line[2:].strip()
            file_path = self._file_path_from_activity(detail)
            if not file_path:
                continue

            action = "Modified" if "Success: Modified" in detail else "Created"
            artifacts[file_path] = {"file": file_path, "action": action}

        return list(artifacts.values())

    def agents(self) -> list[dict[str, Any]]:
        graph_state = self.graph_state()
        active_node = graph_state.get("next_node")
        agents = []

        for agent in self.config.dashboard.agents:
            if active_node == agent.node:
                status = "waiting" if agent.node == "executor" else "active"
            else:
                status = "idle"

            agents.append({
                "name": agent.name,
                "node": agent.node,
                "role": agent.role,
                "status": status,
            })

        return agents

    def update_work_dir(self, work_dir: str) -> dict[str, Any]:
        clean_work_dir = work_dir.strip()
        if not clean_work_dir:
            raise ValueError("work_dir cannot be empty.")

        data = self._config_data()
        data["work_dir"] = clean_work_dir
        self._write_config(data)
        (self.project_root / self.config.work_dir).mkdir(parents=True, exist_ok=True)

        return self.config_snapshot()

    def update_operation_mode(self, operation_mode: str) -> dict[str, Any]:
        try:
            mode = OperationalMode(operation_mode)
        except ValueError as exc:
            valid = ", ".join(mode.value for mode in OperationalMode)
            raise ValueError(f"operation_mode must be one of: {valid}") from exc

        data = self._config_data()
        data["operation_mode"] = mode.value
        self._write_config(data)

        return self.config_snapshot()

    def _config_data(self) -> dict[str, Any]:
        config_path = self.project_root / "specgate.yaml"
        data: dict[str, Any] = {}
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return data

    def _write_config(self, data: dict[str, Any]) -> None:
        config_path = self.project_root / "specgate.yaml"
        config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        self.config = load_config(str(self.project_root))

    def reset_metrics(self) -> dict[str, Any]:
        self.io.reset_metrics()
        return self.progress()

    def reset_activity(self) -> dict[str, Any]:
        self.io.reset_activity()
        return self.journal()

    def open_workspace_path(self, filepath: str, reveal: bool = False) -> dict[str, str]:
        target = self._workspace_path(filepath)
        if not target.exists():
            raise ValueError(f"{filepath} does not exist inside work_dir.")

        if reveal:
            self._reveal_path(target)
            path_to_open = target.parent if target.is_file() else target
        else:
            path_to_open = target
            self._open_path(path_to_open)

        return {"path": str(path_to_open), "status": "opened"}

    def open_work_dir(self) -> dict[str, str]:
        work_dir = (self.project_root / self.config.work_dir).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)

        self._open_path(work_dir)

        return {"path": str(work_dir), "status": "opened"}

    def select_work_dir(self) -> dict[str, Any]:
        selected_path = self._ask_directory()
        if not selected_path:
            return self.config_snapshot() | {"selected": False}

        selected = Path(selected_path).resolve()
        try:
            work_dir = str(selected.relative_to(self.project_root.resolve()))
        except ValueError:
            work_dir = str(selected)

        snapshot = self.update_work_dir(work_dir)
        return snapshot | {"selected": True}

    def _ask_directory(self) -> str:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            return filedialog.askdirectory(
                title="Select Spec-Gate working directory",
                initialdir=str((self.project_root / self.config.work_dir).resolve()),
                mustexist=False,
            )
        finally:
            root.destroy()

    def _open_path(self, path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _reveal_path(self, path: Path) -> None:
        if sys.platform.startswith("win"):
            if path.is_file():
                subprocess.Popen(["explorer", f"/select,{str(path)}"])
            else:
                os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            if path.is_file():
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["open", str(path)])
        else:
            folder = path.parent if path.is_file() else path
            subprocess.Popen(["xdg-open", str(folder)])

    def _workspace_path(self, filepath: str) -> Path:
        work_dir = (self.project_root / self.config.work_dir).resolve()
        target = (work_dir / filepath).resolve()
        try:
            target.relative_to(work_dir)
        except ValueError as exc:
            raise ValueError(f"{filepath} escapes configured work_dir.") from exc
        return target

    def _file_path_from_activity(self, detail: str) -> str | None:
        match = re.search(r"Success:\s+(?:Created|Modified)\s+(.+)$", detail)
        if not match:
            return None

        filepath = match.group(1).strip()
        try:
            self._workspace_path(filepath)
        except ValueError:
            return None
        return filepath

    def graph_state(self) -> dict[str, Any]:
        if self.graph is None:
            return {"available": False, "next": [], "next_node": None, "values": {}}

        try:
            snapshot = self.graph.get_state(self.thread_config)
        except Exception as exc:
            return {"available": False, "error": str(exc), "next": [], "next_node": None, "values": {}}

        values = getattr(snapshot, "values", {}) or {}
        next_nodes = list(getattr(snapshot, "next", ()) or [])

        return {
            "available": True,
            "next": next_nodes,
            "next_node": next_nodes[0] if next_nodes else None,
            "values": self._json_safe(values),
        }

    def _task_counts(self, tasks: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"pending": 0, "completed": 0, "failed": 0, "in_progress": 0}
        for task in tasks:
            status = task["status"]
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _budget_ratio(self, total_cost: float, config: Config) -> float:
        budget = config.agent_settings.executor.budget_limit_usd
        if budget <= 0:
            return 0.0
        return min(total_cost / budget, 1.0)

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _read_int(self, text: str, pattern: str) -> int:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0

    def _read_float(self, text: str, pattern: str) -> float:
        match = re.search(pattern, text)
        return float(match.group(1)) if match else 0.0

    def _json_safe(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        return value
