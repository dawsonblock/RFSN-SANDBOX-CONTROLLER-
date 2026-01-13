"""Polyrepo buildpack for monorepo support.

Handles repositories with multiple projects in different languages.
"""

from typing import List, Optional, Dict, Any

from .base import (
    Buildpack,
    BuildpackType,
    BuildpackContext,
    DetectResult,
    Step,
    TestPlan,
    FailureInfo,
)
from .python_pack import PythonBuildpack
from .node_pack import NodeBuildpack
from .go_pack import GoBuildpack
from .rust_pack import RustBuildpack
from .java_pack import JavaBuildpack
from .dotnet_pack import DotnetBuildpack


class PolyrepoBuildpack(Buildpack):
    """Buildpack for polyglot/monorepo repositories."""

    def __init__(self):
        """Initialize the polyrepo buildpack."""
        super().__init__()
        self._buildpack_type = BuildpackType.POLYREPO
        self._sub_buildpacks = [
            PythonBuildpack(),
            NodeBuildpack(),
            GoBuildpack(),
            RustBuildpack(),
            JavaBuildpack(),
            DotnetBuildpack(),
        ]

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this is a polyrepo repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if polyrepo detected, None otherwise.
        """
        # Detect which sub-buildpacks apply
        detected = []
        for buildpack in self._sub_buildpacks:
            result = buildpack.detect(ctx)
            if result and result.confidence > 0.5:
                detected.append((buildpack, result))

        # Need at least 2 different languages to be a polyrepo
        if len(detected) < 2:
            return None

        # Sort by confidence
        detected.sort(key=lambda x: x[1].confidence, reverse=True)

        # Calculate overall confidence
        avg_confidence = sum(r.confidence for _, r in detected) / len(detected)

        return DetectResult(
            buildpack_type=BuildpackType.POLYREPO,
            confidence=avg_confidence,
            metadata={
                "detected_languages": [
                    {
                        "type": bp.buildpack_type.value,
                        "confidence": r.confidence,
                    }
                    for bp, r in detected
                ],
                "primary": detected[0][0].buildpack_type.value,
            },
        )

    def image(self) -> str:
        """Return the Docker image for polyrepo.

        Returns:
            Docker image tag (uses Python as base for flexibility).
        """
        return "python:3.11-slim"

    def sysdeps_whitelist(self) -> List[str]:
        """Return polyrepo system dependencies.

        Returns:
            List of allowed system packages (union of all buildpacks).
        """
        all_packages = set()
        for buildpack in self._sub_buildpacks:
            all_packages.update(buildpack.sysdeps_whitelist())
        return sorted(list(all_packages))

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate polyrepo installation steps.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps.
        """
        steps = []

        # Use primary language's install plan
        primary = self._get_primary_buildpack(ctx)
        if primary:
            steps.extend(primary.install_plan(ctx))

        return steps

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate polyrepo test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        # Use primary language's test plan
        primary = self._get_primary_buildpack(ctx)
        if primary:
            return primary.test_plan(ctx, focus_file)

        # Fallback to Python
        return TestPlan(
            argv=["python", "-m", "pytest", "-q"],
            description="Run pytest (fallback)",
            timeout_sec=120,
            network_required=False,
            focus_file=focus_file,
        )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse polyrepo test output for failures.

        Args:
            stdout: Standard output from test execution.
            stderr: Standard error from test execution.

        Returns:
            FailureInfo with parsed failure details.
        """
        # Try to detect language from output and use appropriate parser
        output = stdout + "\n" + stderr

        # Check for Python patterns
        if "FAILED" in output and ("::" in output or "Traceback" in output):
            return PythonBuildpack().parse_failures(stdout, stderr)

        # Check for Node.js patterns
        if "FAIL" in output and ("jest" in output.lower() or "mocha" in output.lower()):
            return NodeBuildpack().parse_failures(stdout, stderr)

        # Check for Go patterns
        if "--- FAIL:" in output:
            return GoBuildpack().parse_failures(stdout, stderr)

        # Check for Rust patterns
        if "test result: FAILED" in output:
            return RustBuildpack().parse_failures(stdout, stderr)

        # Check for Java patterns
        if "Tests run:" in output or "BUILD FAILED" in output:
            return JavaBuildpack().parse_failures(stdout, stderr)

        # Check for .NET patterns
        if "Failed!" in output:
            return DotnetBuildpack().parse_failures(stdout, stderr)

        # Default to Python
        return PythonBuildpack().parse_failures(stdout, stderr)

    def focus_plan(self, failure: FailureInfo) -> Optional[TestPlan]:
        """Generate focused test plan based on failure.

        Args:
            failure: Failure information from test execution.

        Returns:
            TestPlan for focused testing, or None if not possible.
        """
        # Try to determine language from likely files
        if failure.likely_files:
            for file_path in failure.likely_files:
                if file_path.endswith(".py"):
                    return PythonBuildpack().focus_plan(failure)
                elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                    return NodeBuildpack().focus_plan(failure)
                elif file_path.endswith(".go"):
                    return GoBuildpack().focus_plan(failure)
                elif file_path.endswith(".rs"):
                    return RustBuildpack().focus_plan(failure)
                elif file_path.endswith(".java"):
                    return JavaBuildpack().focus_plan(failure)
                elif file_path.endswith(".cs"):
                    return DotnetBuildpack().focus_plan(failure)

        return None

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for polyrepo.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names.
        """
        # Use primary language's goals
        primary = self._get_primary_buildpack(ctx)
        if primary:
            return primary.get_verification_goals(ctx)

        return ["test"]

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required services for polyrepo.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names.
        """
        services = set()
        for buildpack in self._sub_buildpacks:
            services.update(buildpack.get_services_required(ctx))
        return sorted(list(services))

    def _get_primary_buildpack(self, ctx: BuildpackContext) -> Optional[Buildpack]:
        """Get the primary buildpack for the repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            Primary buildpack or None.
        """
        detected = []
        for buildpack in self._sub_buildpacks:
            result = buildpack.detect(ctx)
            if result and result.confidence > 0.5:
                detected.append((buildpack, result))

        if not detected:
            return None

        # Return highest confidence buildpack
        detected.sort(key=lambda x: x[1].confidence, reverse=True)
        return detected[0][0]
