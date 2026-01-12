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
    args = parser.parse_args()

    cfg = ControllerConfig(
        github_url=args.repo,
        test_cmd=args.test,
        ref=args.ref,
        max_steps=args.steps,
    )
    result = run_controller(cfg)
    print(result)


if __name__ == "__main__":
    main()