from langgraph.store.memory import InMemoryStore

from specgate.utils.spatial_context_store import SpatialContextStore


def test_spatial_context_store_reads_verified_and_pitfalls():
    store = SpatialContextStore(InMemoryStore())

    store.record_success("core", "Task", "ok", {"status": "passed"})
    store.record_pitfall("core", "Task", "fail", "Pytest Failed", "assert false")

    context = store.get_room_context("core", "Task")

    assert context["verified"] == [{"status": "passed"}]
    assert context["pitfalls"] == [
        {
            "error": "Pytest Failed",
            "failed_context": "assert false",
            "remediation": "Do not repeat this pattern",
        }
    ]
