# Contributing to Spec-Gate

Thanks for helping improve Spec-Gate. This project is a local AI orchestration harness, so reliability, observability, and safe filesystem behavior matter as much as feature polish.

## Setup

Install backend dependencies:

```powershell
uv sync
```

Install and build the frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run build
cd ..
```

Start the dashboard:

```powershell
uv run specgate-dashboard
```

Open:

```text
http://127.0.0.1:8765/
```

## Configuration

Use `specgate.yaml` for project settings such as `work_dir`, provider, model, and dashboard agents.

Use `.env` for secrets. Do not commit `.env`.

Supported provider credential pattern:

```text
<PROVIDER>_BASE_URL
<PROVIDER>_API_KEY
```

For OpenRouter, `OPENROUTER_BASE_UR` is also accepted as a compatibility alias.

## Development Workflow

1. Keep tasks in `SPEC.md` small and independently testable.
2. Run the dashboard and execute one task at a time when testing orchestration behavior.
3. Use the Activity panel to verify model calls, tool calls, changed files, and test results.
4. Keep AI-created files inside the configured `work_dir`.
5. Avoid committing generated workspace output unless it is intentionally part of a test fixture.

## Tests

Run all backend tests:

```powershell
uv run pytest
```

Run frontend build checks:

```powershell
cd frontend
npm.cmd run build
```

Please add or update tests when changing:

- config loading
- workspace file tools
- graph routing
- dashboard API endpoints
- observability/activity parsing
- usage and cost tracking

## Coding Guidelines

- Prefer existing patterns before adding new abstractions.
- Keep file operations constrained to the configured workspace.
- Make dashboard state visible and actionable; avoid silent background failures.
- Do not expose API keys, `.env` contents, or raw secrets in logs or UI responses.
- When adding provider support, keep credentials provider-scoped and configurable through environment variables.

## Pull Request Checklist

- Backend tests pass with `uv run pytest`.
- Frontend builds with `npm.cmd run build`.
- New behavior is visible in the dashboard when relevant.
- Activity logs explain slow, failed, or long-running operations clearly.
- Documentation is updated if setup, configuration, or workflows change.
