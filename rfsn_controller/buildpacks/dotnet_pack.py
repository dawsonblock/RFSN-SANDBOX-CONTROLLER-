""".NET buildpack implementation.

Handles .NET repositories with .csproj, .sln, or global.json.
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


class DotnetBuildpack(Buildpack):
    """Buildpack for .NET repositories."""

    def __init__(self):
        """Initialize the .NET buildpack."""
        super().__init__()
        self._buildpack_type = BuildpackType.DOTNET

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this is a .NET repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if .NET detected, None otherwise.
        """
        # Check for .NET indicator files
        found_indicators = []
        if any(f.endswith(".csproj") for f in ctx.repo_tree):
            found_indicators.append(".csproj")
        if any(f.endswith(".sln") for f in ctx.repo_tree):
            found_indicators.append(".sln")
        if "global.json" in ctx.files or any(f.endswith("/global.json") or f == "global.json" for f in ctx.repo_tree):
            found_indicators.append("global.json")
        if "Directory.Build.props" in ctx.files or any(
            f.endswith("/Directory.Build.props") or f == "Directory.Build.props" for f in ctx.repo_tree
        ):
            found_indicators.append("Directory.Build.props")

        if not found_indicators:
            return None

        # .csproj or .sln is the primary indicator
        if ".csproj" not in found_indicators and ".sln" not in found_indicators:
            return None

        confidence = 0.9

        return DetectResult(
            buildpack_type=BuildpackType.DOTNET,
            confidence=confidence,
            metadata={"indicators": found_indicators},
        )

    def image(self) -> str:
        """Return the Docker image for .NET.

        Returns:
            Docker image tag.
        """
        return "mcr.microsoft.com/dotnet/sdk:8.0"

    def sysdeps_whitelist(self) -> List[str]:
        """Return .NET-specific system dependencies.

        Returns:
            List of allowed system packages.
        """
        # .NET needs build-essential for native compilation
        common = ["build-essential", "pkg-config", "git", "ca-certificates"]
        return common

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate .NET installation steps.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps.
        """
        steps = []

        # Restore dependencies
        steps.append(Step(
            argv=["dotnet", "restore"],
            description="Restore .NET dependencies",
            timeout_sec=300,
            network_required=True,
        ))

        return steps

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate .NET test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        if focus_file:
            # Try to run specific test project
            argv = ["dotnet", "test", "--nologo", "--filter", f"FullyQualifiedName~{focus_file}"]
        else:
            argv = ["dotnet", "test", "--nologo"]

        return TestPlan(
            argv=argv,
            description="Run .NET tests",
            timeout_sec=120,
            network_required=False,
            focus_file=focus_file,
        )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse .NET test output for failures.

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

        # Parse .NET test failures
        # Pattern: Failed!  - Failed: TestName (Error Message)
        fail_pattern = r'Failed!\s+-\s+Failed:\s+([^\s(]+)'
        for match in re.finditer(fail_pattern, output):
            test_name = match.group(1)
            failing_tests.append(test_name)

        # Extract file paths from stack traces
        # Pattern: /path/to/file.cs:line
        file_pattern = r'([^\s]+\.cs):(\d+)'
        for match in re.finditer(file_pattern, output):
            file_path = match.group(1)
            likely_files.append(file_path)

        # Parse error type
        error_pattern = r'([A-Z][a-zA-Z]*Exception):'
        error_match = re.search(error_pattern, output)
        if error_match:
            error_type = error_match.group(1)

        # Parse error message
        message_pattern = r'[A-Z][a-zA-Z]*Exception:\s*(.+?)(?:\n|$)'
        message_match = re.search(message_pattern, output)
        if message_match:
            error_message = message_match.group(1).strip()

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
            argv=["dotnet", "test", "--nologo", "--filter", f"FullyQualifiedName~{test_name}"],
            description=f"Focus test on {test_name}",
            timeout_sec=120,
            network_required=False,
            focus_file=test_name,
        )

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for .NET.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names.
        """
        goals = ["test"]

        # Check for .csproj files with analyzers
        for filename in ctx.files:
            if filename.endswith(".csproj"):
                content = ctx.files.get(filename, "")
                if "StyleCop" in content or "Roslynator" in content:
                    goals.append("lint")
                break

        return goals

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required external services for .NET.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names (postgres, redis, mysql, mongodb, etc.).
        """
        services = []

        # Check .csproj files for service indicators
        for filename in ctx.files:
            if filename.endswith(".csproj"):
                content = ctx.files.get(filename, "").lower()

                # PostgreSQL
                if any(
                    dep in content
                    for dep in ["npgsql", "postgres", "entityframeworkcore.postgresql"]
                ):
                    services.append("postgres")

                # Redis
                if any(
                    dep in content
                    for dep in ["stackexchange.redis", "redis"]
                ):
                    services.append("redis")

                # MySQL
                if any(
                    dep in content
                    for dep in ["mysql", "mysql.data", "pomelo.entityframeworkcore.mysql"]
                ):
                    services.append("mysql")

                # MongoDB
                if any(
                    dep in content
                    for dep in ["mongodb", "mongodriver"]
                ):
                    services.append("mongodb")

                # Elasticsearch
                if any(
                    dep in content
                    for dep in ["elasticsearch", "nest"]
                ):
                    services.append("elasticsearch")

                # RabbitMQ
                if any(
                    dep in content
                    for dep in ["rabbitmq", "masstransit"]
                ):
                    services.append("rabbitmq")

                break

        return services
