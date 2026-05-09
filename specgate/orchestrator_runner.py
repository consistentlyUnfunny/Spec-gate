import traceback
from threading import Lock, Thread
from typing import Any

from .runtime import THREAD_CONFIG, create_initial_state
from .tools.file_ops import configure_workspace
from .utils.config_loader import load_config
from .utils.io_manager import IOManager


class OrchestratorRunner:
    """
    Runs the LangGraph orchestration loop from API requests without blocking FastAPI.
    """

    def __init__(self, graph: Any | None):
        self.graph = graph
        self.io = IOManager(".")
        self._lock = Lock()
        self._thread: Thread | None = None
        self._status = "idle"
        self._last_error = ""
        self._current_step = "Idle"
        self._stop_requested = False

    def start(self) -> dict[str, str]:
        if self.graph is None:
            return {"status": "unavailable", "message": "Graph is not available."}

        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"status": "running", "message": "Orchestrator is already running."}

            self._status = "running"
            self._last_error = ""
            self._current_step = "Starting orchestrator"
            self._stop_requested = False
            self.io.append_activity("Runner", "Run requested from dashboard.")
            self._thread = Thread(target=self._run_loop, daemon=True)
            self._thread.start()

        return {"status": "running", "message": "Orchestrator started."}

    def stop(self) -> dict[str, str]:
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                self._status = "stopped"
                return {"status": "stopped", "message": "Orchestrator is not running."}

            self._stop_requested = True
            self._status = "stopping"
            self._current_step = "Stopping after current graph step"
            self.io.append_activity("Runner", "Stop requested. Waiting for the current graph step to finish.")
            return {"status": "stopping", "message": "Stop requested. Current graph step will finish first."}

    def status(self) -> dict[str, str]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                status = "stopping" if self._stop_requested else "running"
            else:
                status = self._status
            return {"status": status, "last_error": self._last_error, "current_step": self._current_step}

    def _run_loop(self) -> None:
        try:
            self._set_step("Configuring workspace")
            configure_workspace(load_config().work_dir)
            self.io.append_activity("Runner", "Workspace configured. Loading graph checkpoint.")
            snapshot = self.graph.get_state(THREAD_CONFIG)
            if not snapshot.next:
                self._set_step("Planning next task")
                self.io.append_activity("Runner", "No active checkpoint node. Starting from the planner.")
                for _ in self.graph.stream(create_initial_state(), THREAD_CONFIG):
                    if self._should_stop():
                        self._mark_stopped()
                        return

            while True:
                if self._should_stop():
                    self._mark_stopped()
                    return

                snapshot = self.graph.get_state(THREAD_CONFIG)
                if not snapshot.next:
                    break

                next_node = snapshot.next[0]
                self._set_step(f"Running graph node: {next_node}")
                self.io.append_activity("Runner", f"Resuming graph at `{next_node}`.")
                for _ in self.graph.stream(None, THREAD_CONFIG):
                    if self._should_stop():
                        self._mark_stopped()
                        return

            with self._lock:
                self._status = "completed"
                self._current_step = "Completed"
            self.io.append_activity("Runner", "Run completed.")
        except Exception as exc:
            print("Orchestrator run failed:")
            traceback.print_exc()
            with self._lock:
                self._status = "failed"
                self._last_error = str(exc)
                self._current_step = "Failed"
            self.io.append_activity("Runner", f"Run failed: {exc}")

    def _should_stop(self) -> bool:
        with self._lock:
            return self._stop_requested

    def _mark_stopped(self) -> None:
        with self._lock:
            self._status = "stopped"
            self._current_step = "Stopped"
            self._stop_requested = False
        self.io.append_activity("Runner", "Run stopped.")

    def _set_step(self, step: str) -> None:
        with self._lock:
            self._current_step = step
