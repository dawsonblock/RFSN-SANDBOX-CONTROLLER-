"""Setup phase validation and reporting.

Tracks the success/failure of project setup operations and provides
hard bailout rules to prevent entering the repair loop when the project
isn't properly installed.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SetupStatus(Enum):
    """Overall setup status."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SetupReport:
    """Report on the success/failure of setup operations."""

    # Overall status
    status: SetupStatus = SetupStatus.SUCCESS

    # Dependency installation results
    pip_install_ok: bool = True
    pip_install_error: Optional[str] = None
    node_install_ok: bool = True
    node_install_error: Optional[str] = None
    go_install_ok: bool = True
    go_install_error: Optional[str] = None
    rust_install_ok: bool = True
    rust_install_error: Optional[str] = None
    java_install_ok: bool = True
    java_install_error: Optional[str] = None
    dotnet_install_ok: bool = True
    dotnet_install_error: Optional[str] = None

    # Lockfile detection
    has_lockfile: bool = False
    lockfile_path: Optional[str] = None

    # System dependencies
    sysdeps_installed: List[str] = field(default_factory=list)
    sysdeps_failed: List[str] = field(default_factory=list)
    sysdeps_blocked: List[str] = field(default_factory=list)
    missing_system_deps: List[str] = field(default_factory=list)

    # Test framework detection
    test_framework_detected: bool = False
    test_framework_name: Optional[str] = None
    tests_found: bool = False

    # Bailout reason if setup failed
    bailout_reason: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_bailout(self) -> bool:
        """Determine if we should bail out based on setup results."""
        return self.status != SetupStatus.SUCCESS

    def get_bailout_message(self) -> str:
        """Get a human-readable bailout message."""
        if self.bailout_reason:
            return self.bailout_reason

        reasons = []

        # Check dependency installation failures
        if not self.pip_install_ok:
            reasons.append(f"Python dependencies failed: {self.pip_install_error}")
        if not self.node_install_ok:
            reasons.append(f"Node dependencies failed: {self.node_install_error}")
        if not self.go_install_ok:
            reasons.append(f"Go dependencies failed: {self.go_install_error}")
        if not self.rust_install_ok:
            reasons.append(f"Rust dependencies failed: {self.rust_install_error}")
        if not self.java_install_ok:
            reasons.append(f"Java dependencies failed: {self.java_install_error}")
        if not self.dotnet_install_ok:
            reasons.append(f".NET dependencies failed: {self.dotnet_install_error}")

        # Check for missing system deps
        if self.missing_system_deps:
            reasons.append(f"Missing system dependencies: {', '.join(self.missing_system_deps)}")

        # Check for missing lockfile when dependencies exist
        if not self.has_lockfile and any([
            not self.pip_install_ok,
            not self.node_install_ok,
            not self.go_install_ok,
        ]):
            reasons.append("No lockfile found - dependency resolution may be inconsistent")

        if not reasons:
            return "Setup failed for unknown reasons"

        return "; ".join(reasons)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "status": self.status.value,
            "pip_install_ok": self.pip_install_ok,
            "pip_install_error": self.pip_install_error,
            "node_install_ok": self.node_install_ok,
            "node_install_error": self.node_install_error,
            "go_install_ok": self.go_install_ok,
            "go_install_error": self.go_install_error,
            "rust_install_ok": self.rust_install_ok,
            "rust_install_error": self.rust_install_error,
            "java_install_ok": self.java_install_ok,
            "java_install_error": self.java_install_error,
            "dotnet_install_ok": self.dotnet_install_ok,
            "dotnet_install_error": self.dotnet_install_error,
            "has_lockfile": self.has_lockfile,
            "lockfile_path": self.lockfile_path,
            "sysdeps_installed": self.sysdeps_installed,
            "sysdeps_failed": self.sysdeps_failed,
            "sysdeps_blocked": self.sysdeps_blocked,
            "missing_system_deps": self.missing_system_deps,
            "test_framework_detected": self.test_framework_detected,
            "test_framework_name": self.test_framework_name,
            "tests_found": self.tests_found,
            "bailout_reason": self.bailout_reason,
            "should_bailout": self.should_bailout(),
            "metadata": self.metadata,
        }


def create_setup_report(
    pip_result: Optional[Any] = None,
    node_result: Optional[Any] = None,
    go_result: Optional[Any] = None,
    rust_result: Optional[Any] = None,
    java_result: Optional[Any] = None,
    dotnet_result: Optional[Any] = None,
    lockfile_path: Optional[str] = None,
    sysdeps_installed: Optional[List[str]] = None,
    sysdeps_failed: Optional[List[str]] = None,
    sysdeps_blocked: Optional[List[str]] = None,
    test_framework_name: Optional[str] = None,
    tests_found: bool = False,
) -> SetupReport:
    """Create a SetupReport from component results.

    Args:
        pip_result: Result of pip install (has ok, stdout, stderr attributes)
        node_result: Result of npm install (has ok, stdout, stderr attributes)
        go_result: Result of go mod download (has ok, stdout, stderr attributes)
        rust_result: Result of cargo fetch (has ok, stdout, stderr attributes)
        java_result: Result of mvn/gradle (has ok, stdout, stderr attributes)
        dotnet_result: Result of dotnet restore (has ok, stdout, stderr attributes)
        lockfile_path: Path to lockfile if found
        sysdeps_installed: List of installed system packages
        sysdeps_failed: List of failed system packages
        sysdeps_blocked: List of blocked system packages
        test_framework_name: Name of detected test framework
        tests_found: Whether tests were found

    Returns:
        SetupReport with all results populated.
    """
    report = SetupReport()

    # Process pip install result
    if pip_result is not None:
        report.pip_install_ok = getattr(pip_result, "ok", True)
        if not report.pip_install_ok:
            report.pip_install_error = getattr(pip_result, "stderr", "")[:500]

    # Process node install result
    if node_result is not None:
        report.node_install_ok = getattr(node_result, "ok", True)
        if not report.node_install_ok:
            report.node_install_error = getattr(node_result, "stderr", "")[:500]

    # Process go install result
    if go_result is not None:
        report.go_install_ok = getattr(go_result, "ok", True)
        if not report.go_install_ok:
            report.go_install_error = getattr(go_result, "stderr", "")[:500]

    # Process rust install result
    if rust_result is not None:
        report.rust_install_ok = getattr(rust_result, "ok", True)
        if not report.rust_install_ok:
            report.rust_install_error = getattr(rust_result, "stderr", "")[:500]

    # Process java install result
    if java_result is not None:
        report.java_install_ok = getattr(java_result, "ok", True)
        if not report.java_install_ok:
            report.java_install_error = getattr(java_result, "stderr", "")[:500]

    # Process dotnet install result
    if dotnet_result is not None:
        report.dotnet_install_ok = getattr(dotnet_result, "ok", True)
        if not report.dotnet_install_ok:
            report.dotnet_install_error = getattr(dotnet_result, "stderr", "")[:500]

    # Lockfile
    if lockfile_path:
        report.has_lockfile = True
        report.lockfile_path = lockfile_path

    # System dependencies
    if sysdeps_installed:
        report.sysdeps_installed = sysdeps_installed
    if sysdeps_failed:
        report.sysdeps_failed = sysdeps_failed
    if sysdeps_blocked:
        report.sysdeps_blocked = sysdeps_blocked

    # Test framework
    if test_framework_name:
        report.test_framework_detected = True
        report.test_framework_name = test_framework_name
    report.tests_found = tests_found

    # Determine overall status
    critical_failures = [
        not report.pip_install_ok,
        not report.node_install_ok,
        not report.go_install_ok,
        not report.rust_install_ok,
        not report.java_install_ok,
        not report.dotnet_install_ok,
    ]

    if any(critical_failures):
        report.status = SetupStatus.FAILED
    elif sysdeps_failed or sysdeps_blocked:
        report.status = SetupStatus.PARTIAL

    return report
