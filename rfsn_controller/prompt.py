"""Helpers for constructing model input strings."""

from typing import Dict, Any


def _truncate(s: str, n: int) -> str:
    """Truncate a string to at most n characters, appending a marker if truncated."""
    if not s:
        return ""
    return s if len(s) <= n else s[:n] + "\n...[truncated]..."


def build_model_input(state: Dict[str, Any]) -> str:
    """Build a formatted model input string from the controller state.

    The state dictionary should contain keys: goal, intent, subgoal, test_cmd,
    focus_test_cmd, failure_output, repo_tree, constraints, files_block.

    Args:
        state: A mapping of context fields to embed in the prompt.

    Returns:
        A single string with sections separated by headers.
    """
    return (
        f"GOAL:\n{state['goal']}\n\n"
        f"INTENT:\n{state['intent']}\n\n"
        f"SUBGOAL:\n{state['subgoal']}\n\n"
        f"TEST_COMMAND:\n{state['test_cmd']}\n\n"
        f"FOCUS_TEST_COMMAND:\n{state['focus_test_cmd']}\n\n"
        f"FAILURE_OUTPUT:\n{_truncate(state['failure_output'], 45000)}\n\n"
        f"REPO_TREE:\n{_truncate(state['repo_tree'], 20000)}\n\n"
        f"CONSTRAINTS:\n{state['constraints']}\n\n"
        f"FILES:\n{state['files_block']}\n"
    )