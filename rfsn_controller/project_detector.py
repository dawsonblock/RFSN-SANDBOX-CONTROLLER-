"""Multi-language project detection.

Detects project type, install strategy, test strategy, and environment requirements
for Python, Node, Go, Rust, Java, and .NET projects.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class ProjectType(Enum):
    """Supported project types."""
    PYTHON = "python"
    NODE = "node"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    DOTNET = "dotnet"
    UNKNOWN = "unknown"


@dataclass
class ProjectDetection:
    """Result of project detection."""
    project_type: ProjectType
    install_strategy: str
    test_strategy: str
    build_strategy: Optional[str]
    artifact_locations: List[str]
    requires_services: bool
    system_deps_hint: List[str]
    confidence: float  # 0.0 to 1.0


class ProjectDetector:
    """Detects project type and strategies from repository files."""

    # File patterns for each language
    PYTHON_PATTERNS = [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "poetry.lock",
        "tox.ini",
        "pytest.ini",
    ]

    NODE_PATTERNS = [
        "package.json",
        "yarn.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        ".npmrc",
    ]

    GO_PATTERNS = [
        "go.mod",
        "go.sum",
        "go.work",
    ]

    RUST_PATTERNS = [
        "Cargo.toml",
        "Cargo.lock",
    ]

    JAVA_PATTERNS = [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "gradlew",
        "mvnw",
    ]

    DOTNET_PATTERNS = [
        "*.csproj",
        "*.sln",
        "global.json",
        "Directory.Build.props",
    ]

    def __init__(self, repo_path: str):
        """Initialize detector with repository path.

        Args:
            repo_path: Path to the repository root.
        """
        self.repo_path = repo_path
        self._file_cache: Optional[Dict[str, bool]] = None

    def _file_exists(self, pattern: str) -> bool:
        """Check if a file matching pattern exists.

        Args:
            pattern: File pattern (can include wildcards).

        Returns:
            True if matching file exists.
        """
        if self._file_cache is None:
            self._file_cache = {}

        if pattern in self._file_cache:
            return self._file_cache[pattern]

        # Handle wildcards
        if "*" in pattern:
            import glob
            matches = glob.glob(os.path.join(self.repo_path, pattern))
            exists = len(matches) > 0
        else:
            exists = os.path.exists(os.path.join(self.repo_path, pattern))

        self._file_cache[pattern] = exists
        return exists

    def _count_matches(self, patterns: List[str]) -> int:
        """Count how many patterns match.

        Args:
            patterns: List of file patterns to check.

        Returns:
            Number of matching patterns.
        """
        return sum(1 for p in patterns if self._file_exists(p))

    def detect(self) -> ProjectDetection:
        """Detect project type and strategies.

        Returns:
            ProjectDetection with detected information.
        """
        # Count matches for each language
        scores = {
            ProjectType.PYTHON: self._count_matches(self.PYTHON_PATTERNS),
            ProjectType.NODE: self._count_matches(self.NODE_PATTERNS),
            ProjectType.GO: self._count_matches(self.GO_PATTERNS),
            ProjectType.RUST: self._count_matches(self.RUST_PATTERNS),
            ProjectType.JAVA: self._count_matches(self.JAVA_PATTERNS),
            ProjectType.DOTNET: self._count_matches(self.DOTNET_PATTERNS),
        }

        # Find the project type with highest score
        max_score = max(scores.values())
        if max_score == 0:
            return self._unknown_detection()

        project_type = max(scores, key=scores.get)
        confidence = min(1.0, max_score / 3.0)  # Normalize confidence

        # Get strategies for detected type
        return self._get_strategies(project_type, confidence)

    def _unknown_detection(self) -> ProjectDetection:
        """Return detection for unknown project type."""
        return ProjectDetection(
            project_type=ProjectType.UNKNOWN,
            install_strategy="",
            test_strategy="",
            build_strategy=None,
            artifact_locations=[],
            requires_services=False,
            system_deps_hint=[],
            confidence=0.0,
        )

    def _get_strategies(
        self, project_type: ProjectType, confidence: float
    ) -> ProjectDetection:
        """Get install/test strategies for a project type.

        Args:
            project_type: Detected project type.
            confidence: Detection confidence score.

        Returns:
            ProjectDetection with strategies.
        """
        if project_type == ProjectType.PYTHON:
            return self._python_strategies(confidence)
        elif project_type == ProjectType.NODE:
            return self._node_strategies(confidence)
        elif project_type == ProjectType.GO:
            return self._go_strategies(confidence)
        elif project_type == ProjectType.RUST:
            return self._rust_strategies(confidence)
        elif project_type == ProjectType.JAVA:
            return self._java_strategies(confidence)
        elif project_type == ProjectType.DOTNET:
            return self._dotnet_strategies(confidence)
        else:
            return self._unknown_detection()

    def _python_strategies(self, confidence: float) -> ProjectDetection:
        """Get strategies for Python projects."""
        install = "python -m pip install -e ."
        test = "python -m pytest -q"

        # Check for specific Python tools
        if self._file_exists("poetry.lock"):
            install = "poetry install --no-root"
            test = "poetry run pytest -q"
        elif self._file_exists("Pipfile"):
            install = "pipenv install --dev"
            test = "pipenv run pytest -q"
        elif self._file_exists("pyproject.toml"):
            # Check if it uses modern pip or poetry
            pyproject_path = os.path.join(self.repo_path, "pyproject.toml")
            if os.path.exists(pyproject_path):
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    if "[tool.poetry]" in content:
                        install = "poetry install --no-root"
                        test = "poetry run pytest -q"

        # Detect system deps hints
        sysdeps = []
        if self._file_exists("requirements.txt"):
            req_path = os.path.join(self.repo_path, "requirements.txt")
            with open(req_path, "r") as f:
                content = f.read().lower()
                if "psycopg" in content or "pg" in content:
                    sysdeps.append("libpq-dev")
                if "mysql" in content:
                    sysdeps.append("default-libmysqlclient-dev")
                if "pillow" in content or "pil" in content:
                    sysdeps.extend(["libjpeg-dev", "libpng-dev"])
                if "cryptography" in content:
                    sysdeps.append("libssl-dev")
                if "lxml" in content or "xml" in content:
                    sysdeps.append("libxml2-dev")

        return ProjectDetection(
            project_type=ProjectType.PYTHON,
            install_strategy=install,
            test_strategy=test,
            build_strategy=None,
            artifact_locations=["dist/", "build/", "*.egg-info"],
            requires_services=len(sysdeps) > 0,
            system_deps_hint=list(set(sysdeps)),
            confidence=confidence,
        )

    def _node_strategies(self, confidence: float) -> ProjectDetection:
        """Get strategies for Node.js projects."""
        install = "npm ci"
        test = "npm test"
        build = None

        # Check for yarn
        if self._file_exists("yarn.lock"):
            install = "yarn install --frozen-lockfile"
            test = "yarn test"
        elif self._file_exists("pnpm-lock.yaml"):
            install = "pnpm install --frozen-lockfile"
            test = "pnpm test"

        # Check for build script
        package_path = os.path.join(self.repo_path, "package.json")
        if os.path.exists(package_path):
            with open(package_path, "r") as f:
                content = f.read()
                if '"build"' in content:
                    build = "npm run build"
                    if self._file_exists("yarn.lock"):
                        build = "yarn build"
                    elif self._file_exists("pnpm-lock.yaml"):
                        build = "pnpm build"

        # Detect system deps
        sysdeps = []
        if os.path.exists(package_path):
            with open(package_path, "r") as f:
                content = f.read().lower()
                if "sharp" in content:
                    sysdeps.extend(["libvips-dev", "libjpeg-dev"])
                if "bcrypt" in content or "argon2" in content:
                    sysdeps.append("build-essential")
                if "node-sass" in content or "sass" in content:
                    sysdeps.append("build-essential")

        return ProjectDetection(
            project_type=ProjectType.NODE,
            install_strategy=install,
            test_strategy=test,
            build_strategy=build,
            artifact_locations=["dist/", "build/", "out/"],
            requires_services=len(sysdeps) > 0,
            system_deps_hint=list(set(sysdeps)),
            confidence=confidence,
        )

    def _go_strategies(self, confidence: float) -> ProjectDetection:
        """Get strategies for Go projects."""
        return ProjectDetection(
            project_type=ProjectType.GO,
            install_strategy="go mod download",
            test_strategy="go test ./...",
            build_strategy="go build ./...",
            artifact_locations=["bin/"],
            requires_services=False,
            system_deps_hint=[],
            confidence=confidence,
        )

    def _rust_strategies(self, confidence: float) -> ProjectDetection:
        """Get strategies for Rust projects."""
        return ProjectDetection(
            project_type=ProjectType.RUST,
            install_strategy="cargo fetch",
            test_strategy="cargo test",
            build_strategy="cargo build --release",
            artifact_locations=["target/release/", "target/debug/"],
            requires_services=False,
            system_deps_hint=[],
            confidence=confidence,
        )

    def _java_strategies(self, confidence: float) -> ProjectDetection:
        """Get strategies for Java projects."""
        install = ""
        test = ""
        build = None

        # Detect Maven vs Gradle
        if self._file_exists("pom.xml"):
            install = "mvn dependency:resolve"
            test = "mvn test"
            build = "mvn package"
        elif self._file_exists("build.gradle") or self._file_exists("build.gradle.kts"):
            install = "./gradlew dependencies"
            test = "./gradlew test"
            build = "./gradlew build"

        # Detect system deps
        sysdeps = []
        if self._file_exists("pom.xml"):
            pom_path = os.path.join(self.repo_path, "pom.xml")
            if os.path.exists(pom_path):
                with open(pom_path, "r") as f:
                    content = f.read().lower()
                    if "postgresql" in content or "pg" in content:
                        sysdeps.append("libpq-dev")

        return ProjectDetection(
            project_type=ProjectType.JAVA,
            install_strategy=install,
            test_strategy=test,
            build_strategy=build,
            artifact_locations=["target/", "build/libs/"],
            requires_services=len(sysdeps) > 0,
            system_deps_hint=list(set(sysdeps)),
            confidence=confidence,
        )

    def _dotnet_strategies(self, confidence: float) -> ProjectDetection:
        """Get strategies for .NET projects."""
        return ProjectDetection(
            project_type=ProjectType.DOTNET,
            install_strategy="dotnet restore",
            test_strategy="dotnet test",
            build_strategy="dotnet build --configuration Release",
            artifact_locations=["bin/", "obj/"],
            requires_services=False,
            system_deps_hint=[],
            confidence=confidence,
        )
