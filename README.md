# RFSN Sandbox Controller

<div align="center">

![RFSN Logo](https://img.shields.io/badge/RFSN-Sandbox%20Controller-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python)
![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-purple?style=for-the-badge&logo=google)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

**An autonomous code repair agent using parallel patch evaluation**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Examples](#examples) • [Architecture](#architecture)

</div>

---

## Overview

RFSN Sandbox Controller is an intelligent automated bug-fixing system that:

- 🔧 **Creates disposable sandboxes** for safe, isolated code repair
- 🧪 **Runs tests as ground truth** to verify fixes
- 🤖 **Leverages Gemini 2.0 Flash** for intelligent patch generation
- ⚡ **Evaluates patches in parallel** using isolated git worktrees
- ✅ **Applies only verified winners** that pass all tests
- 🎯 **Auto-detects QuixBugs repositories** with specialized heuristics

---

## Features

### Core Capabilities

- **Parallel Patch Evaluation**: Tests 3 candidate patches simultaneously using `ThreadPoolExecutor`
- **Isolated Worktree Testing**: Each patch evaluated in a separate git worktree to prevent interference
- **Intelligent Policy Engine**: Regex-based error classification with confidence scoring
- **QuixBugs Integration**: Automatic detection and specialized file collection for QuixBugs repositories
- **Structured JSON Output**: Enforced schema for reliable LLM responses
- **Comprehensive Logging**: JSONL logs for full traceability of repair attempts

### Security & Safety

- **Public GitHub Only**: Enforces `https://github.com/` URLs only
- **No Credentials**: Blocks tokens, passwords, and authentication
- **Path Traversal Protection**: Validates all file paths against forbidden prefixes
- **Shell Injection Prevention**: Uses `shlex.quote()` for all external command arguments

### Smart Heuristics

- **Error Classification**: Automatically categorizes errors (import, type, attribute, syntax, assertion)
- **Context Extraction**: Extracts line numbers, file paths, and error messages from tracebacks
- **Focus Test Selection**: Runs only the first failing test for faster feedback
- **Intent Selection**: Chooses repair strategy based on error type

---

## Installation

### Prerequisites

- Python 3.9 or higher
- Gemini API key ([Get one here](https://ai.google.dev/))

### Setup

```bash
# Clone the repository
git clone https://github.com/dawsonblock/RFSN-SANDBOX-CONTROLLER-.git
cd RFSN-SANDBOX-CONTROLLER-

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

---

## Usage

### Basic Command

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/OWNER/REPO" \
  --test "pytest -q tests/test_file.py" \
  --steps 12
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--repo` | Public GitHub repository URL | Required |
| `--test` | Test command to run | Required |
| `--steps` | Maximum repair iterations | 12 |
| `--ref` | Git branch or commit to checkout | `None` |

### Example: Fix QuixBugs Bug

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/jkoppel/QuixBugs" \
  --test "pytest -q python_testcases/test_quicksort.py"
```

---

## Examples

### QuixBugs QuickSort Fix

The controller successfully fixed the QuixBugs quicksort bug in **1 iteration**:

**Problem**: QuickSort only included pivot once, failing on duplicate values

**Solution**:
```diff
-    return lesser + [pivot] + greater
+    return lesser + [pivot for x in arr if x == pivot] + greater
```

**Result**: All 13 tests passing ✅

### Output Structure

```json
{
  "ok": true,
  "sandbox": "/tmp/rfsn_sb_abc123",
  "repo_dir": "/tmp/rfsn_sb_abc123/repo"
}
```

### Log Analysis

Logs are written as JSONL in the sandbox directory:

```bash
# View repair steps
cat /tmp/rfsn_sb_abc123/run.jsonl | jq '.phase'

# Check model responses
cat /tmp/rfsn_sb_abc123/run.jsonl | jq 'select(.phase=="model")'

# See patch evaluations
cat /tmp/rfsn_sb_abc123/run.jsonl | jq 'select(.phase=="candidate_eval")'
```

---

## Architecture

### Components

```
rfsn_controller/
├── cli.py              # Command-line interface
├── controller.py       # Main orchestration loop
├── sandbox.py          # Git & filesystem utilities
├── verifier.py         # Test runner integration
├── parsers.py          # Test output parsing
├── policy.py           # Heuristic policy engine
├── prompt.py           # Model input construction
├── llm_gemini.py       # Gemini API client
├── parallel.py         # Parallel patch evaluation
└── log.py              # JSONL logging
```

### Workflow

```
1. Clone Repository
   ↓
2. Run Tests (measure)
   ↓
3. Analyze Failure (policy)
   ↓
4. Collect Relevant Files
   ↓
5. Generate 3 Patches (LLM)
   ↓
6. Evaluate in Parallel (worktrees)
   ↓
7. Apply Winner (if any)
   ↓
8. Repeat or Success
```

### QuixBugs Mode

When a QuixBugs repository is detected, the controller:

1. **Maps test files to program files**: `test_quicksort.py` → `quicksort.py`
2. **Collects both files**: Test + implementation
3. **Guides LLM**: Edit `python_programs/*.py`, NOT `python_testcases/*.py`

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |

### Model Settings

- **Model**: `gemini-2.0-flash`
- **Temperatures**: `[0.0, 0.2, 0.4]` (3 parallel evaluations)
- **Timeout**: 90s (focus test), 180s (full test)
- **Max Steps**: 12 (configurable)

---

## Testing

### Run Test Suite

```bash
pytest test_improvements.py -v
```

### QuixBugs Integration Test

```bash
python test_quixbugs_direct.py
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## License

MIT License - see LICENSE file for details

---

## Acknowledgments

- **QuixBugs**: Benchmark dataset for program repair
- **Google Gemini**: LLM for intelligent patch generation
- **pytest**: Testing framework integration

---

<div align="center">

**Built with ❤️ for automated code repair**

[Report Bug](https://github.com/dawsonblock/RFSN-SANDBOX-CONTROLLER-/issues) • [Request Feature](https://github.com/dawsonblock/RFSN-SANDBOX-CONTROLLER-/issues)

</div>