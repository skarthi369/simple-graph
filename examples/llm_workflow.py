import sys
import os
import asyncio
import threading

# Add src to python path to run without publishing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from simplegraph import SimpleGraph

# --- Mock Complex / Non-Pickleable Objects ---

class MockLLMClient:
    """Simulates a complex LLM client with uncopyable attributes like thread locks or network handles."""
    def __init__(self):
        self.lock = threading.Lock()
        self.socket_mock = "socket_active_connection"

    def query(self, prompt: str) -> str:
        # Mocking LLM generation response
        if "review" in prompt.lower():
            if "excellent" in prompt:
                return "APPROVED"
            return "Needs more depth. Add info about state checkpoints and thread safety."
        else:
            if "excellent" in prompt.lower():
                return "SimpleGraph is an excellent, ultra-simple Python library for multi-agent workflows."
            return "SimpleGraph is an ultra-simple Python library for multi-agent workflows."

# --- Node/Agent Functions ---

async def async_writer(state: dict) -> dict:
    """Asynchronous Writer Agent."""
    client = state["llm_client"]
    feedback = state.get("reviewer_feedback", "None")
    
    print("[Writer Agent] Writing essay content...")
    await asyncio.sleep(0.05) # Async IO simulation
    
    # Check if we have received feedback previously
    if "checkpoint" in feedback.lower() or "depth" in feedback.lower():
        prompt = "Write an excellent draft about SimpleGraph."
    else:
        prompt = "Write an essay about SimpleGraph."
        
    content = client.query(prompt)
    
    return {
        "essay_content": content,
        "history": state.get("history", []) + ["Writer updated draft."]
    }

def sync_reviewer(state: dict) -> dict:
    """Synchronous Reviewer Agent (automatically offloaded to background thread)."""
    client = state["llm_client"]
    content = state.get("essay_content", "")
    
    print("[Reviewer Agent] Reviewing draft (Running synchronously on background thread)...")
    
    # We query the mock LLM client
    prompt = f"Review this draft: '{content}'"
    review_status = client.query(prompt)
    
    if "APPROVED" in review_status:
        return {
            "approved": True,
            "reviewer_feedback": "Draft is approved!",
            "__next__": None # End of flow
        }
    else:
        # Loop back to writer with feedback
        return {
            "approved": False,
            "reviewer_feedback": "Review: Add more depth about state checkpoints.",
            "__next__": "writer"
        }

# --- Orchestrating the Async Workflow ---

async def main():
    graph = SimpleGraph()
    
    # Register sync and async agents
    graph.add_node("writer", async_writer)
    graph.add_node("reviewer", sync_reviewer)
    
    # Configure routing
    # 'writer' transitions statically to 'reviewer'
    graph.add_edge("writer", "reviewer")
    # 'reviewer' dynamically transitions based on its returned "__next__" key
    
    graph.set_entry_point("writer")
    
    # Create the state containing non-pickleable LLM Client and a thread Lock
    initial_state = {
        "llm_client": MockLLMClient(),
        "state_mutex": threading.Lock(), # This would crash regular deepcopy
        "approved": False
    }
    
    print("\n>>> Executing Polymorphic Multi-Agent Graph asynchronously...")
    final_state = await graph.run_async(initial_state)
    
    # Print ledger timeline
    graph.ledger.print_debug_timeline()
    
    print("Final State Content:", final_state.get("essay_content"))
    print("Approval Status:", final_state.get("reviewer_feedback"))

if __name__ == "__main__":
    asyncio.run(main())
