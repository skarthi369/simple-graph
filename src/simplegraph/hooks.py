import json
import datetime
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("simplegraph")

class InfiniteLoopError(RuntimeError):
    """Raised when an execution cycle or loop threshold is exceeded to prevent infinite cycles."""
    pass

class PauseExecution(Exception):
    """Raised by interceptor hooks or node functions to gracefully pause the execution graph."""
    def __init__(self, message: str = "Execution paused", next_node: Optional[str] = None):
        super().__init__(message)
        self.next_node = next_node

class Checkpoint:
    """
    A structured snapshot representing the exact execution state of a SimpleGraph.
    Includes the application state, execution pointer (next node), and loop-protection counters.
    """
    def __init__(
        self,
        state: Dict[str, Any],
        next_node: Optional[str],
        step_count: int = 0,
        node_visit_counts: Optional[Dict[str, int]] = None,
        created_at: Optional[str] = None
    ):
        self.state = state
        self.next_node = next_node
        self.step_count = step_count
        self.node_visit_counts = node_visit_counts or {}
        # ISO 8601 timestamp for ordering and debugging multiple checkpoints
        self.created_at = created_at or datetime.datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the checkpoint to a dictionary. Unserializable state elements are converted to strings."""
        serialized_state = {}
        for k, v in self.state.items():
            try:
                # Try a quick test serialization
                json.dumps({k: v})
                serialized_state[k] = v
            except (TypeError, OverflowError):
                # Fallback to string representations for non-serializable fields
                serialized_state[k] = f"<Unserializable: {type(v).__name__}>"
                logger.warning(
                    f"State key '{k}' of type '{type(v).__name__}' is not JSON serializable and was cast to string in checkpoint."
                )

        return {
            "state": serialized_state,
            "next_node": self.next_node,
            "step_count": self.step_count,
            "node_visit_counts": self.node_visit_counts,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Reconstructs a Checkpoint object from a dictionary."""
        return cls(
            state=data.get("state", {}),
            next_node=data.get("next_node"),
            step_count=data.get("step_count", 0),
            node_visit_counts=data.get("node_visit_counts", {}),
            created_at=data.get("created_at")
        )

    def to_json(self) -> str:
        """Converts checkpoint to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Checkpoint":
        """Creates a checkpoint from a JSON string."""
        return cls.from_dict(json.loads(json_str))
