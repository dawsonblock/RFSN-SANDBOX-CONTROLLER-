"""Test framework detection and command selection.

Detects test frameworks from project configuration files and provides
appropriate test commands. Handles edge cases like pytest exit code 2
(no tests found).
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

__test__ = False


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    UNTEST = "unittest"
    NOSE = "nose"
    NOX = "nox"
    TOX = "tox"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    GO_TEST = "go_test"
    CARGO_TEST = "cargo_test"
    MVN_TEST = "mvn_test"
    GRADLE_TEST = "gradle_test"
    DOTNET_TEST = "dotnet_test"
    UNKNOWN = "unknown"


@dataclass
class TestDetectionResult:
    """Result of test framework detection."""

    framework: TestFramework
    test_command: str
    config_file: Optional[str] = None
    tests_found: bool = True
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "framework": self.framework.value,
            "test_command": self.test_command,
            "config_file": self.config_file,
            "tests_found": self.tests_found,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class TestDetector:
    """Detects test frameworks and suggests test commands."""

    # Python test patterns
    PYTHON_PATTERNS = {
        "pytest": [
            r"pytest",
            r"py\.test",
            r"python -m pytest",
        ],
        "unittest": [
            r"unittest",
            r"python -m unittest",
        ],
        "nose": [
            r"nosetests",
            r"nose2",
        ],
    }

    # Python config files
    PYTHON_CONFIGS = {
        "pyproject.toml": {
            "pytest": r'\[tool\.pytest\]',
            "unittest": r'\[tool\.unittest\]',
        },
        "setup.cfg": {
            "pytest": r'\[pytest\]',
            "tox": r'\[tox\]',
        },
        "pytest.ini": {
            "pytest": r'\[pytest\]',
        },
        "tox.ini": {
            "tox": r'\[tox\]',
            "pytest": r'\[pytest\]',
        },
        "noxfile.py": {
            "nox": r'nox\.session',
        },
    }

    # Node.js test patterns
    NODE_PATTERNS = {
        "jest": [
            r"jest",
            r"npm test.*jest",
            r"yarn test.*jest",
        ],
        "mocha": [
            r"mocha",
            r"npm test.*mocha",
            r"yarn test.*mocha",
        ],
        "vitest": [
            r"vitest",
            r"npm test.*vitest",
            r"yarn test.*vitest",
        ],
    }

    # Node.js config files
    NODE_CONFIGS = {
        "package.json": {
            "jest": r'"test":\s*".*jest',
            "mocha": r'"test":\s*".*mocha',
            "vitest": r'"test":\s*".*vitest',
        },
        "jest.config.js": {
            "jest": r'module\.exports',
        },
        "vitest.config.js": {
            "vitest": r'defineConfig',
        },
    }

    # Go test patterns
    GO_PATTERNS = {
        "go_test": [
            r"go test",
            r"go test ./\.\.\.",
        ],
    }

    # Rust test patterns
    RUST_PATTERNS = {
        "cargo_test": [
            r"cargo test",
        ],
    }

    # Java test patterns
    JAVA_PATTERNS = {
        "mvn_test": [
            r"mvn test",
            r"mvn surefire:test",
        ],
        "gradle_test": [
            r"gradle test",
            r"./gradlew test",
        ],
    }

    # .NET test patterns
    DOTNET_PATTERNS = {
        "dotnet_test": [
            r"dotnet test",
        ],
    }

    def __init__(self):
        """Initialize the test detector."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for each language."""
        self.python_patterns = {
            fw: [re.compile(p, re.IGNORECASE) for p in patterns]
            for fw, patterns in self.PYTHON_PATTERNS.items()
        }
        self.node_patterns = {
            fw: [re.compile(p, re.IGNORECASE) for p in patterns]
            for fw, patterns in self.NODE_PATTERNS.items()
        }
        self.go_patterns = {
            fw: [re.compile(p, re.IGNORECASE) for p in patterns]
            for fw, patterns in self.GO_PATTERNS.items()
        }
        self.rust_patterns = {
            fw: [re.compile(p, re.IGNORECASE) for p in patterns]
            for fw, patterns in self.RUST_PATTERNS.items()
        }
        self.java_patterns = {
            fw: [re.compile(p, re.IGNORECASE) for p in patterns]
            for fw, patterns in self.JAVA_PATTERNS.items()
        }
        self.dotnet_patterns = {
            fw: [re.compile(p, re.IGNORECASE) for p in patterns]
            for fw, patterns in self.DOTNET_PATTERNS.items()
        }

    def detect_from_config(
        self,
        config_content: str,
        config_file: str,
        language: str = "python"
    ) -> Optional[TestDetectionResult]:
        """Detect test framework from config file content.

        Args:
            config_content: Content of the config file.
            config_file: Name of the config file.
            language: Programming language (python, node, go, rust, java, dotnet).

        Returns:
            TestDetectionResult if detected, None otherwise.
        """
        if language == "python":
            configs = self.PYTHON_CONFIGS
        elif language == "node":
            configs = self.NODE_CONFIGS
        else:
            return None

        if config_file not in configs:
            return None

        for framework, pattern in configs[config_file].items():
            if re.search(pattern, config_content, re.IGNORECASE):
                test_command = self._get_test_command(framework, language)
                return TestDetectionResult(
                    framework=TestFramework(framework),
                    test_command=test_command,
                    config_file=config_file,
                    confidence=0.9,
                )

        return None

    def detect_from_command(
        self,
        command: str,
        language: str = "python"
    ) -> Optional[TestDetectionResult]:
        """Detect test framework from test command.

        Args:
            command: Test command string.
            language: Programming language.

        Returns:
            TestDetectionResult if detected, None otherwise.
        """
        if language == "python":
            patterns = self.python_patterns
        elif language == "node":
            patterns = self.node_patterns
        elif language == "go":
            patterns = self.go_patterns
        elif language == "rust":
            patterns = self.rust_patterns
        elif language == "java":
            patterns = self.java_patterns
        elif language == "dotnet":
            patterns = self.dotnet_patterns
        else:
            return None

        for framework, regex_list in patterns.items():
            for regex in regex_list:
                if regex.search(command):
                    return TestDetectionResult(
                        framework=TestFramework(framework),
                        test_command=command,
                        confidence=0.8,
                    )

        return None

    def detect_from_exit_code(
        self,
        exit_code: int,
        stderr: str,
        language: str = "python"
    ) -> Optional[TestDetectionResult]:
        """Handle test exit codes and suggest fixes.

        Args:
            exit_code: Exit code from test command.
            stderr: Standard error output.
            language: Programming language.

        Returns:
            TestDetectionResult with suggested fix, None if no issue.
        """
        # Pytest exit code 2: no tests collected
        if exit_code == 2 and language == "python":
            if "collected 0 items" in stderr or "no tests collected" in stderr.lower():
                # Suggest alternative test commands
                suggestions = [
                    "pytest -q --collect-only",
                    "python -m pytest -q",
                    "python -m unittest discover -q",
                    "python -m pytest tests/ -q",
                ]

                return TestDetectionResult(
                    framework=TestFramework.PYTEST,
                    test_command=suggestions[0],
                    tests_found=False,
                    confidence=0.7,
                    metadata={
                        "issue": "no_tests_found",
                        "suggestions": suggestions,
                        "original_stderr": stderr[:500],
                    },
                )

        # Jest exit code 1 with no tests
        if exit_code == 1 and language == "node":
            if "No tests found" in stderr or "No specs found" in stderr:
                suggestions = [
                    "npm test -- --listTests",
                    "npm test -- tests/",
                    "jest --findRelatedTests",
                ]

                return TestDetectionResult(
                    framework=TestFramework.JEST,
                    test_command=suggestions[0],
                    tests_found=False,
                    confidence=0.7,
                    metadata={
                        "issue": "no_tests_found",
                        "suggestions": suggestions,
                        "original_stderr": stderr[:500],
                    },
                )

        return None

    def _get_test_command(self, framework: str, language: str) -> str:
        """Get default test command for a framework.

        Args:
            framework: Test framework name.
            language: Programming language.

        Returns:
            Default test command string.
        """
        commands = {
            "pytest": "pytest -q",
            "unittest": "python -m unittest discover -q",
            "nose": "nosetests -q",
            "nox": "nox -s test",
            "tox": "tox -q",
            "jest": "npm test",
            "mocha": "npm test",
            "vitest": "npm test",
            "go_test": "go test ./...",
            "cargo_test": "cargo test",
            "mvn_test": "mvn test",
            "gradle_test": "./gradlew test",
            "dotnet_test": "dotnet test",
        }
        return commands.get(framework, "pytest -q")

    def detect(
        self,
        project_type: str,
        config_files: Dict[str, str],
        test_cmd: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ) -> TestDetectionResult:
        """Detect test framework using multiple methods.

        Args:
            project_type: Project type (python, node, go, rust, java, dotnet).
            config_files: Dictionary of config file names to contents.
            test_cmd: Current test command (if any).
            exit_code: Exit code from test command (if any).
            stderr: Standard error from test command (if any).

        Returns:
            TestDetectionResult with best match.
        """
        # Map project type to language
        lang_map = {
            "python": "python",
            "node": "node",
            "go": "go",
            "rust": "rust",
            "java": "java",
            "dotnet": "dotnet",
        }
        language = lang_map.get(project_type, "python")

        # Priority 1: Handle exit code issues
        if exit_code is not None and stderr:
            exit_result = self.detect_from_exit_code(exit_code, stderr, language)
            if exit_result:
                return exit_result

        # Priority 2: Detect from config files
        for config_file, content in config_files.items():
            config_result = self.detect_from_config(content, config_file, language)
            if config_result:
                return config_result

        # Priority 3: Detect from existing test command
        if test_cmd:
            cmd_result = self.detect_from_command(test_cmd, language)
            if cmd_result:
                return cmd_result

        # Priority 4: Default to language-specific default
        default_cmd = self._get_test_command("pytest" if language == "python" else f"{language}_test", language)
        return TestDetectionResult(
            framework=TestFramework.UNKNOWN,
            test_command=default_cmd,
            confidence=0.5,
            metadata={"fallback": True},
        )


TestFramework.__test__ = False
TestDetectionResult.__test__ = False
TestDetector.__test__ = False
