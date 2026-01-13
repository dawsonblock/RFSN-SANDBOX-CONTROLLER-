"""Buildpack base interface and types.

Defines the contract that all buildpacks must implement for multi-language
repository support.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class BuildpackType(Enum):
    """Supported buildpack types."""
    PYTHON = "python"
    NODE = "node"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    DOTNET = "dotnet"
    POLYREPO = "polyrepo"
    UNKNOWN = "unknown"


@dataclass
class DetectResult:
    """Result of buildpack detection."""

    buildpack_type: BuildpackType
    confidence: float  # 0.0 to 1.0
    workspace: Optional[str] = None  # Subdirectory for monorepos
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Step:
    """A single installation or setup step."""

    argv: List[str]  # Command as argv list (never shell=True)
    description: str
    timeout_sec: int = 300
    network_required: bool = False


@dataclass
class TestPlan:
    """A test execution plan."""

    argv: List[str]  # Command as argv list
    description: str
    timeout_sec: int = 120
    network_required: bool = False
    focus_file: Optional[str] = None  # For focused tests


@dataclass
class FailureInfo:
    """Parsed failure information from test output."""

    failing_tests: List[str]  # Test identifiers
    likely_files: List[str]  # Files to examine
    signature: str  # Hash of failure signature
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BuildpackContext:
    """Context provided to buildpack methods."""

    repo_dir: str
    repo_tree: List[str]
    files: Dict[str, str]  # filename -> content
    workspace: Optional[str] = None


class Buildpack:
    """Base class for all buildpacks.

    Each buildpack must implement:
    - detect(): Determine if this buildpack applies
    - image(): Return the Docker image to use
    - sysdeps_whitelist(): Return allowed system packages
    - install_plan(): Return installation steps
    - test_plan(): Return test execution plan
    - parse_failures(): Parse test output for failures
    - focus_plan(): Generate focused test plan
    """

    def __init__(self):
        """Initialize the buildpack."""
        self._buildpack_type = BuildpackType.UNKNOWN

    @property
    def buildpack_type(self) -> BuildpackType:
        """Return the buildpack type."""
        return self._buildpack_type

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this buildpack applies to the repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if this buildpack applies, None otherwise.
        """
        raise NotImplementedError("Subclasses must implement detect()")

    def image(self) -> str:
        """Return the Docker image to use for this buildpack.

        Returns:
            Docker image tag (e.g., "python:3.11-slim").
        """
        raise NotImplementedError("Subclasses must implement image()")

    def sysdeps_whitelist(self) -> List[str]:
        """Return the whitelist of allowed system packages.

        Returns:
            List of package names allowed for installation.
        """
        # Common core packages
        common = ["build-essential", "pkg-config", "git", "ca-certificates"]
        return common

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate installation steps for this buildpack.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps to execute.
        """
        raise NotImplementedError("Subclasses must implement install_plan()")

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        raise NotImplementedError("Subclasses must implement test_plan()")

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse test output to extract failure information.

        Args:
            stdout: Standard output from test execution.
            stderr: Standard error from test execution.

        Returns:
            FailureInfo with parsed failure details.
        """
        raise NotImplementedError("Subclasses must implement parse_failures()")

    def focus_plan(self, failure: FailureInfo) -> Optional[TestPlan]:
        """Generate focused test plan based on failure.

        Args:
            failure: Failure information from test execution.

        Returns:
            TestPlan for focused testing, or None if not possible.
        """
        return None

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required external services for this buildpack.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names (postgres, redis, mysql, mongodb, etc.).
        """
        return []

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for this buildpack.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names (test, lint, typecheck, etc.).
        """
        return ["test"]
