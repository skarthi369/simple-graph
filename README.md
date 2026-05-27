# SimpleGraph 🕸️

**SimpleGraph** is an ultra-simple, concurrent, transparent, and highly customizable multi-agent orchestration framework for Python. 

Unlike complex, heavy multi-agent libraries that impose mandatory graph compilation steps, specialized custom channels, or state reducers, **SimpleGraph** prioritizes **Absolute Simplicity** and **Zero Cognitive Friction**. It handles multi-agent orchestration using standard Python dictionaries, sequential execution flows, dynamic runtime routing, and robust built-in safeguards.

---

## Key Features

1. ⚡ **Zero-Boilerplate State Management:** Entire state is a standard Python flat dictionary. Agents simply return partial updates, which the core engine merges seamlessly.
2. 🔀 **Dynamic Runtime Routing:** No compilation phase. Flow execution is computed dynamically at runtime using a strict routing priority.
3. 🧵 **Polymorphic Concurrency:** Mixing synchronous and asynchronous agents? SimpleGraph inspects your agent signatures and automatically offloads blocking synchronous nodes to background threads (`asyncio.to_thread`) without blocking the event loop.
4. 🔒 **Thread-Safe Merging:** State updates from background worker threads are consolidated and merged exclusively on the main event loop thread, completely eliminating data write race conditions.
5. 🛡️ **Safe Deep-Copy & Diffing:** The local tracking engine deep-copies state before and after each node run to calculate exact key diffs. It gracefully falls back to reference sharing when un-pickleable objects (like LLM clients, database handles, or thread locks) are stored in the state.
6. 🕵️ **Time-Travel Visual Debugger:** A built-in terminal ledger that records all mutations and renders a gorgeous, colorized timeline showing exactly who mutated what, and when.
7. 💾 **Structured Checkpoints & Pause/Resume:** Interceptor hooks can pause execution and export a full `Checkpoint` object (state + pointer + history metadata), enabling seamless serializable pause-and-resume workflows.
8. 🔄 **Dynamic Loop Protection:** Loop and step thresholds can be configured globally or per-node to safely handle writer-reviewer cycles.

---

## Installation

You can install SimpleGraph locally in editable mode during development:

```bash
pip install -e .
```

---

## Quickstart: Cyclic Math Workflow (Non-LLM)

Below is an elegant, non-LLM cyclic calculation flow:

```python
from simplegraph import SimpleGraph

# 1. Define simple nodes accepting and returning partial state dictionaries
def initiator(state: dict) -> dict:
    return {"number": 10}

def multiplier(state: dict) -> dict:
    return {"number": state["number"] * 2}

def checker(state: dict) -> dict:
    # Use "__next__" to override flow dynamically
    if state["number"] < 50:
        return {"__next__": "multiplier"}
    return {"status": "success", "__next__": None}

# 2. Setup the graph
graph = SimpleGraph()
graph.add_node("initiator", initiator)
graph.add_node("multiplier", multiplier)
graph.add_node("checker", checker)

# Connect static edges
graph.add_edge("initiator", "multiplier")
graph.add_edge("multiplier", "checker")

graph.set_entry_point("initiator")

# 3. Run execution and print the timeline
final_state = graph.run({})
graph.ledger.print_debug_timeline()
```

---

## Advanced: Asynchronous Writer-Reviewer Flow (LLM Client with Locks)

SimpleGraph seamlessly supports complex LLM workflows containing asynchronous routines and un-pickleable objects (e.g. locks, database handles, API clients):

```python
import asyncio
import threading
from simplegraph import SimpleGraph

class MockLLMClient:
    def __init__(self):
        self.lock = threading.Lock()  # Famously uncopyable
    
    def query(self, prompt: str) -> str:
        return "SimpleGraph is an elegant orchestration framework."

async def writer_agent(state: dict) -> dict:
    client = state["llm_client"]
    # ... async call ...
    await asyncio.sleep(0.01)
    return {"draft": client.query("Write essay")}

def reviewer_agent(state: dict) -> dict:
    # Synchronous blocking review logic, auto-offloaded to background thread pool
    draft = state["draft"]
    return {"approved": True, "__next__": None}

async def main():
    graph = SimpleGraph()
    graph.add_node("writer", writer_agent)
    graph.add_node("reviewer", reviewer_agent)
    graph.add_edge("writer", "reviewer")
    graph.set_entry_point("writer")

    initial_state = {
        "llm_client": MockLLMClient(),
        "draft": "",
        "approved": False
    }

    final_state = await graph.run_async(initial_state)
    graph.ledger.print_debug_timeline()

asyncio.run(main())
```

---

## Under the Hood: Routing Precedence

When deciding which node to transition to next, the orchestrator follows this exact priority hierarchy:

1. **Highest:** Override returned in the dictionary payload using the special `__next__` key (e.g., `return {"val": 42, "__next__": "custom_node"}`).
2. **Medium:** Dynamic routing functions registered via `add_conditional_edges("from_node", router_func)`.
3. **Lowest:** Static edges defined with `add_edge("from_node", "to_node")`.

---

## License

This project is licensed under the MIT License.
