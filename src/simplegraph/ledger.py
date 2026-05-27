import copy
import logging
from typing import Dict, Any, List

logger = logging.getLogger("simplegraph")

def safe_deepcopy(obj: Any) -> Any:
    """
    Safely performs a deep copy of a state dictionary. 
    If a non-pickleable/complex object is encountered, it falls back to shallow reference copy.
    """
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            try:
                new_dict[k] = safe_deepcopy(v)
            except Exception:
                new_dict[k] = v
                logger.warning(
                    f"Failed to deepcopy state key '{k}' of type '{type(v).__name__}'. Falling back to reference sharing."
                )
        return new_dict
    elif isinstance(obj, list):
        new_list = []
        for item in obj:
            try:
                new_list.append(safe_deepcopy(item))
            except Exception:
                new_list.append(item)
        return new_list
    elif isinstance(obj, tuple):
        new_items = []
        for item in obj:
            try:
                new_items.append(safe_deepcopy(item))
            except Exception:
                new_items.append(item)
        return tuple(new_items)
    elif isinstance(obj, set):
        new_set = set()
        for item in obj:
            try:
                new_set.add(safe_deepcopy(item))
            except Exception:
                new_set.add(item)
        return new_set
    else:
        # Atomic types or uncopyable objects
        try:
            return copy.deepcopy(obj)
        except Exception:
            return obj

def compute_diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes key-level differences between two state dicts.
    Returns a dict with: 'added', 'modified', and 'deleted' keys.
    """
    added = {}
    modified = {}
    deleted = {}

    before_keys = set(before.keys())
    after_keys = set(after.keys())

    for k in after_keys - before_keys:
        added[k] = after[k]

    for k in before_keys - after_keys:
        deleted[k] = before[k]

    for k in before_keys & after_keys:
        # Avoid direct equality checks crashing on numpy arrays or complex objects
        try:
            is_equal = before[k] == after[k]
        except Exception:
            is_equal = False

        if not is_equal:
            modified[k] = {
                "old": before[k],
                "new": after[k]
            }

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted
    }

class LedgerRecord:
    """A record representing one node execution step in the graph history."""
    def __init__(self, step: int, node_name: str, state_before: Dict[str, Any], state_after: Dict[str, Any]):
        self.step = step
        self.node_name = node_name
        # Caller (engine) already passes isolated safe_deepcopy snapshots — no re-copy needed here.
        self.state_before = state_before
        self.state_after = state_after
        self.diff = compute_diff(self.state_before, self.state_after)

class ImmutableLedger:
    """An execution ledger that tracks and stores state changes immutably."""
    def __init__(self):
        self.records: List[LedgerRecord] = []

    def commit(self, node_name: str, state_before: Dict[str, Any], state_after: Dict[str, Any]):
        """Commit a new step and its corresponding state change to the ledger."""
        step = len(self.records) + 1
        record = LedgerRecord(step, node_name, state_before, state_after)
        self.records.append(record)

    def print_debug_timeline(self):
        """Prints a gorgeous, visual step-by-step debugger timeline showing state mutations."""
        # ANSI Escape Codes for stunning color coding
        C_RESET = "\033[0m"
        C_HEADER = "\033[95m\033[1m"
        C_NODE = "\033[96m\033[1m"
        C_ADD = "\033[92m"  # Green
        C_MOD = "\033[93m"  # Yellow
        C_DEL = "\033[91m"  # Red
        C_MUTED = "\033[90m" # Gray
        C_BORDER = "\033[35m" # Magenta

        print("\n" + C_BORDER + "=" * 80 + C_RESET)
        print(C_HEADER + "   SIMPLEGRAPH TIME-TRAVEL VISUAL DEBUGGER TIMELINE" + C_RESET)
        print(C_BORDER + "=" * 80 + C_RESET)

        if not self.records:
            print(C_MUTED + "  No records registered in the ledger yet." + C_RESET)
            print(C_BORDER + "=" * 80 + C_RESET)
            return

        for record in self.records:
            print(f"\n {C_BORDER}[Step {record.step}]{C_RESET} Agent: {C_NODE}{record.node_name}{C_RESET}")
            print(C_MUTED + "  " + "-" * 76 + C_RESET)

            diff = record.diff
            has_changes = False

            if diff["added"]:
                has_changes = True
                for k, v in diff["added"].items():
                    print(f"    {C_ADD}[+] [ADDED]    {k:<18} -> {repr(v)}{C_RESET}")

            if diff["modified"]:
                has_changes = True
                for k, change in diff["modified"].items():
                    print(f"    {C_MOD}[~] [MODIFIED] {k:<18} -> Old: {repr(change['old'])}\n                       -> New: {repr(change['new'])}{C_RESET}")

            if diff["deleted"]:
                has_changes = True
                for k, v in diff["deleted"].items():
                    print(f"    {C_DEL}[-] [DELETED]  {k:<18} -> {repr(v)}{C_RESET}")

            if not has_changes:
                print(C_MUTED + "    (No state mutations detected)" + C_RESET)

        print("\n" + C_BORDER + "=" * 80 + C_RESET + "\n")
