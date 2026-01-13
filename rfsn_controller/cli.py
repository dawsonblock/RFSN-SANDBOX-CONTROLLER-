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
        default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
        help="Gemini model to use (default: gemini-2.0-flash-exp, or GEMINI_MODEL env var)",
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
    )
    result = run_controller(cfg)
    print(result)


if __name__ == "__main__":
    main()