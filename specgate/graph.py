import sqlite3
import shlex
import subprocess
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .state import OperationalMode, SpecGateState, TaskStatus
from .utils.io_manager import IOManager
from .utils.knowledge_loader import KnowledgeLoader
from .utils.spatial_context_store import SpatialContextStore
from .utils.config_loader import load_config
from .utils.usage_tracker import calculate_usage_report
from .tools.file_ops import configure_workspace, replace_content_block, create_file


io = IOManager(project_root=".")
cfg = load_config()

conn = sqlite3.connect(".specgate/checkpoint.db", check_same_thread=False)
memory = SqliteSaver(conn)

base_store = InMemoryStore()
spatial_store = SpatialContextStore(base_store)
knowledge_loader = KnowledgeLoader(project_root=".", knowledge_base=cfg.knowledge_base)
configure_workspace(cfg.work_dir)

exec_cfg = cfg.agent_settings.executor

executor_llm = ChatOpenAI(
    base_url=exec_cfg.base_url,
    api_key=exec_cfg.api_key,
    model=exec_cfg.model,
    temperature=exec_cfg.temperature
)

# bind tools
tools = [replace_content_block, create_file]
llm_with_tools = executor_llm.bind_tools(tools)

def route_after_planner(state: SpecGateState) -> str:
    return "end" if state["current_task_id"] == -1 else "executor"


def route_after_executor(state: SpecGateState) -> str:
    return "planner" if cfg.operation_mode == OperationalMode.VIBE else "tester"


def route_after_tester(state: SpecGateState) -> str:
    if state["exit_code"] == 0:
        return "planner"

    if cfg.operation_mode == OperationalMode.RAPID and state.get("last_execution_ok", False):
        return "planner"

    task_id = state["current_task_id"]
    retry_count = state.get("retry_counts", {}).get(task_id, 0)
    if retry_count >= exec_cfg.max_retries:
        return "end"

    return "executor"


def planner_node(state: SpecGateState): 
    """
    Syncs specs.md to graph state
    """
    print("***Node: Planner***")
    io.append_activity("Planner", "Reading SPEC.md and selecting the next pending task.")
    if io.compact_journal():
        print("Journal compacted into SUMMARY.md")

    current_hash = io.get_spec_hash()
    if state.get("last_spec_hash") != current_hash:
        print("SPEC.md changed, Re-syncing tasks...")
        
    tasks = io.parse_tasks_from_spec()
    spec_markdown = io.spec_path.read_text(encoding="utf-8") if io.spec_path.exists() else ""
    knowledge_documents = knowledge_loader.load_linked_documents(spec_markdown)
    active_context = [knowledge_loader.format_for_prompt(knowledge_documents)] if knowledge_documents else []

    next_task = next((
        t for t in tasks if t.status == TaskStatus.PENDING), 
        None
    )

    if not next_task:
        print("All tasks completed")
        io.append_activity("Planner", "No pending tasks found.")
        io.sync_progress(tasks, state.get("total_tokens", 0), state.get("total_cost", 0.0))
        print(io.snapshot_state("Spec-Gate state: all tasks completed"))
        return {
            "tasks": tasks,
            "current_task_id": -1,
            "last_spec_hash": current_hash,
            "active_context": active_context,
        }

    io.sync_progress(tasks, state.get("total_tokens", 0), state.get("total_cost", 0.0))
    io.append_activity("Planner", f"Next task selected: {next_task.name}.")
    return {
        "tasks": tasks,
        "current_task_id": next_task.id,
        "last_spec_hash": current_hash,
        "active_context": active_context,
        "is_approved": False  # Reset approval for the new task
    }


def executor_node(state: SpecGateState):
    """
    Execute instructions
    """
    print("\n*** Node: Executor ***")
    active_task = next(t for t in state["tasks"] if t.id == state["current_task_id"])
    print(f"Working on: {active_task.name}")
    io.append_activity(active_task.name, f"Executor started with `{exec_cfg.provider}/{exec_cfg.model}`.")
    
    # Retrieve Spatial Context (Memory), tasks name as room
    room_memory = spatial_store.get_room_context(wing="core", room=active_task.name)
    pitfalls = room_memory.get("pitfalls", [])
    
    pitfall_text = ""
    if pitfalls:
        pitfall_text = "\nPREVIOUS FAILURES TO AVOID:\n" + "\n".join([str(p) for p in pitfalls])

    context_text = "\n\n".join(state.get("active_context", []))
    if context_text:
        context_text = f"\n{context_text}\n"

    system_prompt = SystemMessage(content=f"""
    You are a Senior Backend Engineer. 
    Current Task: {active_task.name}
    Description: {active_task.description}
    {context_text}
    {pitfall_text}
    
    CRITICAL INSTRUCTIONS:
    - Use the 'replace_content_block' tool to modify existing files.
    - The 'search_block' MUST be an EXACT, character-for-character copy.
    - If creating a new file, use 'create_file'.
    """)

    messages = [system_prompt, HumanMessage(content="Execute the task using your tools. Only call the tools, do not output conversational text.")]

    print(f"Waiting for {exec_cfg.model} to think...")
    io.append_activity(active_task.name, "Calling model and waiting for tool calls.")
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as exc:
        error_detail = str(exc)
        if exec_cfg.provider.lower() == "openrouter" and "401" in error_detail:
            error_detail = (
                "OpenRouter authentication failed with 401. "
                "Check that OPENROUTER_API_KEY is loaded and valid."
            )
        print(f"Model call failed: {error_detail}")
        io.append_activity(active_task.name, f"Model call failed: {error_detail}")
        raise
    io.append_activity(active_task.name, "Model response received. Inspecting tool calls.")
    usage_report = calculate_usage_report(
        response,
        exec_cfg.input_cost_per_million_tokens,
        exec_cfg.output_cost_per_million_tokens,
    )
    total_tokens = state.get("total_tokens", 0) + usage_report.total_tokens
    total_cost = state.get("total_cost", 0.0) + usage_report.cost_usd
    budget_exceeded = total_cost > exec_cfg.budget_limit_usd

    # Append to Journal
    with open(io.journal_path, "a", encoding="utf-8") as f:
        f.write(f"\n## Task: {active_task.name}\n")
        f.write(f"- Attempting execution using {exec_cfg.model}...\n")
        f.write(
            "- Usage: "
            f"{usage_report.input_tokens} input tokens, "
            f"{usage_report.output_tokens} output tokens, "
            f"{usage_report.total_tokens} total tokens, "
            f"${usage_report.cost_usd:.6f} estimated cost.\n"
        )

    if response.tool_calls:
        successful_tool_calls = 0
        for tool_call in response.tool_calls:
            print(f"Tool Called: {tool_call['name']}")
            io.append_activity(active_task.name, f"Calling tool `{tool_call['name']}`.")
            
            if tool_call["name"] == "replace_content_block":
                result = replace_content_block.invoke(tool_call["args"])
            elif tool_call["name"] == "create_file":
                result = create_file.invoke(tool_call["args"])
            else:
                result = "Error: Unknown tool."
                
            print(f"Tool Result: {result}")
            if isinstance(result, str) and result.startswith("Success:"):
                successful_tool_calls += 1
            
            with open(io.journal_path, "a", encoding="utf-8") as f:
                f.write(f"- Executed `{tool_call['name']}`: {result}\n")
    else:
        successful_tool_calls = 0
        print("LLM didn't call any tools. It might have hallucinated conversational text.")
        content_preview = str(response.content).strip().replace("\n", " ")[:240]
        detail = "Model returned no tool calls."
        if content_preview:
            detail = f"{detail} Response preview: {content_preview}"
        io.append_activity(active_task.name, detail)

    io.sync_progress(state["tasks"], total_tokens, total_cost)
    execution_ok = successful_tool_calls > 0

    if budget_exceeded:
        print(f"Budget exceeded: ${total_cost:.4f} > ${exec_cfg.budget_limit_usd:.4f}")
        with open(io.journal_path, "a", encoding="utf-8") as f:
            f.write(f"- BUDGET EXCEEDED: ${total_cost:.4f} > ${exec_cfg.budget_limit_usd:.4f}\n")
        return {
            "exit_code": 1,
            "last_execution_ok": execution_ok,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        }

    if cfg.operation_mode == OperationalMode.VIBE:
        if not execution_ok:
            return {
                "exit_code": 1,
                "last_execution_ok": False,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
            }
        io.mark_task_completed(active_task.id)
        print("Vibe mode enabled: marked task complete without running tests.")
        print(io.snapshot_state(f"Spec-Gate state: completed {active_task.name}"))
        return {
            "exit_code": 0,
            "last_execution_ok": execution_ok,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        }

    return {
        "exit_code": 0 if execution_ok else 1,
        "last_execution_ok": execution_ok,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }


def tester_node(state: SpecGateState):
    """
    QA node, run tests
    """
    active_task = next(t for t in state["tasks"] if t.id == state["current_task_id"])
    retry_counts = dict(state.get("retry_counts", {}))
    if not state.get("last_execution_ok", False):
        retry_counts[active_task.id] = retry_counts.get(active_task.id, 0) + 1
        test_output = "Executor did not complete any successful tool calls."
        print(test_output)
        io.append_activity(active_task.name, test_output)
        with open(io.journal_path, "a", encoding="utf-8") as f:
            f.write(f"- EXECUTION FAILED: {test_output}\n")
        return {
            "exit_code": 1,
            "last_execution_ok": False,
            "last_test_output": test_output,
            "retry_counts": retry_counts,
        }

    try:
        test_cmd = active_task.test_cmd or cfg.qa_settings.test_runner
        print(f"Running tests: {test_cmd}")
        io.append_activity(active_task.name, f"Running tests: `{test_cmd}`.")
        result = subprocess.run(
            shlex.split(test_cmd),
            cwd=cfg.work_dir,
            capture_output=True,
            text=True,
        )
        exit_code = result.returncode
        test_output = (result.stdout + "\n" + result.stderr).strip()
        
        if exit_code == 0:
            print("Tests Passed!")
            io.append_activity(active_task.name, "Tests passed.")
            io.mark_task_completed(active_task.id)
            retry_counts[active_task.id] = 0
            print(io.snapshot_state(f"Spec-Gate state: completed {active_task.name}"))
            # Record Success in Spatial Memory
            spatial_store.record_success(
                wing="core", 
                room=active_task.name, 
                key="latest_pass", 
                data={"status": "passed"}
            )
        else:
            if cfg.operation_mode == OperationalMode.RAPID:
                print("Tests failed, but Rapid mode allows progress with a warning.")
                io.append_activity(active_task.name, "Tests failed, but rapid mode marked the task complete.")
                io.mark_task_completed(active_task.id)
                print(io.snapshot_state(f"Spec-Gate state: rapid-completed {active_task.name}"))
            else:
                retry_counts[active_task.id] = retry_counts.get(active_task.id, 0) + 1
                if retry_counts[active_task.id] >= exec_cfg.max_retries:
                    print("Tests failed and retry limit reached. Halting for human review.")
                    failed_tasks = [
                        task.model_copy(update={"status": TaskStatus.FAILED})
                        if task.id == active_task.id
                        else task
                        for task in state["tasks"]
                    ]
                    io.sync_progress(
                        failed_tasks,
                        state.get("total_tokens", 0),
                        state.get("total_cost", 0.0),
                    )
                    print(io.snapshot_state(f"Spec-Gate state: failed {active_task.name}"))
                else:
                    print("Tests failed. Retrying executor.")

            # Record Pitfall in Spatial Memory
            spatial_store.record_pitfall(
                wing="core", 
                room=active_task.name, 
                key=f"fail_{hash(result.stderr)}", # Unique key for the error
                error="Pytest Failed", 
                context=test_output[-500:] # Pass the last 500 chars of the error log
            )
            
            # Append error to Journal
            with open(io.journal_path, "a", encoding="utf-8") as f:
                f.write(f"- TEST FAILED. Error logged to memory.\n")
                
    except FileNotFoundError:
        print("'pytest' not found in environment. Mocking failure for safety.")
        io.append_activity(active_task.name, "`pytest` was not found in the environment.")
        exit_code = 1
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[active_task.id] = retry_counts.get(active_task.id, 0) + 1

    return {
        "exit_code": exit_code,
        "last_execution_ok": state.get("last_execution_ok", False),
        "last_test_output": locals().get("test_output", ""),
        "retry_counts": retry_counts,
    }

builder = StateGraph(SpecGateState)

builder.add_node("planner", planner_node)
builder.add_node("executor", executor_node)
builder.add_node("tester", tester_node)

builder.set_entry_point("planner")

builder.add_conditional_edges(
    "executor",
    route_after_executor,
    {
        "planner": "planner",
        "tester": "tester"
    }
)

builder.add_conditional_edges(
    "tester",
    route_after_tester,
    {
        "planner": "planner",
        "executor": "executor",
        "end": END
    }
)

builder.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "end": END,
        "executor": "executor"
    }
)

# HITL, interupt before building so human can review the plan
graph = builder.compile(
    checkpointer = memory,
    interrupt_before=["executor"]
)

