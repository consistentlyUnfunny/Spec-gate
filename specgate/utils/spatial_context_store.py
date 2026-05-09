from typing import Any

class SpatialContextStore:
    """
    Manages project-specifc memory orgaized by:
    Wing (Domain) > Room (feature) > Locus (Specifc Context)
    """

    def __init__(self, store: Any):
        self.store = store

    def record_success(self, wing: str, room: str, key: str, data: dict[str, Any]):
        """
        Store a record using dict, loi style
        """
        namespace = ("loci", wing, room, "verified")
        self.store.put(namespace, key, data)
    
    def record_pitfall(self, wing: str, room: str, key: str, error: str, context: str):
        """
        Store a negative memory so that it doesn't repeat the same mistake
        """
        namespace = ("loci", wing, room, "pitfalls")
        self.store.put(namespace, key, {
            "error": error,
            "failed_context": context,
            "remediation": "Do not repeat this pattern"
        })

    def get_room_context(self, wing: str, room: str) -> dict[str, list[dict[str, Any]]]:
        """
        Retrieves verified paths and pitfalls
        """
        verified = self.store.search(("loci", wing, room, "verified"))
        pitfalls = self.store.search(("loci", wing, room, "pitfalls"))

        return {
            "verified": [item.value for item in verified],
            "pitfalls": [item.value for item in pitfalls]
        }
