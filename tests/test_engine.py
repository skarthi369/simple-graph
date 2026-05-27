import asyncio
import time
import pytest
from simplegraph.engine import SimpleGraph
from simplegraph.hooks import Checkpoint, PauseExecution

# --- Test Node Definitions ---

def sync_blocking_node(state):
    # Simulate blocking call (like network SDK or disk I/O)
    time.sleep(0.05)
    return {"val": state.get("val", 0) + 10}

async def async_node(state):
    await asyncio.sleep(0.01)
    return {"val": state.get("val", 0) + 5}

# --- Synchronous & Asynchronous Polymorphism Tests ---

def test_sync_execution():
    graph = SimpleGraph()
    graph.add_node("step1", sync_blocking_node)
    graph.set_entry_point("step1")

    result = graph.run({"val": 5})
    assert result["val"] == 15

@pytest.mark.asyncio
async def test_async_polymorphic_execution():
    graph = SimpleGraph()
    # Register both sync and async nodes
    graph.add_node("sync_node", sync_blocking_node)
    graph.add_node("async_node", async_node)

    graph.add_edge("sync_node", "async_node")
    graph.set_entry_point("sync_node")

    # Run async loop
    result = await graph.run_async({"val": 100})
    # sync_node adds 10, async_node adds 5 -> total 115
    assert result["val"] == 115

# --- Routing Precedence Tests ---

def test_routing_precedence():
    graph = SimpleGraph()

    graph.add_node("start", lambda state: {"__next__": "priority_node"})
    graph.add_node("priority_node", lambda state: {"status": "reached_priority"})
    graph.add_node("router_node", lambda state: {"status": "reached_router"})
    graph.add_node("static_node", lambda state: {"status": "reached_static"})

    graph.add_conditional_edges("start", lambda state: "router_node")
    graph.add_edge("start", "static_node")
    graph.set_entry_point("start")

    result = graph.run({})
    assert result["status"] == "reached_priority"

def test_routing_precedence_medium_priority():
    graph = SimpleGraph()

    graph.add_node("start", lambda state: {"status": "started"})
    graph.add_node("router_node", lambda state: {"status": "reached_router"})
    graph.add_node("static_node", lambda state: {"status": "reached_static"})

    graph.add_conditional_edges("start", lambda state: "router_node")
    graph.add_edge("start", "static_node")
    graph.set_entry_point("start")

    result = graph.run({})
    assert result["status"] == "reached_router"

def test_routing_precedence_lowest_priority():
    graph = SimpleGraph()

    graph.add_node("start", lambda state: {"status": "started"})
    graph.add_node("static_node", lambda state: {"status": "reached_static"})

    graph.add_edge("start", "static_node")
    graph.set_entry_point("start")

    result = graph.run({})
    assert result["status"] == "reached_static"

# --- Fix 5a: on_node_start and on_node_end hooks are called ---

def test_lifecycle_hooks_called():
    graph = SimpleGraph()
    graph.add_node("step1", lambda state: {"x": 1})
    graph.add_node("step2", lambda state: {"x": 2})
    graph.add_edge("step1", "step2")
    graph.set_entry_point("step1")

    start_log = []
    end_log = []

    graph.register_on_node_start(lambda name, state: start_log.append(name))
    graph.register_on_node_end(lambda name, state, updates, diff: end_log.append(name))

    graph.run({})

    # Both nodes must have had their start and end hooks called
    assert start_log == ["step1", "step2"]
    assert end_log == ["step1", "step2"]

# --- Fix 5b: resume_async works from a checkpoint ---

@pytest.mark.asyncio
async def test_async_resume_from_checkpoint():
    graph = SimpleGraph()

    async def first_node(state):
        return {"phase": "first_done"}

    async def second_node(state):
        return {"phase": "second_done"}

    graph.add_node("first_node", first_node)
    graph.add_node("second_node", second_node)
    graph.add_edge("first_node", "second_node")
    graph.set_entry_point("first_node")

    # Simulate a mid-flight checkpoint — as if execution paused after first_node
    checkpoint = Checkpoint(
        state={"phase": "first_done"},
        next_node="second_node",
        step_count=1,
        node_visit_counts={"first_node": 1}
    )

    # Resume from the checkpoint — should only run second_node
    result = await graph.resume_async(checkpoint)
    assert result["phase"] == "second_done"
    # Ledger should only have 1 record (second_node only ran)
    assert len(graph.ledger.records) == 1
    assert graph.ledger.records[0].node_name == "second_node"

# --- Fix 5c: Unregistered node name raises ValueError ---

def test_unregistered_node_raises_error():
    graph = SimpleGraph()
    # Edge references "ghost_node" which is never registered
    graph.add_node("start", lambda state: {"__next__": "ghost_node"})
    graph.set_entry_point("start")

    with pytest.raises(ValueError, match="ghost_node"):
        graph.run({})
