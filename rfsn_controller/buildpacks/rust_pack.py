"""Rust buildpack implementation.

Handles Rust repositories with Cargo.toml and Cargo.lock.
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


class RustBuildpack(Buildpack):
    """Buildpack for Rust repositories."""

    def __init__(self):
        """Initialize the Rust buildpack."""
        super().__init__()
        self._buildpack_type = BuildpackType.RUST

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this is a Rust repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if Rust detected, None otherwise.
        """
        # Check for Rust indicator files
        rust_indicators = [
            "Cargo.toml",
            "Cargo.lock",
        ]

        found_indicators = []
        for indicator in rust_indicators:
            if indicator in ctx.files or any(f.endswith(indicator) for f in ctx.repo_tree):
                found_indicators.append(indicator)

        if not found_indicators:
            return None

        # Cargo.toml is the primary indicator
        if "Cargo.toml" not in found_indicators:
            return None

        confidence = 0.9 if "Cargo.lock" in found_indicators else 0.8

        return DetectResult(
            buildpack_type=BuildpackType.RUST,
            confidence=confidence,
            metadata={"indicators": found_indicators},
        )

    def image(self) -> str:
        """Return the Docker image for Rust.

        Returns:
            Docker image tag.
        """
        return "rust:1.78-bookworm"

    def sysdeps_whitelist(self) -> List[str]:
        """Return Rust-specific system dependencies.

        Returns:
            List of allowed system packages.
        """
        # Rust mostly needs build-essential for native compilation
        common = ["build-essential", "pkg-config", "git", "ca-certificates"]
        return common

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate Rust installation steps.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps.
        """
        steps = []

        # Fetch dependencies
        steps.append(Step(
            argv=["cargo", "fetch"],
            description="Fetch Rust dependencies",
            timeout_sec=300,
            network_required=True,
        ))

        return steps

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate Rust test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        if focus_file:
            # Try to extract test name from focus file
            argv = ["cargo", "test", focus_file]
        else:
            argv = ["cargo", "test"]

        return TestPlan(
            argv=argv,
            description="Run Rust tests",
            timeout_sec=120,
            network_required=False,
            focus_file=focus_file,
        )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse Rust test output for failures.

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

        # Parse Rust test failures
        # Pattern: test test_name ... FAILED
        fail_pattern = r'test\s+(\w+)\s+\.\.\.\s+FAILED'
        for match in re.finditer(fail_pattern, output):
            test_name = match.group(1)
            failing_tests.append(test_name)

        # Extract file paths from failure output
        # Pattern: src/main.rs:42:5
        file_pattern = r'([^\s]+\.rs):(\d+):(\d+)'
        for match in re.finditer(file_pattern, output):
            file_path = match.group(1)
            likely_files.append(file_path)

        # Parse error type
        error_pattern = r'(panic|error)\[E\d+\]?:\s*(.+)'
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
            argv=["cargo", "test", test_name],
            description=f"Focus test on {test_name}",
            timeout_sec=120,
            network_required=False,
            focus_file=test_name,
        )

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for Rust.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names.
        """
        goals = ["test"]

        # Check for Cargo.toml
        if "Cargo.toml" in ctx.files:
            goals.append("lint")  # cargo clippy

        return goals

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required external services for Rust.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names (postgres, redis, mysql, mongodb, etc.).
        """
        services = []

        # Check Cargo.toml for service indicators
        cargo_toml = ctx.files.get("Cargo.toml", "").lower()

        # PostgreSQL
        if any(
            dep in cargo_toml
            for dep in ["postgres", "tokio-postgres", "diesel/postgres"]
        ):
            services.append("postgres")

        # Redis
        if any(
            dep in cargo_toml
            for dep in ["redis", "redis-rs", "deadpool-redis"]
        ):
            services.append("redis")

        # MySQL
        if any(
            dep in cargo_toml
            for dep in ["mysql", "diesel/mysql"]
        ):
            services.append("mysql")

        # MongoDB
        if any(
            dep in cargo_toml
            for dep in ["mongo", "mongodb", "mongodb"]
        ):
            services.append("mongodb")

        # Elasticsearch
        if any(
            dep in cargo_toml
            for dep in ["elasticsearch", "elastic"]
        ):
            services.append("elasticsearch")

        # RabbitMQ
        if any(
            dep in cargo_toml
            for dep in ["amqp", "rabbitmq", "lapin"]
        ):
            services.append("rabbitmq")

        return services
