# Project Spec-Gate Technical Documentation

**Version:** `1.1.0-Alpha`

**Role:** Durable AI Orchestration Harness

**Architectural Pattern:** State-Machine Driven Durable Execution

---

## 1. System Overview

**Project Spec-Gate** is a production-grade backend framework designed to host autonomous AI agents. It prioritizes reliability, observability, and cost-efficiency by treating agentic workflows as a series of versioned, human-approved state transitions.

Unlike generic autonomous agents, Spec-Gate utilizes a **Durable Execution** model. Progress is persisted in human-readable Markdown files, allowing for seamless recovery from crashes, token limits, or logic errors.

---

## 2. Core Architectural Pillars

### A. The "Memory Palace" (State Management)

State is not stored in a black-box database; it is managed via Git-versioned Markdown files at the root of the project directory to ensure transparency and version control:

- **`SPEC.md`**: The technical blueprint and project constraints.
- **`JOURNAL.md`**: A chronological record of agent reasoning and tool usage.
- **`PROGRESS.md`**: A task-based checklist featuring real-time token and cost metadata.

### B. Durable Orchestration (LangGraph)

The "brain" of the system is a cyclic state machine built on **LangGraph**.

- **Checkpoints:** Every state change is saved to a persistent store (SQLite/Postgres).
- **Interrupts:** Native support for "Human-in-the-Loop" (HITL) approval nodes.
- **Cycles:** Deterministic retry logic for self-healing when agents fail QA tests.

### C. Agentic TDD (Quality Assurance Gate)

Spec-Gate enforces a **"Trust but Verify"** model:

- **Test-Driven Development:** The orchestrator prevents the agent from moving to "Task N+1" until "Task N" passes all associated unit tests.
- **Exit-Code Gating:** Implementation nodes are physically disconnected from the "Completion" node unless the test runner (e.g., `pytest`, `vitest`) returns `0`.

---

## 3. Module Specifications

### Module 1: The Governance Engine (`specgate.yaml`)

A configuration-first approach to project management.

YAML

`# Example specgate.yaml
project_name: "FinanceTrackerPro"
work_dir: "./src"
knowledge_base: "./docs/obsidian_vault"
budget_limit_usd: 5.00
operation_mode: "spec-gate" # Options: spec-gate, rapid, vibe

agent_settings:
  model: "claude-3-5-sonnet"
  max_retries: 3

qa_settings:
  test_runner: "pytest"
  coverage_threshold: 80`

### Module 2: The Observability Dashboard

A local web interface designed to demystify agent autonomy.

- **Live Graph Visualizer:** Real-time tracking of the active node in the LangGraph.
- **The "Gas Gauge":** Real-time estimation of USD spend per feature/task.
- **Graduated Trust Toggle:** A 3-way switch to toggle between **Spec-Gate** (High Rigor), **Rapid** (Auto-Approve), and **Vibe** (Direct Execution).

### Module 3: Linked Context Engine (JIT Knowledge)

Inspired by Obsidian-style bidirectional linking to manage context windows efficiently:

- **Bidirectional Parsing:** The orchestrator scans `SPEC.md` for `[[WikiLinks]]`.
- **Just-in-Time (JIT) Loading:** Only the linked markdown files are injected into the agent's context, preventing "Context Bloat" and reducing costs.

---

## 4. Operational Workflow & Graduated Trust

Spec-Gate adapts its workflow based on the selected `operation_mode` to balance safety and velocity.

1. **Initialize:** Load `specgate.yaml` and set up file system watchers.
2. **Plan:** Agent drafts `SPEC.md` based on the initial user prompt.
3. **Approve:**
    - *Spec-Gate Mode:* Orchestrator enters `WAIT` state for human signature.
    - *Rapid Mode:* Agent auto-approves if the plan aligns with high-level goals.
4. **Execute:**
    - Agent creates unit tests and writes implementation.
    - *Spec-Gate Mode:* Tests **must** return exit `0` to progress.
    - *Rapid Mode:* Tests are run, but failures generate a warning instead of a "Hard Halt."
    - *Vibe Mode:* Skips test generation/execution entirely for maximum speed.
5. **Summarize:** Every 2,000 tokens, the "Librarian" node compresses `JOURNAL.md` into a snapshot.
6. **Deliver:** Final project summary and code delivery.

---

## 5. Value Proposition

- **Insurance against "Infinite Loops":** Hard-coded budget caps save hundreds in API costs.
- **Recovery from "Agent Drift":** Resumable state means 4-hour tasks don't need to be restarted from scratch.
- **Senior-Level Engineering:** Provides an audit trail and QA rigor that "Vibe Coding" cannot replicate.

---

## 6. Project Roadmap

| **Phase** | **Focus** | **Key Deliverables** |
| --- | --- | --- |
| **Phase 1** | **Core** | LangGraph state machine, Markdown sync, Git versioning. |
| **Phase 2** | **Governance** | `specgate.yaml` engine and HITL approval gates. |
| **Phase 3** | **Optimization** | JIT Knowledge Engine, Recursive Summarization, Rapid Mode. |
| **Phase 4** | **Observability** | Metrics Dashboard and UI Polish. |