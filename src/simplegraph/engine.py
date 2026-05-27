import asyncio
import logging
from typing import Dict, Any, Callable, Optional, Union, List

from .ledger import ImmutableLedger, safe_deepcopy, compute_diff
from .hooks import Checkpoint, InfiniteLoopError, PauseExecution
from .utils import is_async_callable, validate_node_signature

logger = logging.getLogger("simplegraph")

class SimpleGraph:
    """
    Core orchestrator engine for the SimpleGraph multi-agent framework.
    Maintains a flat state dictionary, processes partial updates, inspects signatures
    for asynchronous/synchronous thread offloading, and features precise loop protection.
    """
    def __init__(self):
        self.nodes: Dict[str, Callable[[Dict[str, Any]], Union[Dict[str, Any], None]]] = {}
        self.edges: Dict[str, str] = {}
        self.routers: Dict[str, Callable[[Dict[str, Any]], str]] = {}
        self.entry_point: Optional[str] = None
        self.ledger = ImmutableLedger()
        
        # Interceptor hooks
        self._start_hooks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._end_hooks: List[Callable[[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]], None]] = []

    def add_node(self, name: str, func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> "SimpleGraph":
        """Registers a node function under a specific name."""
        validate_node_signature(func, name)
        self.nodes[name] = func
        return self

    def add_edge(self, from_node: str, to_node: str) -> "SimpleGraph":
        """Registers a static transition edge from one node to another."""
        self.edges[from_node] = to_node
        return self

    def add_conditional_edges(self, from_node: str, router_func: Callable[[Dict[str, Any]], str]) -> "SimpleGraph":
        """Registers a dynamic router function to determine the next transition from a node."""
        self.routers[from_node] = router_func
        return self

    def set_entry_point(self, name: str) -> "SimpleGraph":
        """Sets the starting node for execution."""
        if name not in self.nodes:
            raise ValueError(f"Entry point node '{name}' is not registered in the graph.")
        self.entry_point = name
        return self

    def register_on_node_start(self, hook: Callable[[str, Dict[str, Any]], None]) -> "SimpleGraph":
        """Registers a lifecycle hook called before a node starts."""
        self._start_hooks.append(hook)
        return self

    def register_on_node_end(self, hook: Callable[[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]], None]) -> "SimpleGraph":
        """Registers a lifecycle hook called after a node completes."""
        self._end_hooks.append(hook)
        return self

    def _resolve_next_node(self, current_node: str, updates: Dict[str, Any], state: Dict[str, Any]) -> Optional[str]:
        """
        Determines the next node to execute based on a strict priority hierarchy:
        1. Highest: Node-returned overrides via "__next__".
        2. Medium: Dynamic registered routing functions.
        3. Lowest: Static edges.
        """
        # Priority 1: Check for explicit route returned in updates
        if updates and "__next__" in updates:
            return updates["__next__"]

        # Priority 2: Check for registered router function
        if current_node in self.routers:
            return self.routers[current_node](state)

        # Priority 3: Check for static edge
        if current_node in self.edges:
            return self.edges[current_node]

        return None

    def _check_loop_limits(
        self,
        step_count: int,
        visit_counts: Dict[str, int],
        current_node: str,
        max_steps: int,
        custom_node_limits: Optional[Dict[str, int]]
    ):
        """Validates loop safety. Raises InfiniteLoopError if limits are breached."""
        if step_count > max_steps:
            raise InfiniteLoopError(
                f"Global cycle limit reached! Executed {step_count} total steps, exceeding limit of {max_steps}."
            )

        limit = (custom_node_limits or {}).get(current_node, 100) # Default to 100 visits per node to prevent obvious locks
        if visit_counts.get(current_node, 0) > limit:
            raise InfiniteLoopError(
                f"Node execution threshold exceeded! Node '{current_node}' has been visited {visit_counts[current_node]} times (limit: {limit})."
            )

    # --- Synchronous Execution API ---

    def run(self, initial_state: Dict[str, Any], max_steps: int = 100, custom_node_limits: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Synchronously executes the graph starting from the entry point."""
        if not self.entry_point:
            raise ValueError("No entry point set for the graph. Use set_entry_point() first.")
        
        state = safe_deepcopy(initial_state)
        current_node = self.entry_point
        step_count = 0
        node_visit_counts = {}

        return self._run_loop_sync(state, current_node, step_count, node_visit_counts, max_steps, custom_node_limits)

    def resume(self, checkpoint: Checkpoint, max_steps: int = 100, custom_node_limits: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Resumes a paused synchronous execution from a structured Checkpoint."""
        if not checkpoint.next_node:
            logger.info("Checkpoint has no next node. Execution already finished.")
            return checkpoint.state

        state = safe_deepcopy(checkpoint.state)
        current_node = checkpoint.next_node
        step_count = checkpoint.step_count
        node_visit_counts = dict(checkpoint.node_visit_counts)

        return self._run_loop_sync(state, current_node, step_count, node_visit_counts, max_steps, custom_node_limits)

    def _run_loop_sync(
        self,
        state: Dict[str, Any],
        current_node: str,
        step_count: int,
        node_visit_counts: Dict[str, int],
        max_steps: int,
        custom_node_limits: Optional[Dict[str, int]]
    ) -> Dict[str, Any]:
        """Underlying synchronous run-loop engine."""
        while current_node:
            node_visit_counts[current_node] = node_visit_counts.get(current_node, 0) + 1
            step_count += 1

            self._check_loop_limits(step_count, node_visit_counts, current_node, max_steps, custom_node_limits)

            node_func = self.nodes.get(current_node)
            if not node_func:
                raise ValueError(f"Node '{current_node}' is referenced but not registered.")

            # Trigger Start Hooks
            for hook in self._start_hooks:
                hook(current_node, state)

            # Capture safe pre-execution state for tracer ledger
            state_before = safe_deepcopy(state)

            try:
                # Synchronous node gets a copy of state to avoid illegal mutations
                updates = node_func(safe_deepcopy(state))
            except PauseExecution as pe:
                # Capture and re-throw, packing execution pointers + auto-built checkpoint
                pe.next_node = pe.next_node or current_node
                pe.checkpoint = self.create_checkpoint(
                    next_node=pe.next_node,
                    state=state,
                    step_count=step_count,
                    node_visit_counts=node_visit_counts
                )
                raise pe

            if updates is None:
                updates = {}

            # Filter metadata/routing keys out of master state updates
            filtered_updates = {k: v for k, v in updates.items() if k != "__next__"}
            
            # Master update is done strictly here on the main execution thread
            state.update(filtered_updates)

            # Commit to tracing ledger
            self.ledger.commit(current_node, state_before, state)

            # Retrieve exact computed diff from the last committed ledger record
            last_record = self.ledger.records[-1]

            # Trigger End Hooks
            for hook in self._end_hooks:
                hook(current_node, state, updates, last_record.diff)

            # Resolve next node
            current_node = self._resolve_next_node(current_node, updates, state)

        return state

    # --- Asynchronous Execution API ---

    async def run_async(self, initial_state: Dict[str, Any], max_steps: int = 100, custom_node_limits: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Asynchronously executes the graph starting from the entry point, supporting concurrent thread offloading."""
        if not self.entry_point:
            raise ValueError("No entry point set for the graph. Use set_entry_point() first.")
        
        state = safe_deepcopy(initial_state)
        current_node = self.entry_point
        step_count = 0
        node_visit_counts = {}

        return await self._run_loop_async(state, current_node, step_count, node_visit_counts, max_steps, custom_node_limits)

    async def resume_async(self, checkpoint: Checkpoint, max_steps: int = 100, custom_node_limits: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Resumes a paused asynchronous execution from a structured Checkpoint."""
        if not checkpoint.next_node:
            logger.info("Checkpoint has no next node. Execution already finished.")
            return checkpoint.state

        state = safe_deepcopy(checkpoint.state)
        current_node = checkpoint.next_node
        step_count = checkpoint.step_count
        node_visit_counts = dict(checkpoint.node_visit_counts)

        return await self._run_loop_async(state, current_node, step_count, node_visit_counts, max_steps, custom_node_limits)

    async def _run_loop_async(
        self,
        state: Dict[str, Any],
        current_node: str,
        step_count: int,
        node_visit_counts: Dict[str, int],
        max_steps: int,
        custom_node_limits: Optional[Dict[str, int]]
    ) -> Dict[str, Any]:
        """Underlying asynchronous run-loop engine."""
        while current_node:
            node_visit_counts[current_node] = node_visit_counts.get(current_node, 0) + 1
            step_count += 1

            self._check_loop_limits(step_count, node_visit_counts, current_node, max_steps, custom_node_limits)

            node_func = self.nodes.get(current_node)
            if not node_func:
                raise ValueError(f"Node '{current_node}' is referenced but not registered.")

            # Trigger Start Hooks
            for hook in self._start_hooks:
                if asyncio.iscoroutinefunction(hook):
                    await hook(current_node, state)
                else:
                    hook(current_node, state)

            # Capture safe pre-execution state for tracer ledger
            state_before = safe_deepcopy(state)

            try:
                # Sync vs Async execution offloading (Polymorphic Concurrency)
                if is_async_callable(node_func):
                    # Async execution
                    updates = await node_func(safe_deepcopy(state))
                else:
                    # Sync execution offloaded to background thread pool
                    # Input state snapshot is passed to ensure thread isolation
                    state_snapshot = safe_deepcopy(state)
                    updates = await asyncio.to_thread(node_func, state_snapshot)
            except PauseExecution as pe:
                # Auto-attach structured checkpoint so callers don't need to build it manually
                pe.next_node = pe.next_node or current_node
                pe.checkpoint = self.create_checkpoint(
                    next_node=pe.next_node,
                    state=state,
                    step_count=step_count,
                    node_visit_counts=node_visit_counts
                )
                raise pe

            if updates is None:
                updates = {}

            # Filter metadata/routing keys out of master state updates
            filtered_updates = {k: v for k, v in updates.items() if k != "__next__"}
            
            # Master update is done strictly here on the main event loop thread (Guarantees Thread-Safety)
            state.update(filtered_updates)

            # Commit to tracing ledger
            self.ledger.commit(current_node, state_before, state)

            # Retrieve exact computed diff from the last committed ledger record
            last_record = self.ledger.records[-1]

            # Trigger End Hooks
            for hook in self._end_hooks:
                if asyncio.iscoroutinefunction(hook):
                    await hook(current_node, state, updates, last_record.diff)
                else:
                    hook(current_node, state, updates, last_record.diff)

            # Resolve next node
            current_node = self._resolve_next_node(current_node, updates, state)

        return state

    def create_checkpoint(self, next_node: Optional[str], state: Dict[str, Any], step_count: int, node_visit_counts: Dict[str, int]) -> Checkpoint:
        """Helper to construct a Checkpoint state snapshot."""
        return Checkpoint(state=state, next_node=next_node, step_count=step_count, node_visit_counts=node_visit_counts)
