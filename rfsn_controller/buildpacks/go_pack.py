"""Go buildpack implementation.

Handles Go repositories with go.mod and go.sum.
"""

import hashlib
import re
from typing import List, Optional

from .base import (
    Buildpack,
    BuildpackType,
    BuildpackContext,
    DetectResult,
    Step,
    TestPlan,
    FailureInfo,
)


class GoBuildpack(Buildpack):
    """Buildpack for Go repositories."""

    def __init__(self):
        """Initialize the Go buildpack."""
        super().__init__()
        self._buildpack_type = BuildpackType.GO

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this is a Go repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if Go detected, None otherwise.
        """
        # Check for Go indicator files
        go_indicators = [
            "go.mod",
            "go.sum",
            "go.work",
        ]

        found_indicators = []
        for indicator in go_indicators:
            if indicator in ctx.files or any(f.endswith(indicator) for f in ctx.repo_tree):
                found_indicators.append(indicator)

        if not found_indicators:
            return None

        # go.mod is the primary indicator
        if "go.mod" not in found_indicators:
            return None

        confidence = 0.9 if "go.sum" in found_indicators else 0.8

        return DetectResult(
            buildpack_type=BuildpackType.GO,
            confidence=confidence,
            metadata={"indicators": found_indicators},
        )

    def image(self) -> str:
        """Return the Docker image for Go.

        Returns:
            Docker image tag.
        """
        return "golang:1.22-bookworm"

    def sysdeps_whitelist(self) -> List[str]:
        """Return Go-specific system dependencies.

        Returns:
            List of allowed system packages.
        """
        # Go mostly needs build-essential
        common = ["build-essential", "pkg-config", "git", "ca-certificates"]
        return common

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate Go installation steps.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps.
        """
        steps = []

        # Set GOPROXY for faster downloads
        steps.append(Step(
            argv=["go", "env", "-w", "GOPROXY=https://proxy.golang.org,direct"],
            description="Set GOPROXY",
            timeout_sec=30,
            network_required=True,
        ))

        # Download dependencies
        steps.append(Step(
            argv=["go", "mod", "download"],
            description="Download Go dependencies",
            timeout_sec=300,
            network_required=True,
        ))

        return steps

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate Go test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        if focus_file:
            # Try to extract test name from focus file
            argv = ["go", "test", "./...", "-run", focus_file]
        else:
            argv = ["go", "test", "./..."]

        return TestPlan(
            argv=argv,
            description="Run Go tests",
            timeout_sec=120,
            network_required=False,
            focus_file=focus_file,
        )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse Go test output for failures.

        Args:
            stdout: Standard output from test execution.
            stderr: Standard error from test execution.

        Returns:
            FailureInfo with parsed failure details.
        """
        failing_tests = []
        likely_files = []
        error_type = None
        error_message = None

        output = stdout + "\n" + stderr

        # Parse Go test failures
        # Pattern: --- FAIL: TestFunction (0.00s)
        fail_pattern = r'--- FAIL:\s+(\w+)'
        for match in re.finditer(fail_pattern, output):
            test_name = match.group(1)
            failing_tests.append(test_name)

        # Extract file paths from panic messages
        panic_pattern = r'([^\s]+\.go):(\d+)'
        for match in re.finditer(panic_pattern, output):
            file_path = match.group(1)
            likely_files.append(file_path)

        # Parse error type
        error_pattern = r'(panic|error):\s*(.+)'
        error_match = re.search(error_pattern, output, re.IGNORECASE)
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2).strip()

        # Generate signature
        signature_input = "\n".join(failing_tests) + "\n" + (error_type or "")
        signature = hashlib.sha256(signature_input.encode()).hexdigest()[:16]

        return FailureInfo(
            failing_tests=failing_tests,
            likely_files=list(set(likely_files)),
            signature=signature,
            error_type=error_type,
            error_message=error_message,
        )

    def focus_plan(self, failure: FailureInfo) -> Optional[TestPlan]:
        """Generate focused test plan based on failure.

        Args:
            failure: Failure information from test execution.

        Returns:
            TestPlan for focused testing, or None if not possible.
        """
        if not failure.failing_tests:
            return None

        # Focus on the first failing test
        test_name = failure.failing_tests[0]
        return TestPlan(
            argv=["go", "test", "./...", "-run", test_name],
            description=f"Focus test on {test_name}",
            timeout_sec=120,
            network_required=False,
            focus_file=test_name,
        )

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for Go.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names.
        """
        goals = ["test"]

        # Check for go.mod
        if "go.mod" in ctx.files:
            goals.append("lint")  # go vet

        return goals

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required external services for Go.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names (postgres, redis, mysql, mongodb, etc.).
        """
        services = []

        # Check go.mod for service indicators
        go_mod = ctx.files.get("go.mod", "").lower()

        # PostgreSQL
        if any(
            dep in go_mod
            for dep in ["postgres", "pgx", "lib/pq", "github.com/lib/pq"]
        ):
            services.append("postgres")

        # Redis
        if any(
            dep in go_mod
            for dep in ["redis", "go-redis", "github.com/redis/go-redis"]
        ):
            services.append("redis")

        # MySQL
        if any(
            dep in go_mod
            for dep in ["mysql", "go-sql-driver/mysql"]
        ):
            services.append("mysql")

        # MongoDB
        if any(
            dep in go_mod
            for dep in ["mongo", "mongo-driver", "go.mongodb.org/mongo-driver"]
        ):
            services.append("mongodb")

        # Elasticsearch
        if any(
            dep in go_mod
            for dep in ["elasticsearch", "olivere/elastic"]
        ):
            services.append("elasticsearch")

        # RabbitMQ
        if any(
            dep in go_mod
            for dep in ["amqp", "rabbitmq", "github.com/streadway/amqp"]
        ):
            services.append("rabbitmq")

        return services
