# RFSN Sandbox Controller (public GitHub)

This controller:
- creates a disposable sandbox
- clones a public GitHub repo
- runs tests as truth
- asks Gemini 3 Flash for either tool requests or patches
- evaluates patches in isolated git worktrees
- applies only verified winners

## Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set GEMINI_API_KEY in .env

## Run
python -m rfsn_controller.cli \
  --repo "https://github.com/jkoppel/QuixBugs" \
  --test "pytest -q python_testcases/test_quicksort.py" \
  --steps 12

## Logs
A JSONL log is written inside the sandbox temp folder printed in the result.