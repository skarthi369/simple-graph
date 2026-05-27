import pytest
from simplegraph.engine import SimpleGraph
from simplegraph.hooks import PauseExecution, InfiniteLoopError, Checkpoint

# --- Loop Safety Tests ---

def test_infinite_loop_global_limit():
    graph = SimpleGraph()
    # Cycle setup: A -> B -> A
    graph.add_node("node_a", lambda state: {"steps": state.get("steps", 0) + 1})
    graph.add_node("node_b", lambda state: {"steps": state.get("steps", 0) + 1})
    
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", "node_a")
    graph.set_entry_point("node_a")
    
    # Run with a max_steps of 5
    with pytest.raises(InfiniteLoopError) as exc_info:
        graph.run({"steps": 0}, max_steps=5)
    
    assert "Global cycle limit reached" in str(exc_info.value)

def test_infinite_loop_node_specific_limit():
    graph = SimpleGraph()
    # Cycle setup: A -> B -> A
    graph.add_node("node_a", lambda state: {"steps": state.get("steps", 0) + 1})
    graph.add_node("node_b", lambda state: {"steps": state.get("steps", 0) + 1})
    
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", "node_a")
    graph.set_entry_point("node_a")
    
    # Run with a custom node limit for node_b of 2 visits
    with pytest.raises(InfiniteLoopError) as exc_info:
        graph.run({"steps": 0}, max_steps=50, custom_node_limits={"node_b": 2})
        
    assert "Node execution threshold exceeded" in str(exc_info.value)
    assert "node_b" in str(exc_info.value)

# --- Pause and Resume Tests ---

def pause_node(state):
    if not state.get("approved", False):
        raise PauseExecution("Waiting for human authorization", next_node="resume_node")
    return {"status": "authorized"}

def resume_node(state):
    return {"final_status": "done"}

def test_pause_and_resume_flow():
    graph = SimpleGraph()
    graph.add_node("pause_node", pause_node)
    graph.add_node("resume_node", resume_node)
    graph.add_edge("pause_node", "resume_node")
    graph.set_entry_point("pause_node")
    
    initial_state = {"approved": False}
    
    # Execution should pause
    checkpoint = None
    try:
        graph.run(initial_state)
    except PauseExecution as pe:
        # Create a checkpoint matching the snapshot structure
        checkpoint = Checkpoint(
            state={"approved": False},
            next_node=pe.next_node,
            step_count=1,
            node_visit_counts={"pause_node": 1}
        )
        
    assert checkpoint is not None
    assert checkpoint.next_node == "resume_node"
    
    # Simulate a human reviews, updates state, and serializes/deserializes checkpoint
    checkpoint_json = checkpoint.to_json()
    restored_checkpoint = Checkpoint.from_json(checkpoint_json)
    
    # Set the state value to authorized
    restored_checkpoint.state["approved"] = True
    
    # Resume the graph
    final_state = graph.resume(restored_checkpoint)
    assert final_state["approved"] is True
    assert final_state["final_status"] == "done"
