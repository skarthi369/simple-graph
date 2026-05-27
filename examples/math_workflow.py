import sys
import os

# Add src to python path to run without publishing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from simplegraph import SimpleGraph

# --- Nodes ---

def initiator(state: dict) -> dict:
    print("[Initiator] Initializing calculation...")
    return {"number": 10, "iterations": 0}

def multiplier(state: dict) -> dict:
    num = state["number"]
    print(f"[Multiplier] Doubling {num}...")
    return {
        "number": num * 2,
        "iterations": state["iterations"] + 1
    }

def checker(state: dict) -> dict:
    num = state["number"]
    print(f"[Checker] Validating current number {num}...")
    if num < 50:
        # Loop back to multiplier
        print("[Checker] Number is below 50, triggering another multiplication turn.")
        return {"__next__": "multiplier"}
    else:
        print("[Checker] Target value achieved!")
        return {"status": "success", "__next__": None}

# --- Graph Orchestration ---

def main():
    graph = SimpleGraph()
    
    # 1. Register agents/nodes
    graph.add_node("initiator", initiator)
    graph.add_node("multiplier", multiplier)
    graph.add_node("checker", checker)
    
    # 2. Configure routing
    # 'initiator' goes directly to 'multiplier'
    graph.add_edge("initiator", "multiplier")
    
    # 'multiplier' goes directly to 'checker'
    graph.add_edge("multiplier", "checker")
    
    # 'checker' has dynamic routing (loops back to multiplier if < 50, else stops)
    # The engine resolves checker's "__next__" return over standard edges, so we don't need static edge for checker!
    
    # Set starting node
    graph.set_entry_point("initiator")
    
    # Run the graph synchronously
    initial_state = {}
    print("\n>>> Running SimpleGraph workflow...")
    final_state = graph.run(initial_state)
    
    # 3. Print the stunning, immutable debug ledger timeline!
    graph.ledger.print_debug_timeline()
    
    print("Final State Result:", final_state)

if __name__ == "__main__":
    main()
