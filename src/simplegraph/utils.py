import inspect
from typing import Callable, Any

def is_async_callable(func: Callable[..., Any]) -> bool:
    """
    Checks if a callable is an asynchronous coroutine function.
    Handles class methods, nested functions, and __call__ callables.
    """
    if inspect.iscoroutinefunction(func):
        return True
    if hasattr(func, "__call__") and inspect.iscoroutinefunction(func.__call__):
        return True
    return False

def validate_node_signature(func: Callable[..., Any], name: str):
    """
    Validates that a node function accepts at least one parameter (the state dict).
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    
    if len(params) == 0:
        raise ValueError(
            f"Node '{name}' must accept at least one argument representing the state dictionary."
        )
