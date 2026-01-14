"""Node.js buildpack implementation.

Handles Node.js repositories with npm, yarn, pnpm, or bun.
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


class NodeBuildpack(Buildpack):
    """Buildpack for Node.js repositories."""

    def __init__(self):
        """Initialize the Node.js buildpack."""
        super().__init__()
        self._buildpack_type = BuildpackType.NODE

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this is a Node.js repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if Node.js detected, None otherwise.
        """
        # Check for Node.js indicator files
        node_indicators = [
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "bun.lockb",
            "node_modules",
        ]

        found_indicators = []
        for indicator in node_indicators:
            # Check exact filename match in files dict
            if indicator in ctx.files:
                found_indicators.append(indicator)
            # Check for exact filename match in repo_tree (not just endsWith)
            elif any(f == indicator or f.endswith("/" + indicator) for f in ctx.repo_tree):
                found_indicators.append(indicator)

        if not found_indicators:
            return None

        # package.json is the primary indicator
        if "package.json" not in found_indicators:
            return None

        # Calculate confidence
        confidence = 0.6
        if "package-lock.json" in found_indicators:
            confidence += 0.2
        if "yarn.lock" in found_indicators:
            confidence += 0.2
        if "pnpm-lock.yaml" in found_indicators:
            confidence += 0.2

        confidence = min(confidence, 1.0)

        # Determine package manager
        package_manager = "npm"
        if "pnpm-lock.yaml" in found_indicators:
            package_manager = "pnpm"
        elif "yarn.lock" in found_indicators:
            package_manager = "yarn"
        elif "bun.lockb" in found_indicators:
            package_manager = "bun"

        return DetectResult(
            buildpack_type=BuildpackType.NODE,
            confidence=confidence,
            metadata={
                "indicators": found_indicators,
                "package_manager": package_manager,
            },
        )

    def image(self) -> str:
        """Return the Docker image for Node.js.

        Returns:
            Docker image tag (alpine-based for smaller size).
        """
        return "node:20-alpine"

    def sysdeps_whitelist(self) -> List[str]:
        """Return Node.js-specific system dependencies.

        Returns:
            List of allowed system packages.
        """
        # Common core + Node.js extras for native modules
        common = ["build-essential", "pkg-config", "git", "ca-certificates"]
        node_extras = ["python3", "make", "g++"]
        return common + node_extras

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate Node.js installation steps.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps.
        """
        steps = []

        # Determine package manager from detection or files
        package_manager = "npm"
        if "pnpm-lock.yaml" in ctx.files:
            package_manager = "pnpm"
        elif "yarn.lock" in ctx.files:
            package_manager = "yarn"
        elif "bun.lockb" in ctx.files:
            package_manager = "bun"

        # Install dependencies based on package manager
        if package_manager == "pnpm":
            # Try pnpm with corepack, fall back to npm if unavailable
            steps.append(Step(
                argv=["sh", "-c", "corepack enable && pnpm --version || echo 'pnpm_not_available'"],
                description="Check if pnpm is available",
                timeout_sec=60,
                network_required=True,
            ))
            steps.append(Step(
                argv=["sh", "-c", "pnpm install --frozen-lockfile 2>/dev/null || npm install"],
                description="Install dependencies (pnpm or npm fallback)",
                timeout_sec=300,
                network_required=True,
            ))
        elif package_manager == "yarn":
            steps.append(Step(
                argv=["sh", "-c", "corepack enable && yarn --version || echo 'yarn_not_available'"],
                description="Check if yarn is available",
                timeout_sec=60,
                network_required=True,
            ))
            steps.append(Step(
                argv=["sh", "-c", "yarn install --frozen-lockfile 2>/dev/null || npm install"],
                description="Install dependencies (yarn or npm fallback)",
                timeout_sec=300,
                network_required=True,
            ))
        elif package_manager == "bun":
            steps.append(Step(
                argv=["bun", "install"],
                description="Install dependencies with bun",
                timeout_sec=300,
                network_required=True,
            ))
        else:  # npm
            if "package-lock.json" in ctx.files:
                steps.append(Step(
                    argv=["npm", "ci"],
                    description="Install dependencies with npm ci",
                    timeout_sec=300,
                    network_required=True,
                ))
            else:
                steps.append(Step(
                    argv=["npm", "install"],
                    description="Install dependencies with npm",
                    timeout_sec=300,
                    network_required=True,
                ))

        return steps

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate Node.js test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        package_json = ctx.files.get("package.json", "")

        # Check for test script
        if '"test"' in package_json:
            # Determine test runner
            if "jest" in package_json:
                if focus_file:
                    argv = ["npx", "jest", focus_file, "--runInBand"]
                else:
                    argv = ["npm", "test", "--silent"]
                return TestPlan(
                    argv=argv,
                    description="Run Jest tests",
                    timeout_sec=120,
                    network_required=False,
                    focus_file=focus_file,
                )
            elif "mocha" in package_json:
                if focus_file:
                    argv = ["npx", "mocha", focus_file]
                else:
                    argv = ["npm", "test", "--silent"]
                return TestPlan(
                    argv=argv,
                    description="Run Mocha tests",
                    timeout_sec=120,
                    network_required=False,
                    focus_file=focus_file,
                )
            elif "vitest" in package_json:
                if focus_file:
                    argv = ["npx", "vitest", "run", focus_file]
                else:
                    argv = ["npm", "test", "--silent"]
                return TestPlan(
                    argv=argv,
                    description="Run Vitest tests",
                    timeout_sec=120,
                    network_required=False,
                    focus_file=focus_file,
                )
            else:
                # Default test script
                return TestPlan(
                    argv=["npm", "test", "--silent"],
                    description="Run npm test",
                    timeout_sec=120,
                    network_required=False,
                    focus_file=focus_file,
                )

        # Default to jest if no test script
        if focus_file:
            argv = ["npx", "jest", focus_file, "--runInBand"]
        else:
            argv = ["npx", "jest", "--runInBand"]
        return TestPlan(
            argv=argv,
            description="Run Jest (default)",
            timeout_sec=120,
            network_required=False,
            focus_file=focus_file,
        )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse Node.js test output for failures.

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

        # Parse Jest failures
        jest_pattern = r'FAIL\s+([^\s]+)'
        for match in re.finditer(jest_pattern, output):
            test_file = match.group(1)
            failing_tests.append(test_file)
            likely_files.append(test_file)

        # Parse Mocha failures
        mocha_pattern = r'\s+\d+\)\s+([^\s]+)'
        for match in re.finditer(mocha_pattern, output):
            test_name = match.group(1)
            failing_tests.append(test_name)

        # Parse error type
        error_pattern = r'([A-Z][a-zA-Z]*Error):'
        error_match = re.search(error_pattern, output)
        if error_match:
            error_type = error_match.group(1)

        # Parse error message
        message_pattern = r'[A-Z][a-zA-Z]*Error:\s*(.+?)(?:\n|$)'
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
        if not failure.likely_files:
            return None

        # Focus on the first likely file
        focus_file = failure.likely_files[0]
        return TestPlan(
            argv=["npx", "jest", focus_file, "--runInBand"],
            description=f"Focus test on {focus_file}",
            timeout_sec=120,
            network_required=False,
            focus_file=focus_file,
        )

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for Node.js.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names.
        """
        goals = ["test"]

        package_json = ctx.files.get("package.json", "")

        # Check for linting
        if '"lint"' in package_json or '"eslint"' in package_json:
            goals.append("lint")

        # Check for type checking
        if '"typecheck"' in package_json or '"tsc"' in package_json:
            goals.append("typecheck")

        return goals

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required external services for Node.js.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names (postgres, redis, mysql, mongodb, etc.).
        """
        services = []

        # Check package.json for service indicators
        package_json = ctx.files.get("package.json", "").lower()

        # PostgreSQL
        if any(
            dep in package_json
            for dep in ["pg", "postgres", "pg-promise", "sequelize", "typeorm"]
        ):
            services.append("postgres")

        # Redis
        if any(
            dep in package_json
            for dep in ["redis", "ioredis", "redis-mock", "connect-redis"]
        ):
            services.append("redis")

        # MySQL
        if any(
            dep in package_json
            for dep in ["mysql", "mysql2", "sequelize", "typeorm"]
        ):
            services.append("mysql")

        # MongoDB
        if any(
            dep in package_json
            for dep in ["mongodb", "mongoose", "mongorito"]
        ):
            services.append("mongodb")

        # Elasticsearch
        if any(
            dep in package_json
            for dep in ["elasticsearch", "@elastic/elasticsearch"]
        ):
            services.append("elasticsearch")

        # RabbitMQ
        if any(
            dep in package_json
            for dep in ["amqplib", "rabbitmq", "bull", "bullmq"]
        ):
            services.append("rabbitmq")

        return services
