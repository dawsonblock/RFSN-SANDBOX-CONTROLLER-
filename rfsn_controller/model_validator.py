"""Strict model output validation.

Validates model JSON responses and diffs:
- Schema validation for mode/tool_request/patch
- Diff validation (must be valid unified diff)
- Fallback behavior for invalid output
"""

import re
import json
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ModelOutput:
    """Validated model output."""

    mode: str  # "tool_request", "patch", or "feature_summary"
    requests: Optional[list[Dict[str, Any]]] = None
    diff: Optional[str] = None
    why: Optional[str] = None
    summary: Optional[str] = None
    completion_status: Optional[str] = None
    is_valid: bool = True
    validation_error: Optional[str] = None


class ModelOutputValidator:
    """Validates model output and provides fallback behavior."""

    # Valid unified diff patterns
    DIFF_HEADER_PATTERN = re.compile(r'^diff --git a/')
    HUNK_PATTERN = re.compile(r'^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@')
    FILE_PATTERN = re.compile(r'^--- a/')
    NEW_FILE_PATTERN = re.compile(r'^\+\+\+ b/')

    # Patterns that indicate invalid diffs
    MARKDOWN_FENCE = re.compile(r'^```')
    INVALID_DIFF_PATTERNS = [
        MARKDOWN_FENCE,
        re.compile(r'^# '),  # Markdown heading
        re.compile(r'^\* '),  # Markdown bullet
        re.compile(r'^- '),  # Markdown dash
    ]

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate(self, output: str) -> ModelOutput:
        """Validate model JSON output.

        Args:
            output: Raw JSON string from model.

        Returns:
            ModelOutput with validation results.
        """
        # Try to parse JSON
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to invalid JSON output",
                is_valid=False,
                validation_error=f"Invalid JSON: {e}",
            )

        # Validate schema
        if not isinstance(data, dict):
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to invalid output format",
                is_valid=False,
                validation_error="Output must be a JSON object",
            )

        mode = data.get("mode")

        if mode == "tool_request":
            return self._validate_tool_request(data)
        elif mode == "patch":
            return self._validate_patch(data)
        elif mode == "feature_summary":
            return self._validate_feature_summary(data)
        else:
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to unknown mode",
                is_valid=False,
                validation_error=f"Unknown mode: {mode}",
            )

    def _validate_tool_request(self, data: Dict[str, Any]) -> ModelOutput:
        """Validate tool_request mode output.

        Args:
            data: Parsed JSON data.

        Returns:
            ModelOutput with validation results.
        """
        requests = data.get("requests")
        why = data.get("why", "")

        if not isinstance(requests, list):
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to invalid requests format",
                is_valid=False,
                validation_error="requests must be a list",
            )

        if not requests:
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to empty requests",
                is_valid=False,
                validation_error="requests cannot be empty",
            )

        # Validate each request
        for i, req in enumerate(requests):
            if not isinstance(req, dict):
                return ModelOutput(
                    mode="tool_request",
                    requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                    why="Requesting clarification due to invalid request format",
                    is_valid=False,
                    validation_error=f"Request {i} must be a dict",
                )

            if "tool" not in req:
                return ModelOutput(
                    mode="tool_request",
                    requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                    why="Requesting clarification due to missing tool field",
                    is_valid=False,
                    validation_error=f"Request {i} missing 'tool' field",
                )

        return ModelOutput(
            mode="tool_request",
            requests=requests,
            why=why,
            is_valid=True,
        )

    def _validate_patch(self, data: Dict[str, Any]) -> ModelOutput:
        """Validate patch mode output.

        Args:
            data: Parsed JSON data.

        Returns:
            ModelOutput with validation results.
        """
        diff = data.get("diff", "")

        if not diff or not diff.strip():
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to empty diff",
                is_valid=False,
                validation_error="diff cannot be empty",
            )

        # Validate diff format
        is_valid_diff, error = self._validate_diff_format(diff)
        if not is_valid_diff:
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to invalid diff format",
                is_valid=False,
                validation_error=error,
            )

        return ModelOutput(
            mode="patch",
            diff=diff,
            is_valid=True,
        )

    def _validate_feature_summary(self, data: Dict[str, Any]) -> ModelOutput:
        """Validate feature_summary mode output.

        Args:
            data: Parsed JSON data.

        Returns:
            ModelOutput with validation results.
        """
        summary = data.get("summary", "")
        completion_status = data.get("completion_status", "")

        if not summary or not summary.strip():
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to empty summary",
                is_valid=False,
                validation_error="summary cannot be empty",
            )

        if completion_status not in ["complete", "partial", "blocked", "in_progress"]:
            return ModelOutput(
                mode="tool_request",
                requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
                why="Requesting clarification due to invalid completion_status",
                is_valid=False,
                validation_error=f"Invalid completion_status: {completion_status}",
            )

        return ModelOutput(
            mode="feature_summary",
            summary=summary,
            completion_status=completion_status,
            is_valid=True,
        )

    def _validate_diff_format(self, diff: str) -> Tuple[bool, Optional[str]]:
        """Validate that a string is a valid unified diff.

        Args:
            diff: The diff string to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        lines = diff.strip().split('\n')

        if len(lines) < 2:
            return False, "Diff too short"

        # Check for invalid patterns (markdown fences, etc.)
        for line in lines:
            for pattern in self.INVALID_DIFF_PATTERNS:
                if pattern.match(line):
                    return False, f"Invalid diff pattern: {line.strip()}"

        # Check for valid diff patterns
        has_header = False
        has_hunk = False
        has_file_marker = False

        for line in lines:
            if self.DIFF_HEADER_PATTERN.match(line):
                has_header = True
            if self.HUNK_PATTERN.match(line):
                has_hunk = True
            if self.FILE_PATTERN.match(line) or self.NEW_FILE_PATTERN.match(line):
                has_file_marker = True

        # Must have at least a file marker or hunk
        if not (has_file_marker or has_hunk):
            return False, "Diff missing file markers or hunks"

        return True, None

    def validate_with_retry(
        self,
        output: str,
        max_retries: int = 1,
    ) -> ModelOutput:
        """Validate with retry at temp=0.

        Args:
            output: Raw JSON string from model.
            max_retries: Maximum number of retries.

        Returns:
            ModelOutput with validation results.
        """
        result = self.validate(output)

        if result.is_valid or max_retries == 0:
            return result

        # Retry with fallback
        return ModelOutput(
            mode="tool_request",
            requests=[{"tool": "sandbox.read_file", "args": {"path": "README.md"}}],
            why="Requesting clarification after validation failure",
            is_valid=False,
            validation_error=result.validation_error,
        )


def is_valid_unified_diff(diff: str) -> bool:
    """Quick check if a string looks like a valid unified diff.

    Args:
        diff: The diff string to check.

    Returns:
        True if valid, False otherwise.
    """
    validator = ModelOutputValidator()
    is_valid, _ = validator._validate_diff_format(diff)
    return is_valid
