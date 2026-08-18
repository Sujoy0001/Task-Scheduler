from typing import Callable

TASK_REGISTRY: dict[str, Callable] = {}

def task(func: Callable) -> Callable:
    """
    Decorator to register a function as a task.
    """
    TASK_REGISTRY[func.__name__] = func
    return func


def get_task(func_name: str) -> Callable:
    if func_name not in TASK_REGISTRY:
        raise ValueError(f"Task '{func_name}' is not registered.")
    return TASK_REGISTRY[func_name]