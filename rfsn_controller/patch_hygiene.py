"""Patch hygiene gates for quality control.

Ensures patches meet quality standards before acceptance:
- Max lines changed
- Max files changed
- Forbidden directories
- Forbidden file patterns
- Test deletion protection
- Skip pattern detection
"""

import re
from typing import List, Set, Tuple, Optional


class PatchHygieneConfig:
    """Configuration for patch hygiene gates."""
    
    def __init__(
        self,
        max_lines_changed: int = 200,
        max_files_changed: int = 5,
        forbidden_dirs: Optional[Set[str]] = None,
        forbidden_file_patterns: Optional[Set[str]] = None,
        allow_test_deletion: bool = False,
    ):
        self.max_lines_changed = max_lines_changed
        self.max_files_changed = max_files_changed
        self.forbidden_dirs = forbidden_dirs or self._default_forbidden_dirs()
        self.forbidden_file_patterns = forbidden_file_patterns or self._default_forbidden_patterns()
        self.allow_test_deletion = allow_test_deletion
    
    @staticmethod
    def _default_forbidden_dirs() -> Set[str]:
        """Default directories that should never be modified."""
        return {
            'vendor/',
            'third_party/',
            'node_modules/',
            '.git/',
            '__pycache__/',
            '.venv/',
            'venv/',
            'env/',
            '.env',
            '.idea/',
            '.vscode/',
            'dist/',
            'build/',
            'target/',
            'bin/',
            'obj/',
        }
    
    @staticmethod
    def _default_forbidden_patterns() -> Set[str]:
        """Default file patterns that should never be modified."""
        return {
            'package-lock.json',
            'yarn.lock',
            'pnpm-lock.yaml',
            'poetry.lock',
            'Pipfile.lock',
            'requirements.lock',
            '*.lock',
            '.env',
            '.env.*',
            '*.key',
            '*.pem',
            'id_rsa',
            'id_ed25519',
            'secrets.yml',
            'config/secrets',
        }


class PatchHygieneResult:
    """Result of patch hygiene validation."""
    
    def __init__(self, is_valid: bool, violations: List[str]):
        self.is_valid = is_valid
        self.violations = violations
    
    def __bool__(self):
        return self.is_valid


def validate_patch_hygiene(
    diff: str,
    config: Optional[PatchHygieneConfig] = None,
) -> PatchHygieneResult:
    """Validate a patch against hygiene gates.

    Args:
        diff: The git diff to validate.
        config: Hygiene configuration (uses defaults if None).

    Returns:
        PatchHygieneResult with validation status and violations.
    """
    if config is None:
        config = PatchHygieneConfig()
    
    violations = []
    
    # Parse diff to extract changed files and line counts
    files_changed, lines_added, lines_removed = _parse_diff(diff)
    
    # Check max files changed
    if len(files_changed) > config.max_files_changed:
        violations.append(
            f"Too many files changed: {len(files_changed)} > {config.max_files_changed}"
        )
    
    # Check max lines changed
    total_lines = lines_added + lines_removed
    if total_lines > config.max_lines_changed:
        violations.append(
            f"Too many lines changed: {total_lines} > {config.max_lines_changed}"
        )
    
    # Check forbidden directories
    for filepath in files_changed:
        for forbidden_dir in config.forbidden_dirs:
            if filepath.startswith(forbidden_dir):
                violations.append(f"Cannot modify files in {forbidden_dir}: {filepath}")
    
    # Check forbidden file patterns
    for filepath in files_changed:
        filename = filepath.split('/')[-1]
        for pattern in config.forbidden_file_patterns:
            if pattern.startswith('*'):
                # Wildcard pattern
                if filename.endswith(pattern[1:]):
                    violations.append(f"Cannot modify file matching pattern {pattern}: {filepath}")
            elif pattern == filename or filepath == pattern:
                violations.append(f"Cannot modify file: {filepath}")
    
    # Check for test deletion
    if not config.allow_test_deletion:
        for filepath in files_changed:
            if _is_test_file(filepath):
                # Check if file was deleted (diff starts with "deleted file")
                if f"deleted file mode 100644 {filepath}" in diff or \
                   f"deleted file mode 100755 {filepath}" in diff:
                    violations.append(f"Cannot delete test file: {filepath}")
    
    # Check for skip patterns in modified files
    skip_patterns = [
        r'@pytest\.mark\.skip',
        r'@pytest\.mark\.xfail',
        r'@unittest\.skip',
        r'@unittest\.skipIf',
        r'@unittest\.skipUnless',
    ]
    
    for filepath in files_changed:
        if _is_test_file(filepath):
            for pattern in skip_patterns:
                if re.search(pattern, diff):
                    violations.append(
                        f"Test skip pattern detected in {filepath}: {pattern}"
                    )
    
    # Check for debug prints
    debug_patterns = [
        r'print\([\'"]debug',
        r'print\([\'"]DEBUG',
        r'print\([\'"]XXX',
        r'pprint\(',
        r'pdb\.set_trace',
        r'breakpoint\(',
    ]
    
    for pattern in debug_patterns:
        if re.search(pattern, diff):
            violations.append(f"Debug pattern detected: {pattern}")
    
    return PatchHygieneResult(len(violations) == 0, violations)


def _parse_diff(diff: str) -> Tuple[Set[str], int, int]:
    """Parse a git diff to extract changed files and line counts.

    Args:
        diff: The git diff string.

    Returns:
        (files_changed, lines_added, lines_removed) tuple.
    """
    files_changed = set()
    lines_added = 0
    lines_removed = 0
    
    for line in diff.split('\n'):
        if line.startswith('+++ b/') or line.startswith('--- a/'):
            # Extract file path
            parts = line.split('/')
            if len(parts) > 2:
                filepath = '/'.join(parts[2:])
                files_changed.add(filepath)
        elif line.startswith('+') and not line.startswith('+++'):
            lines_added += 1
        elif line.startswith('-') and not line.startswith('---'):
            lines_removed += 1
    
    return files_changed, lines_added, lines_removed


def _is_test_file(filepath: str) -> bool:
    """Check if a file is a test file.

    Args:
        filepath: The file path.

    Returns:
        True if this is a test file.
    """
    filename = filepath.lower()
    return (
        filename.startswith('test_') or
        filename.endswith('_test.py') or
        filename.endswith('_test.ts') or
        filename.endswith('_test.js') or
        filename.endswith('.test.py') or
        filename.endswith('.test.ts') or
        filename.endswith('.test.js') or
        '/test/' in filepath or
        '/tests/' in filepath
    )
