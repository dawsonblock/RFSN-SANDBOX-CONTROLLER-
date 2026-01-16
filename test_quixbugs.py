"""Test QuixBugs integration with RFSN controller."""

import sys

import pytest
from tests._netgate import require_network

from rfsn_controller.sandbox import create_sandbox, clone_public_github
from rfsn_controller.verifier import run_tests
from rfsn_controller.controller import _collect_relevant_files_quixbugs


def _run_quixbugs_file_collection() -> bool:
    """Test that QuixBugs file collection works correctly."""
    # Create a test sandbox
    sb = create_sandbox()

    # Clone QuixBugs
    print("Cloning QuixBugs...")
    r = clone_public_github(
        sb,
        "https://github.com/jkoppel/QuixBugs"
    )
    if not r.get("ok"):
        print(f"Failed to clone: {r.get('error')}")
        return False
    print("✓ Cloned successfully")

    # Run a failing test
    print("\nRunning quicksort test...")
    test_cmd = "pytest -q python_testcases/test_quicksort.py"
    v = run_tests(sb, test_cmd, timeout_sec=30)

    print(f"Test ok: {v.ok}")
    print(f"Exit code: {v.exit_code}")
    print(f"Failing tests: {v.failing_tests}")

    if v.ok:
        print("Test passed - no bug to fix!")
        return True

    # Collect relevant files using QuixBugs heuristics
    print("\nCollecting relevant files...")
    tree = ["python_testcases/", "python_programs/"]
    files = _collect_relevant_files_quixbugs(sb, v, "\n".join(tree))

    print(f"Collected {len(files)} files:")
    for f in files:
        path = f.get("path", "unknown")
        content = f.get("content") if isinstance(f.get("content"), str) else f.get("text", "")
        text_len = len(content)
        print(f"  - {path} ({text_len} chars)")

    # Verify we got the expected files
    expected_files = [
        "python_testcases/test_quicksort.py",
        "python_programs/quicksort.py",
    ]

    collected_paths = [f.get("path") for f in files]
    print(f"\nExpected files: {expected_files}")
    print(f"Collected paths: {collected_paths}")

    success = all(ef in collected_paths for ef in expected_files)
    if success:
        print("\n✓ All expected files collected!")
    else:
        print("\n✗ Missing some expected files")

    return success


@pytest.mark.network
def test_quixbugs_file_collection():
    require_network()
    assert _run_quixbugs_file_collection()


if __name__ == "__main__":
    success = _run_quixbugs_file_collection()
    sys.exit(0 if success else 1)
