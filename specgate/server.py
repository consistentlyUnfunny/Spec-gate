from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .observability import ObservabilityService
from .orchestrator_runner import OrchestratorRunner

def run():
    import uvicorn

    uvicorn.run(
        "specgate.server:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
    )



def create_app(project_root: str = ".", graph: Any | None = None) -> FastAPI:
    app = FastAPI(title="Spec-Gate Observability", version="0.1.0")
    service = ObservabilityService(project_root=project_root, graph=graph)
    runner = OrchestratorRunner(graph)
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return index_path.read_text(encoding="utf-8")

        return """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Spec-Gate React Dashboard</title>
          </head>
          <body>
            <main>
              <h1>Spec-Gate React Dashboard</h1>
              <p>The React frontend has not been built yet.</p>
              <p>Run <code>cd frontend</code>, <code>npm install</code>, then <code>npm run dev</code> for development or <code>npm run build</code> for FastAPI serving.</p>
            </main>
          </body>
        </html>
        """

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return service.status()

    @app.get("/api/tasks")
    def tasks() -> list[dict[str, Any]]:
        return service.tasks()

    @app.get("/api/progress")
    def progress() -> dict[str, Any]:
        return service.progress()

    @app.get("/api/config")
    def config() -> dict[str, Any]:
        return service.config_snapshot()

    @app.get("/api/journal")
    def journal() -> dict[str, Any]:
        return service.journal()

    @app.get("/api/agents")
    def agents() -> list[dict[str, Any]]:
        return service.agents()

    @app.post("/api/workdir")
    def update_workdir(payload: dict[str, str] = Body(...)) -> dict[str, Any]:
        try:
            return service.update_work_dir(payload.get("work_dir", ""))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/operation-mode")
    def update_operation_mode(payload: dict[str, str] = Body(...)) -> dict[str, Any]:
        try:
            return service.update_operation_mode(payload.get("operation_mode", ""))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/reset-metrics")
    def reset_metrics() -> dict[str, Any]:
        return service.reset_metrics()

    @app.post("/api/reset-activity")
    def reset_activity() -> dict[str, Any]:
        return service.reset_activity()

    @app.post("/api/open-workdir")
    def open_workdir() -> dict[str, str]:
        return service.open_work_dir()

    @app.post("/api/open-workspace-path")
    def open_workspace_path(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
        try:
            return service.open_workspace_path(
                payload.get("filepath", ""),
                reveal=bool(payload.get("reveal", False)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/select-workdir")
    def select_workdir() -> dict[str, Any]:
        return service.select_work_dir()

    @app.get("/api/graph-state")
    def graph_state() -> dict[str, Any]:
        return service.graph_state()

    @app.post("/api/run")
    def run_orchestrator() -> dict[str, str]:
        result = runner.start()
        if result["status"] == "unavailable":
            raise HTTPException(status_code=503, detail=result["message"])
        return result

    @app.post("/api/stop")
    def stop_orchestrator() -> dict[str, str]:
        return runner.stop()

    @app.get("/api/run-status")
    def run_status() -> dict[str, str]:
        return runner.status()

    @app.get("/api/help")
    def help_content() -> dict[str, str]:
        readme_path = Path(project_root) / "README.md"
        if not readme_path.exists():
            return {"content": "# Spec-Gate Help\n\nREADME.md was not found."}
        return {"content": readme_path.read_text(encoding="utf-8")}

    return app


try:
    from .graph import graph as runtime_graph
except Exception:
    runtime_graph = None


app = create_app(graph=runtime_graph)
