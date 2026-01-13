"""Unit tests for v3 multi-language support components."""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from rfsn_controller.project_detector import ProjectDetector, ProjectType
from rfsn_controller.language_templates import Language, get_templates, get_buildpack_image
from rfsn_controller.apt_whitelist import AptWhitelist, AptTier, DEFAULT_WHITELIST
from rfsn_controller.sysdeps_installer import SysdepsInstaller, SysdepsResult
from rfsn_controller.trace_parser import TraceParser, Language as TraceLanguage
from rfsn_controller.goals import GoalFactory, GoalSetFactory, GoalType


class TestProjectDetector:
    """Tests for multi-language project detection."""

    def test_detect_python_project(self):
        """Test detection of Python project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Python project files
            Path(tmpdir, "requirements.txt").write_text("pytest\nrequests\n")
            Path(tmpdir, "setup.py").write_text("from setuptools import setup\n")

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.PYTHON
            assert "pytest" in detection.install_strategy or "pip" in detection.install_strategy
            assert detection.confidence > 0

    def test_detect_node_project(self):
        """Test detection of Node.js project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Node project files
            Path(tmpdir, "package.json").write_text('{"name": "test", "scripts": {"test": "jest"}}\n')
            Path(tmpdir, "yarn.lock").write_text("")

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.NODE
            assert "npm" in detection.install_strategy or "yarn" in detection.install_strategy

    def test_detect_go_project(self):
        """Test detection of Go project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Go project files
            Path(tmpdir, "go.mod").write_text("module test\n\ngo 1.22\n")
            Path(tmpdir, "go.sum").write_text("")

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.GO
            assert "go mod" in detection.install_strategy

    def test_detect_rust_project(self):
        """Test detection of Rust project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Rust project files
            Path(tmpdir, "Cargo.toml").write_text('[package]\nname = "test"\nversion = "0.1.0"\n')
            Path(tmpdir, "Cargo.lock").write_text("")

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.RUST
            assert "cargo" in detection.install_strategy

    def test_detect_java_maven_project(self):
        """Test detection of Java Maven project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Java Maven project files
            Path(tmpdir, "pom.xml").write_text('<project><modelVersion>4.0.0</modelVersion></project>\n')

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.JAVA
            assert "mvn" in detection.install_strategy

    def test_detect_java_gradle_project(self):
        """Test detection of Java Gradle project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Java Gradle project files
            Path(tmpdir, "build.gradle").write_text("plugins { id 'java' }\n")

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.JAVA
            assert "gradle" in detection.install_strategy

    def test_detect_dotnet_project(self):
        """Test detection of .NET project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .NET project files
            Path(tmpdir, "test.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"></Project>\n')

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.DOTNET
            assert "dotnet" in detection.install_strategy

    def test_detect_unknown_project(self):
        """Test detection of unknown project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Empty directory
            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert detection.project_type == ProjectType.UNKNOWN
            assert detection.confidence == 0.0

    def test_python_system_deps_hint(self):
        """Test Python system dependency hints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Python project with psycopg2
            Path(tmpdir, "requirements.txt").write_text("psycopg2-binary\nPillow\ncryptography\n")

            detector = ProjectDetector(tmpdir)
            detection = detector.detect()

            assert "libpq-dev" in detection.system_deps_hint
            assert any("libjpeg" in dep or "libpng" in dep for dep in detection.system_deps_hint)


class TestLanguageTemplates:
    """Tests for language command templates."""

    def test_get_python_templates(self):
        """Test getting Python templates."""
        templates = get_templates(Language.PYTHON)

        assert templates.install == "python -m pip install -e ."
        assert templates.test == "python -m pytest -q"
        assert templates.lint == "ruff check ."
        assert templates.typecheck == "mypy ."

    def test_get_node_templates(self):
        """Test getting Node.js templates."""
        templates = get_templates(Language.NODE)

        assert templates.install == "npm ci"
        assert templates.test == "npm test"
        assert templates.build == "npm run build"

    def test_get_go_templates(self):
        """Test getting Go templates."""
        templates = get_templates(Language.GO)

        assert templates.install == "go mod download"
        assert templates.test == "go test ./..."
        assert templates.build == "go build ./..."

    def test_get_rust_templates(self):
        """Test getting Rust templates."""
        templates = get_templates(Language.RUST)

        assert templates.install == "cargo fetch"
        assert templates.test == "cargo test"
        assert templates.build == "cargo build --release"

    def test_get_buildpack_image(self):
        """Test getting buildpack images."""
        assert get_buildpack_image(Language.PYTHON) == "python:3.11-slim"
        assert get_buildpack_image(Language.NODE) == "node:20-slim"
        assert get_buildpack_image(Language.GO) == "golang:1.22-slim"
        assert get_buildpack_image(Language.RUST) == "rust:1.78-slim"
        assert get_buildpack_image(Language.JAVA) == "eclipse-temurin:17-jdk"
        assert get_buildpack_image(Language.DOTNET) == "mcr.microsoft.com/dotnet/sdk:8.0"


class TestAptWhitelist:
    """Tests for APT package whitelist."""

    def test_default_whitelist_allows_common_packages(self):
        """Test that default whitelist allows common packages."""
        assert DEFAULT_WHITELIST.is_allowed("build-essential")
        assert DEFAULT_WHITELIST.is_allowed("libssl-dev")
        assert DEFAULT_WHITELIST.is_allowed("libpq-dev")
        assert DEFAULT_WHITELIST.is_allowed("libjpeg-dev")

    def test_whitelist_blocks_forbidden_packages(self):
        """Test that whitelist blocks forbidden packages."""
        assert not DEFAULT_WHITELIST.is_allowed("postgresql")
        assert not DEFAULT_WHITELIST.is_allowed("redis-server")
        assert not DEFAULT_WHITELIST.is_allowed("sudo")
        assert not DEFAULT_WHITELIST.is_allowed("docker.io")

    def test_whitelist_filters_packages(self):
        """Test filtering packages against whitelist."""
        packages = ["build-essential", "libssl-dev", "postgresql", "nginx"]
        allowed, blocked = DEFAULT_WHITELIST.filter_allowed(packages)

        assert "build-essential" in allowed
        assert "libssl-dev" in allowed
        assert "postgresql" in blocked
        assert "nginx" in blocked

    def test_whitelist_limits_packages(self):
        """Test that whitelist respects max packages limit."""
        whitelist = AptWhitelist(max_packages=2, max_tier=AptTier.TIER_0)

        assert whitelist.check_within_limits(["build-essential", "pkg-config"])
        assert not whitelist.check_within_limits(["build-essential", "pkg-config", "git"])

    def test_tier_limits(self):
        """Test that tier limits work correctly."""
        whitelist = AptWhitelist(max_packages=100, max_tier=AptTier.TIER_1)

        assert whitelist.is_allowed("build-essential")  # Tier 0
        assert whitelist.is_allowed("libssl-dev")  # Tier 1
        assert not whitelist.is_allowed("libpq-dev")  # Tier 2


class TestSysdepsInstaller:
    """Tests for system dependency installer."""

    def test_parse_error_for_packages(self):
        """Test parsing error output for missing packages."""
        installer = SysdepsInstaller(dry_run=True)

        error = "E: Unable to locate package libpq-dev"
        packages = installer.parse_error_for_packages(error)
        assert "libpq-dev" in packages

        error = "fatal error: openssl/ssl.h: No such file"
        packages = installer.parse_error_for_packages(error)
        assert any("ssl" in pkg.lower() for pkg in packages)

    def test_install_dry_run(self):
        """Test dry run installation."""
        installer = SysdepsInstaller(dry_run=True)

        result = installer.install(
            packages=["build-essential", "libssl-dev"],
            hints=[],
        )

        assert result.success
        assert "build-essential" in result.installed_packages
        assert "libssl-dev" in result.installed_packages

    def test_install_blocks_unapproved_packages(self):
        """Test that unapproved packages are blocked."""
        installer = SysdepsInstaller(dry_run=True)

        result = installer.install(
            packages=["build-essential", "postgresql"],
            hints=[],
        )

        assert result.success
        assert "build-essential" in result.installed_packages
        assert "postgresql" in result.blocked_packages

    def test_install_respects_limits(self):
        """Test that installation respects limits."""
        whitelist = AptWhitelist(max_packages=2, max_tier=AptTier.TIER_0)
        installer = SysdepsInstaller(whitelist=whitelist, dry_run=True)

        result = installer.install(
            packages=["build-essential", "pkg-config", "git"],
            hints=[],
        )

        assert not result.success
        assert "Too many packages" in result.error_message


class TestTraceParser:
    """Tests for multi-language trace parsing."""

    def test_detect_python_trace(self):
        """Test detecting Python traceback."""
        parser = TraceParser()
        trace = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    foo()
  File "test.py", line 5, in foo
    bar()
ZeroDivisionError: division by zero"""

        language = parser.detect_language(trace)
        assert language == TraceLanguage.PYTHON

    def test_detect_node_trace(self):
        """Test detecting Node.js stack trace."""
        parser = TraceParser()
        trace = """Error: something went wrong
    at Module.foo (/path/to/file.js:10:5)
    at Module.bar (/path/to/file.js:5:15)"""

        language = parser.detect_language(trace)
        assert language == TraceLanguage.NODE

    def test_detect_java_trace(self):
        """Test detecting Java exception."""
        parser = TraceParser()
        trace = """Exception in thread "main" java.lang.NullPointerException
    at com.example.Class.method(Class.java:10)
    at com.example.Main.main(Main.java:5)"""

        language = parser.detect_language(trace)
        assert language == TraceLanguage.JAVA

    def test_detect_go_trace(self):
        """Test detecting Go panic."""
        parser = TraceParser()
        trace = """panic: runtime error
goroutine 1 [running]:
main.foo()
        /path/to/file.go:10 +0x123"""

        language = parser.detect_language(trace)
        assert language == TraceLanguage.GO

    def test_detect_rust_trace(self):
        """Test detecting Rust panic."""
        parser = TraceParser()
        trace = """thread 'main' panicked at 'assertion failed', src/main.rs:10:5"""

        language = parser.detect_language(trace)
        assert language == TraceLanguage.RUST

    def test_parse_python_trace(self):
        """Test parsing Python traceback."""
        parser = TraceParser()
        trace = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    foo()
  File "test.py", line 5, in foo
    bar()
ZeroDivisionError: division by zero"""

        parsed = parser.parse(trace)

        assert parsed.language == TraceLanguage.PYTHON
        assert parsed.error_type == "ZeroDivisionError"
        assert len(parsed.frames) >= 2
        assert parsed.frames[0].filepath == "test.py"
        assert parsed.frames[0].line_number == 10

    def test_extract_files_from_trace(self):
        """Test extracting files from trace."""
        parser = TraceParser()
        trace = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    foo()
  File "other.py", line 5, in foo
    bar()"""

        files = parser.extract_files_to_examine(trace)

        assert "test.py" in files
        assert "other.py" in files


class TestGoals:
    """Tests for goal types and factories."""

    def test_create_test_goal(self):
        """Test creating a test goal."""
        goal = GoalFactory.create_test_goal("pytest -q")

        assert goal.goal_type == GoalType.TEST
        assert goal.command == "pytest -q"
        assert goal.required is True

    def test_create_build_goal(self):
        """Test creating a build goal."""
        goal = GoalFactory.create_build_goal("npm run build")

        assert goal.goal_type == GoalType.BUILD
        assert goal.command == "npm run build"
        assert goal.required is True

    def test_create_lint_goal(self):
        """Test creating a lint goal."""
        goal = GoalFactory.create_lint_goal("ruff check .", required=False)

        assert goal.goal_type == GoalType.LINT
        assert goal.required is False

    def test_create_typecheck_goal(self):
        """Test creating a typecheck goal."""
        goal = GoalFactory.create_typecheck_goal("mypy .")

        assert goal.goal_type == GoalType.TYPECHECK
        assert goal.command == "mypy ."

    def test_create_repro_goal(self):
        """Test creating a repro goal."""
        goal = GoalFactory.create_repro_goal("python repro.py")

        assert goal.goal_type == GoalType.REPRO
        assert goal.command == "python repro.py"

    def test_goal_set_for_python(self):
        """Test creating goal set for Python."""
        goal_set = GoalSetFactory.for_python(
            test_cmd="pytest -q",
            lint_cmd="ruff check .",
            typecheck_cmd="mypy .",
        )

        assert goal_set.primary_goal.goal_type == GoalType.TEST
        assert len(goal_set.verification_goals) == 2

    def test_goal_set_for_node(self):
        """Test creating goal set for Node.js."""
        goal_set = GoalSetFactory.for_node(
            test_cmd="npm test",
            build_cmd="npm run build",
        )

        assert goal_set.primary_goal.goal_type == GoalType.TEST
        assert any(g.goal_type == GoalType.BUILD for g in goal_set.verification_goals)

    def test_goal_set_for_build_only(self):
        """Test creating goal set for build-only project."""
        goal_set = GoalSetFactory.for_build_only(
            build_cmd="cargo build",
        )

        assert goal_set.primary_goal.goal_type == GoalType.BUILD

    def test_get_required_goals(self):
        """Test getting only required goals."""
        goal_set = GoalSetFactory.for_python(
            test_cmd="pytest -q",
            lint_cmd="ruff check .",
        )

        required = goal_set.get_required_goals()
        assert len(required) == 1  # Only test is required
        assert required[0].goal_type == GoalType.TEST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
