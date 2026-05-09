# Spec-Gate

Spec-Gate is a local AI orchestration harness for running implementation tasks from a durable project specification. It uses `SPEC.md` as the task source, LangGraph as the workflow engine, Markdown files for recoverable state, and a React/FastAPI dashboard for observing and controlling runs.

The core idea is simple: write or generate a clear spec, let the agent work task-by-task, verify with tests, and keep all progress visible.

## What Spec-Gate Is For

Spec-Gate is meant to make AI-assisted coding less fragile. Instead of giving an agent one large prompt and hoping it finishes correctly, you give it a durable spec made of small tasks. The system then executes those tasks through a controlled loop.

It is useful when you want:

- A visible plan before implementation.
- Task-by-task execution instead of one giant autonomous run.
- Test-gated progress.
- A recoverable audit trail.
- Local model support through Ollama.
- A dashboard that shows what the agent is doing.
- A safer output boundary through `work_dir`.

Spec-Gate is not trying to replace an engineer. It is closer to a disciplined project harness around AI coding: the human owns the intent and review, while the agent handles bounded implementation attempts.

## Why It Exists

AI coding agents can drift, loop, forget context, or mark work as done when nothing useful happened. Spec-Gate exists to reduce those failure modes.

The design goals are:

- **Durability:** progress survives crashes, restarts, and long runs.
- **Transparency:** state is stored in files you can read.
- **Control:** tasks come from `SPEC.md`, not hidden state.
- **Verification:** tests gate completion in `spec-gate` mode.
- **Observability:** the dashboard shows progress, usage, activity, and agents.
- **Containment:** file writes are restricted to a configured working directory.

## How Spec-Gate Works

Spec-Gate reads tasks from `SPEC.md`. A task must use this checkbox format:

```md
- [ ] Task name: Task description.
```

When the task is completed, Spec-Gate marks it as:

```md
- [x] Task name: Task description.
```

The orchestrator flow is:

1. **Planner** reads `SPEC.md` and finds the next unchecked task.
2. **Executor** asks the configured model to make file changes with tools.
3. **Tester** runs the configured test command, usually `pytest`.
4. If tests pass, the task is checked off.
5. If tests fail, Spec-Gate retries until `max_retries` is reached.
6. The dashboard shows tasks, cost, token usage, agent status, and activity.

## Memory Technique

Spec-Gate uses a “Memory Palace” style of state management. The idea is that important memory should live in named places that are easy for humans and agents to revisit.

There are three layers:

- **Project memory:** durable Markdown files such as `SPEC.md`, `.specgate/JOURNAL.md`, `.specgate/PROGRESS.md`, and `.specgate/SUMMARY.md`.
- **Spatial memory:** execution memories are grouped by domain and task, using a structure like `wing -> room -> context`. For example, the `core` wing can contain a room for a task, and that room can store verified successes or pitfalls.
- **Linked context:** `SPEC.md` can contain `[[WikiLinks]]`, and Spec-Gate loads only those linked Markdown files from `knowledge_base`.

This gives the agent a small, relevant context window instead of dumping every document into every prompt. It also gives the human readable recovery points when something goes wrong.

In practice:

- `SPEC.md` is the blueprint.
- `PROGRESS.md` is the task and usage dashboard source.
- `JOURNAL.md` is the run log.
- `SUMMARY.md` keeps compacted history when the journal grows.
- Linked docs in `knowledge_base` provide just-in-time background context.

## Recommended Workflow

You can write `SPEC.md` by hand, but the best workflow is to ask an AI to draft it for you.

Example prompt to use in ChatGPT or another planning model:

```text
Write a SPEC.md for this project using Spec-Gate task format.

Requirements:
- Use Markdown.
- Include a short Goal section.
- Include a Tasks section.
- Every task must use this exact format:
  - [ ] Task name: Task description.
- Keep each task small enough to implement and test independently.

Project idea:
<describe what you want built>
```

Then paste the generated Markdown into `SPEC.md`, review it, save it, and run Spec-Gate from the dashboard.

## Quick Start

Install dependencies:

```powershell
uv sync
cd frontend
npm.cmd install
npm.cmd run build
cd ..
```

Start the dashboard and API:

```powershell
uv run specgate-dashboard
```

Open:

```text
http://127.0.0.1:8765/
```

Edit `SPEC.md`, save it, then click **Run** in the dashboard.

## Running With Ollama

Start Ollama:

```powershell
ollama serve
```

Pull a coding model:

```powershell
ollama pull qwen2.5-coder
```

Set `.env`:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_API_KEY=ollama
```

Configure `specgate.yaml`:

```yaml
project_name: "Spec-Gate-Demo"
work_dir: "./workspace"
knowledge_base: "./docs"
operation_mode: "spec-gate"

agent_settings:
  executor:
    provider: "ollama"
    model: "qwen2.5-coder"
    temperature: 0.3
    max_retries: 3
    budget_limit_usd: 5.0

qa_settings:
  test_runner: "pytest"
  coverage_threshold: 80

dashboard:
  agents:
    - name: Planner
      node: planner
      role: planning
    - name: Executor
      node: executor
      role: implementation
    - name: Tester
      node: tester
      role: quality gate
```

Local Ollama models vary in tool-calling quality. If a model does not create files, check the Activity panel. Spec-Gate will no longer mark a task complete when no successful tool calls happened.

## Using OpenAI Or Another OpenAI-Compatible API

Change credentials in `.env`:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
```

Change the executor provider and model in `specgate.yaml`:

```yaml
agent_settings:
  executor:
    provider: "openai"
    model: "gpt-4.1-mini"
    temperature: 0.2
    max_retries: 3
    budget_limit_usd: 5.0
    input_cost_per_million_tokens: 0.40
    output_cost_per_million_tokens: 1.60
```

The config loader maps credentials by provider name:

```text
provider: "openai" -> OPENAI_BASE_URL and OPENAI_API_KEY
provider: "ollama" -> OLLAMA_BASE_URL and OLLAMA_API_KEY
```

## Where To Configure Things

Use `specgate.yaml` for project behavior:

```yaml
project_name: "My Project"
work_dir: "./workspace"
knowledge_base: "./docs"
operation_mode: "spec-gate"

agent_settings:
  executor:
    provider: "ollama"
    model: "qwen2.5-coder"
    temperature: 0.3
    max_retries: 3
    budget_limit_usd: 5.0

qa_settings:
  test_runner: "pytest"
  coverage_threshold: 80

dashboard:
  agents:
    - name: Planner
      node: planner
      role: planning
    - name: Executor
      node: executor
      role: implementation
    - name: Tester
      node: tester
      role: quality gate
    - name: Librarian
      node: librarian
      role: summarization
```

Use `.env` for secrets:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_API_KEY=ollama
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
```

Do not commit `.env`.

## Working Directory

`work_dir` controls where the AI is allowed to create and modify files.

Example:

```yaml
work_dir: "./workspace"
```

The dashboard also has a Working Directory control. Click **Browse** to choose a folder using your local file explorer. The selected folder is saved back into `specgate.yaml`.

The file tools are restricted to this directory, so paths like `../outside.py` are rejected.

## Dashboard Controls

The dashboard runs at:

```text
http://127.0.0.1:8765/
```

Controls:

- **Run** starts or resumes the orchestration loop.
- **Stop** requests the runner to stop after the current graph step finishes.
- **Reset** clears token and cost metrics while preserving task status.
- **Browse** opens a native folder picker for `work_dir`.
- **Save** saves a typed working directory path.
- **Help** opens this README inside the dashboard.
- The moon/sun button toggles dark mode.

The dashboard auto-refreshes, so there is no manual refresh button.

Action results appear as dismissible snackbar messages in the lower-right corner.

## Agent Display Configuration

The Agents panel is driven by `specgate.yaml`, not hardcoded in the frontend. This lets you change the graph shape without rewriting the dashboard.

Default example:

```yaml
dashboard:
  agents:
    - name: Planner
      node: planner
      role: planning
    - name: Executor
      node: executor
      role: implementation
    - name: Tester
      node: tester
      role: quality gate
    - name: Librarian
      node: librarian
      role: summarization
```

The `node` value must match the LangGraph node name. When LangGraph reports that node as the current `next_node`, the dashboard highlights that agent card.

If you later change the graph to a different team, update the config:

```yaml
dashboard:
  agents:
    - name: Researcher
      node: research
      role: context gathering
    - name: Architect
      node: architect
      role: system design
    - name: Coder
      node: coder
      role: implementation
    - name: Reviewer
      node: reviewer
      role: code review
    - name: Tester
      node: tester
      role: quality gate
```

The dashboard will render those agents automatically.

## Durable State Files

Spec-Gate writes recoverable state into `.specgate/`:

```text
.specgate/JOURNAL.md
.specgate/PROGRESS.md
.specgate/SUMMARY.md
.specgate/checkpoint.db
```

`PROGRESS.md` stores task progress and usage totals. `JOURNAL.md` stores execution activity. `SUMMARY.md` stores compacted journal snapshots.

## JIT Knowledge With WikiLinks

You can link supporting docs from `SPEC.md`:

```md
Use [[Architecture Notes]] and [[API Contracts]].
```

If `knowledge_base` is `./docs`, Spec-Gate will try to load:

```text
docs/Architecture Notes.md
docs/API Contracts.md
```

Only linked Markdown files are injected into the executor context.

## Test Task

Paste this into `SPEC.md` to test the loop:

```md
# Project Specification

## Goal

Test that Spec-Gate can create a tiny Python feature and verify it with pytest.

## Tasks

- [ ] Create greeting utility: Inside the configured working directory, create `specgate_demo.py` with a function `build_greeting(name: str) -> str` that returns `Hello, {name}!`. Also create `test_specgate_demo.py` with a pytest test that verifies `build_greeting("Ada")` returns `Hello, Ada!`.
```

Expected files appear inside the configured `work_dir`.

## Development Commands

Run backend and built React app:

```powershell
uv run specgate-dashboard
```

Develop the React frontend with hot reload:

```powershell
uv run specgate-dashboard
cd frontend
npm.cmd run dev
```

Run tests:

```powershell
uv run pytest
```

Build frontend:

```powershell
cd frontend
npm.cmd run build
```

## Current Limitations

- Stop is cooperative. It stops between graph steps but cannot instantly kill an in-flight model call.
- Local models may not reliably support tool calling.
- The browser cannot safely expose arbitrary filesystem paths by itself, so folder selection is handled by the local FastAPI backend.
