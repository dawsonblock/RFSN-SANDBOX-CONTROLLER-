"""Test runner integration for the RFSN controller."""

from dataclasses import dataclass, field
from typing import List

from .sandbox import Sandbox, run_cmd
from .parsers import parse_pytest_failures, error_signature


@dataclass
class VerifyResult:
    """Wrapper for test run results."""

    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    failing_tests: List[str] = field(default_factory=list)
    sig: str = ""


def run_tests(sb: Sandbox, test_cmd: str, timeout_sec: int = 120) -> VerifyResult:
    """Run a test command and return structured results.

    Args:
        sb: The sandbox in which to run the tests.
        test_cmd: Command line to invoke the tests (e.g. "pytest -q").
        timeout_sec: Maximum seconds to wait for the command.

    Returns:
        A VerifyResult with status and details.
    """
    r = run_cmd(sb, test_cmd, timeout_sec=timeout_sec)
    out = (r.get("stdout") or "") + (r.get("stderr") or "")
    fails = parse_pytest_failures(out)
    sig = error_signature(r.get("stdout") or "", r.get("stderr") or "")
    try:
        exit_code = int(r.get("exit_code") or 1)
    except (ValueError, TypeError):
        exit_code = 1
    return VerifyResult(
        ok=bool(r.get("ok")),
        exit_code=exit_code,
        stdout=r.get("stdout") or "",
        stderr=r.get("stderr") or "",
        failing_tests=fails,
        sig=sig,
    )