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
    focus_test_cmd, failure_output, repo_tree, constraints, files_block, observations.
    
    For feature mode, additional keys: feature_description, acceptance_criteria,
    current_subgoal_index, completed_subgoals.

    Args:
        state: A mapping of context fields to embed in the prompt.

    Returns:
        A single string with sections separated by headers.
    """
    # Check if this is feature mode
    is_feature_mode = state.get('mode') == 'feature'
    
    sections = [
        f"GOAL:\n{state['goal']}\n\n",
    ]
    
    if is_feature_mode:
        # Feature mode sections
        sections.append(f"FEATURE_DESCRIPTION:\n{state.get('feature_description', '')}\n\n")
        
        acceptance_criteria = state.get('acceptance_criteria', [])
        if acceptance_criteria:
            criteria_text = "\n".join(f"  - {c}" for c in acceptance_criteria)
            sections.append(f"ACCEPTANCE_CRITERIA:\n{criteria_text}\n\n")
        
        completed_subgoals = state.get('completed_subgoals', [])
        if completed_subgoals:
            completed_text = "\n".join(f"  ✓ {s}" for s in completed_subgoals)
            sections.append(f"COMPLETED_SUBGOALS:\n{completed_text}\n\n")
        
        current_subgoal = state.get('current_subgoal', '')
        if current_subgoal:
            sections.append(f"CURRENT_SUBGOAL:\n{current_subgoal}\n\n")
    else:
        # Repair mode sections (original behavior)
        sections.extend([
            f"INTENT:\n{state['intent']}\n\n",
            f"SUBGOAL:\n{state['subgoal']}\n\n",
        ])
    
    sections.extend([
        f"TEST_COMMAND:\n{state['test_cmd']}\n\n",
        f"FOCUS_TEST_COMMAND:\n{state['focus_test_cmd']}\n\n",
        f"FAILURE_OUTPUT:\n{_truncate(state['failure_output'], 45000)}\n\n",
        f"REPO_TREE:\n{_truncate(state['repo_tree'], 20000)}\n\n",
        f"CONSTRAINTS:\n{state['constraints']}\n\n",
        f"FILES:\n{state['files_block']}\n",
    ])

    if state.get('action_priors'):
        sections.append(
            f"\nACTION_PRIORS:\n{_truncate(state['action_priors'], 12000)}\n"
        )
    
    # Add observations if present
    if state.get('observations'):
        sections.append(f"\nOBSERVATIONS:\n{_truncate(state['observations'], 30000)}")
    
    return "".join(sections)