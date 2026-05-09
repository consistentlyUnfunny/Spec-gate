from typing import Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel
from enum import Enum

class OperationalMode(str, Enum):
    SPEC_GATE = "spec-gate"
    RAPID = "rapid"
    VIBE = "vibe"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: int
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    test_cmd: str | None = None
    source_file: str | None = None

class SpecGateState(TypedDict):
    # File paths config
    project_root: str
    spec_path: str
    # task info
    tasks: Annotated[list[Task], "The sequence of tasks derived from SPEC.md"]
    current_task_id: int
    # hash guard to prevent agent drfit (when you edit spec file during task execution)
    last_spec_hash: str
    # context of execution
    journal_tail: str  
    last_test_output: str
    exit_code: int
    last_execution_ok: bool
    retry_counts: dict[int, int]
    active_context: list[str]
    # cost compute
    total_tokens: int
    total_cost: float
    # hitl
    is_approved: bool

