import sys 
from pathlib import Path

from specgate.graph import graph
from specgate.state import SpecGateState

def print_header():
    """
    Prints CLI header for program
    """
    print("="*60)
    print("Spec-gate Initialized")
    print("="*60)

def handle_interruption(state: SpecGateState) -> bool:
    """
    Handles HITL interaction between pauses before the executor node
    """
    current_task_id = state.get("current_task_id", -1)
    if current_task_id == -1:
        print("All task completed")
        return False
    
    tasks = state.get("tasks", [])
    active_task = next((t for t in tasks if t.id == current_task_id), None)

    if not active_task:
        print(f"\nWarning: Task ID {current_task_id} not found in state")
        return False
    
    # present the plan
    print("\n" + "="*40)
    print("APPROVAL REQUIRED")
    print("="*40)
    print(f"Task: {active_task.name}")
    print(f"Description: {active_task.description}")
    print("="*40)

    while True:
        user_input = input("Proceed with execution? (y/n/exit): ").strip().lower()
        if user_input in ['y', 'yes']:
            return True
        elif user_input in ['n', 'no']:
            return False
        elif user_input == 'exit':
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid input. PLease type 'y', 'n', or 'exit'")
    

def main():
    print_header()

    initial_state = SpecGateState(
        project_root=".",
        spec_path="SPEC.md",
        tasks=[],
        current_task_id=-1,
        last_spec_hash="",
        journal_tail="",
        last_test_output="",
        exit_code=0,
        retry_counts={},
        active_context=[],
        total_tokens=0,
        total_cost=0.0,
        is_approved=False
    )

    # a static thread_id for SQLite checkpointer so it remembers the state across reboots.
    config = {"configurable": {"thread_id": "project-specgate-dev"}}

    # check if we're continuing from a previous interruption
    current_state_snapshot = graph.get_state(config)

    # not starting from snapshot
    if not current_state_snapshot.next:
        print("\nStarting new orchestration loop...")
        try:
            for event in graph.stream(initial_state, config):
                for node_name, state_update in event.items():
                    # no printing here because the nods have logging already
                    pass
        except Exception as e:
            print(f"\nFatal Error during Execution: {e}")
            sys.exit(1)

    while True:
        state_snapshot = graph.get_state(config)
        
        # If there's no next node, the graph reached the END node.
        if not state_snapshot.next:
            print("\n🎉 Spec-Gate execution completed successfully.")
            break
            
        next_node = state_snapshot.next[0]
        
        if next_node == "executor":
            # We are paused before the executor. Ask the human.
            approved = handle_interruption(state_snapshot.values)
            
            if approved:
                print("\n⚙️ Resuming execution...")
                for event in graph.stream(None, config):
                    pass 
            else:
                print("Exiting interactive loop.")
                break
        else:
             for event in graph.stream(None, config):
                 pass


if __name__ == "__main__":
    if not Path("SPEC.md").exists():
        print("Creating default SPEC.md file...")
        Path("SPEC.md").write_text("# Project Specification\n\n- [ ] Task 1: Initialize Project\n", encoding="utf-8")
        
    main()
