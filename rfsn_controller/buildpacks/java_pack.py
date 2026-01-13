"""Java buildpack implementation.

Handles Java repositories with Maven or Gradle.
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


class JavaBuildpack(Buildpack):
    """Buildpack for Java repositories."""

    def __init__(self):
        """Initialize the Java buildpack."""
        super().__init__()
        self._buildpack_type = BuildpackType.JAVA

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect if this is a Java repository.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            DetectResult if Java detected, None otherwise.
        """
        # Check for Java indicator files
        java_indicators = [
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "gradlew",
            "gradlew.bat",
        ]

        found_indicators = []
        for indicator in java_indicators:
            if indicator in ctx.files or any(f.endswith(indicator) for f in ctx.repo_tree):
                found_indicators.append(indicator)

        if not found_indicators:
            return None

        # Determine build system
        build_system = "maven" if "pom.xml" in found_indicators else "gradle"

        confidence = 0.9 if build_system == "maven" else 0.85

        return DetectResult(
            buildpack_type=BuildpackType.JAVA,
            confidence=confidence,
            metadata={
                "indicators": found_indicators,
                "build_system": build_system,
            },
        )

    def image(self) -> str:
        """Return the Docker image for Java.

        Returns:
            Docker image tag.
        """
        return "eclipse-temurin:17-jdk"

    def sysdeps_whitelist(self) -> List[str]:
        """Return Java-specific system dependencies.

        Returns:
            List of allowed system packages.
        """
        # Java needs build-essential for native compilation
        common = ["build-essential", "pkg-config", "git", "ca-certificates"]
        return common

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate Java installation steps.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of installation steps.
        """
        steps = []

        # Determine build system
        if "pom.xml" in ctx.files:
            # Maven
            steps.append(Step(
                argv=["mvn", "-q", "-DskipTests", "package"],
                description="Build with Maven",
                timeout_sec=300,
                network_required=True,
            ))
        else:
            # Gradle
            if "gradlew" in ctx.files or any(f.endswith("gradlew") for f in ctx.repo_tree):
                steps.append(Step(
                    argv=["./gradlew", "--no-daemon", "testClasses"],
                    description="Build with Gradle wrapper",
                    timeout_sec=300,
                    network_required=True,
                ))
            else:
                steps.append(Step(
                    argv=["gradle", "--no-daemon", "testClasses"],
                    description="Build with Gradle",
                    timeout_sec=300,
                    network_required=True,
                ))

        return steps

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate Java test execution plan.

        Args:
            ctx: Buildpack context with repo information.
            focus_file: Optional file to focus tests on.

        Returns:
            TestPlan with command and configuration.
        """
        # Determine build system
        if "pom.xml" in ctx.files:
            # Maven
            if focus_file:
                # Try to run specific test class
                argv = ["mvn", "-q", "test", f"-Dtest={focus_file}"]
            else:
                argv = ["mvn", "-q", "test"]
            return TestPlan(
                argv=argv,
                description="Run Maven tests",
                timeout_sec=120,
                network_required=False,
                focus_file=focus_file,
            )
        else:
            # Gradle
            if "gradlew" in ctx.files or any(f.endswith("gradlew") for f in ctx.repo_tree):
                argv = ["./gradlew", "--no-daemon", "test"]
            else:
                argv = ["gradle", "--no-daemon", "test"]
            return TestPlan(
                argv=argv,
                description="Run Gradle tests",
                timeout_sec=120,
                network_required=False,
                focus_file=focus_file,
            )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse Java test output for failures.

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

        # Parse Maven test failures
        # Pattern: Tests run: X, Failures: Y, Errors: Z
        maven_pattern = r'Failures:\s+(\d+)'
        maven_match = re.search(maven_pattern, output)
        if maven_match:
            # Extract failing test names
            fail_pattern = r'([A-Z][a-zA-Z0-9_]+Test)\.([a-zA-Z0-9_]+)'
            for match in re.finditer(fail_pattern, output):
                test_class = match.group(1)
                test_method = match.group(2)
                failing_tests.append(f"{test_class}.{test_method}")
                likely_files.append(test_class.replace(".", "/") + ".java")

        # Parse Gradle test failures
        gradle_pattern = r'([A-Z][a-zA-Z0-9_]+Test) > ([a-zA-Z0-9_]+)\s+FAILED'
        for match in re.finditer(gradle_pattern, output):
            test_class = match.group(1)
            test_method = match.group(2)
            failing_tests.append(f"{test_class}.{test_method}")
            likely_files.append(test_class.replace(".", "/") + ".java")

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
            argv=["mvn", "-q", "test", f"-Dtest={test_name}"],
            description=f"Focus test on {test_name}",
            timeout_sec=120,
            network_required=False,
            focus_file=test_name,
        )

    def get_verification_goals(self, ctx: BuildpackContext) -> List[str]:
        """Get verification goals for Java.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of goal names.
        """
        goals = ["test"]

        # Check for checkstyle or spotbugs
        if "pom.xml" in ctx.files:
            pom_content = ctx.files.get("pom.xml", "")
            if "checkstyle" in pom_content or "spotbugs" in pom_content:
                goals.append("lint")

        return goals

    def get_services_required(self, ctx: BuildpackContext) -> List[str]:
        """Get required external services for Java.

        Args:
            ctx: Buildpack context with repo information.

        Returns:
            List of service names (postgres, redis, mysql, mongodb, etc.).
        """
        services = []

        # Check pom.xml or build.gradle for service indicators
        pom_xml = ctx.files.get("pom.xml", "").lower()
        build_gradle = ctx.files.get("build.gradle", "").lower()
        all_config = pom_xml + build_gradle

        # PostgreSQL
        if any(
            dep in all_config
            for dep in ["postgresql", "postgres", "hibernate", "spring-boot-starter-data-jpa"]
        ):
            services.append("postgres")

        # Redis
        if any(
            dep in all_config
            for dep in ["redis", "spring-boot-starter-data-redis", "jedis", "lettuce"]
        ):
            services.append("redis")

        # MySQL
        if any(
            dep in all_config
            for dep in ["mysql", "mysql-connector", "spring-boot-starter-data-mysql"]
        ):
            services.append("mysql")

        # MongoDB
        if any(
            dep in all_config
            for dep in ["mongodb", "mongo", "spring-boot-starter-data-mongodb"]
        ):
            services.append("mongodb")

        # Elasticsearch
        if any(
            dep in all_config
            for dep in ["elasticsearch", "spring-boot-starter-data-elasticsearch"]
        ):
            services.append("elasticsearch")

        # RabbitMQ
        if any(
            dep in all_config
            for dep in ["rabbitmq", "amqp", "spring-boot-starter-amqp"]
        ):
            services.append("rabbitmq")

        return services
