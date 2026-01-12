import argparse
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
    args = parser.parse_args()

    cfg = ControllerConfig(
        github_url=args.repo,
        test_cmd=args.test,
        ref=args.ref,
        max_steps=args.steps,
        fix_all=args.fix_all,
        max_steps_without_progress=args.max_steps_without_progress,
        collect_finetuning_data=args.collect_finetuning_data,
    )
    result = run_controller(cfg)
    print(result)


if __name__ == "__main__":
    main()