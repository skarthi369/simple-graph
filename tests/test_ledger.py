import threading
import pytest
from simplegraph.ledger import safe_deepcopy, compute_diff, ImmutableLedger

def test_safe_deepcopy_unpickleable():
    # threading.Lock is famously un-pickleable
    lock = threading.Lock()
    state = {
        "status": "active",
        "lock": lock,
        "nested": {
            "key": "value",
            "lock_nested": lock
        }
    }
    
    copied = safe_deepcopy(state)
    assert copied["status"] == "active"
    assert copied["nested"]["key"] == "value"
    # Verify lock references are shared/copied safely without crash
    assert copied["lock"] is lock
    assert copied["nested"]["lock_nested"] is lock

def test_compute_diff():
    before = {"a": 1, "b": "hello", "c": [1, 2]}
    after = {"b": "world", "c": [1, 2], "d": 4.5}
    
    diff = compute_diff(before, after)
    
    assert "d" in diff["added"]
    assert diff["added"]["d"] == 4.5
    
    assert "a" in diff["deleted"]
    assert diff["deleted"]["a"] == 1
    
    assert "b" in diff["modified"]
    assert diff["modified"]["b"]["old"] == "hello"
    assert diff["modified"]["b"]["new"] == "world"
    
    assert "c" not in diff["modified"]
    assert "c" not in diff["added"]
    assert "c" not in diff["deleted"]

def test_ledger_print_timeline():
    ledger = ImmutableLedger()
    ledger.commit("node_1", {"x": 1}, {"x": 2, "y": "new"})
    ledger.commit("node_2", {"x": 2, "y": "new"}, {"x": 2, "y": "new"}) # No change
    ledger.commit("node_3", {"x": 2, "y": "new"}, {"x": 2}) # Deleted y
    
    # Just verify calling it does not crash
    ledger.print_debug_timeline()
