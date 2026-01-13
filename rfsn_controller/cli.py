import argparse
import os
from dotenv import load_dotenv

from .controller import ControllerConfig, run_controller


def main() -> None:
    """Entry point for the CLI.

    Loads environment variables from .env, parses command-line arguments,
    constructs a ControllerConfig, and runs the controller.
    """
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        required=True,
        help="Public GitHub URL: https://github.com/OWNER/REPO",
    )
    parser.add_argument(
        "--test",
        default="pytest -q",
        help="Test command to satisfy",
    )
    parser.add_argument(
        "--ref",
        default=None,
        help="Optional branch/tag/sha to checkout before running",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=12,
        help="Maximum controller steps before giving up",
    )
    parser.add_argument(
        "--fix-all",
        action="store_true",
        help="Continue fixing bugs until all tests pass (no max steps limit)",
    )
    parser.add_argument(
        "--max-steps-without-progress",
        type=int,
        default=10,
        help="Early termination if no progress after N steps (default: 10)",
    )
    parser.add_argument(
        "--collect-finetuning-data",
        action="store_true",
        help="Collect successful patches for model fine-tuning",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("RFSN_MODEL", "deepseek-chat"),
        help="Model to use (default: deepseek-chat, or RFSN_MODEL env var)",
    )
    parser.add_argument(
        "--max-minutes",
        type=int,
        default=30,
        help="Total time budget in minutes (default: 30)",
    )
    parser.add_argument(
        "--install-timeout",
        type=int,
        default=300,
        help="Timeout for dependency installation in seconds (default: 300)",
    )
    parser.add_argument(
        "--focus-timeout",
        type=int,
        default=120,
        help="Timeout for focused test runs in seconds (default: 120)",
    )
    parser.add_argument(
        "--full-timeout",
        type=int,
        default=300,
        help="Timeout for full test suite runs in seconds (default: 300)",
    )
    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=40,
        help="Maximum total tool calls per run (default: 40)",
    )
    parser.add_argument(
        "--docker-image",
        default="python:3.11-slim",
        help="Docker image for sandboxed execution (default: python:3.11-slim)",
    )
    parser.add_argument(
        "--unsafe-host-exec",
        action="store_true",
        help="Allow running commands on host instead of Docker (DANGEROUS, not recommended)",
    )
    parser.add_argument(
        "--cpu",
        type=float,
        default=2.0,
        help="Docker CPU limit (default: 2.0)",
    )
    parser.add_argument(
        "--mem-mb",
        type=int,
        default=4096,
        help="Docker memory limit in MB (default: 4096)",
    )
    parser.add_argument(
        "--pids",
        type=int,
        default=256,
        help="Docker process ID limit (default: 256)",
    )
    parser.add_argument(
        "--docker-readonly",
        action="store_true",
        help="Mount repo as read-only with /tmp as tmpfs (more secure)",
    )
    parser.add_argument(
        "--lint-cmd",
        default=None,
        help="Lint command for verification (e.g., 'ruff check .')",
    )
    parser.add_argument(
        "--typecheck-cmd",
        default=None,
        help="Typecheck command for verification (e.g., 'mypy .')",
    )
    parser.add_argument(
        "--repro-cmd",
        default=None,
        help="Repro command for verification (e.g., 'pytest -q --repeat=2')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Clone + detect + setup + baseline test, then exit (no repair loop)",
    )
    parser.add_argument(
        "--project-type",
        default="auto",
        choices=["auto", "python", "node", "go", "rust", "java", "dotnet"],
        help="Project type (default: auto-detect)",
    )
    parser.add_argument(
        "--buildpack",
        default="auto",
        help="Docker buildpack image (default: auto-select based on project type)",
    )
    parser.add_argument(
        "--enable-sysdeps",
        action="store_true",
        help="Enable automatic system dependency installation (SYSDEPS phase)",
    )
    parser.add_argument(
        "--sysdeps-tier",
        default="4",
        choices=["0", "1", "2", "3", "4", "5", "6", "7"],
        help="Maximum APT tier for system dependencies (default: 4)",
    )
    parser.add_argument(
        "--sysdeps-max-packages",
        type=int,
        default=10,
        help="Maximum number of system packages to install (default: 10)",
    )
    parser.add_argument(
        "--build-cmd",
        default=None,
        help="Build command for verification (e.g., 'npm run build')",
    )
    args = parser.parse_args()

    cfg = ControllerConfig(
        github_url=args.repo,
        test_cmd=args.test,
        ref=args.ref,
        max_steps=args.steps,
        fix_all=args.fix_all,
        max_steps_without_progress=args.max_steps_without_progress,
        collect_finetuning_data=args.collect_finetuning_data,
        model=args.model,
        max_minutes=args.max_minutes,
        install_timeout=args.install_timeout,
        focus_timeout=args.focus_timeout,
        full_timeout=args.full_timeout,
        max_tool_calls=args.max_tool_calls,
        docker_image=args.docker_image,
        unsafe_host_exec=args.unsafe_host_exec,
        cpu=args.cpu,
        mem_mb=args.mem_mb,
        pids=args.pids,
        docker_readonly=args.docker_readonly,
        lint_cmd=args.lint_cmd,
        typecheck_cmd=args.typecheck_cmd,
        repro_cmd=args.repro_cmd,
        dry_run=args.dry_run,
        project_type=args.project_type,
        buildpack=args.buildpack,
        enable_sysdeps=args.enable_sysdeps,
        sysdeps_tier=int(args.sysdeps_tier),
        sysdeps_max_packages=args.sysdeps_max_packages,
        build_cmd=args.build_cmd,
    )
    result = run_controller(cfg)
    print(result)


if __name__ == "__main__":
    main()