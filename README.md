# RFSN Sandbox Controller

<div align="center">

![RFSN Logo](https://img.shields.io/badge/RFSN-Sandbox%20Controller-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python)
![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-purple?style=for-the-badge&logo=google)
![Docker](https://img.shields.io/badge/Docker-Supported-blue?style=for-the-badge&logo=docker)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

**A commercial-grade autonomous code repair agent with production hardening**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Docker](#docker) • [Examples](#examples) • [Architecture](#architecture)

</div>

---

## Overview

RFSN Sandbox Controller is an intelligent automated bug-fixing system designed for **real-world production repositories**. It combines:

- 🔧 **Docker-based isolation** for secure, reproducible repairs
- 🛡️ **Strict security hardening** with command allowlisting and URL validation
- 🧪 **Test-driven verification** as ground truth for fixes
- 🤖 **Gemini 2.0 Flash** for intelligent patch generation
- ⚡ **Parallel patch evaluation** using isolated git worktrees
- 🎯 **Multi-language support** (Python, Node.js, Rust, Go)
- 📦 **Evidence pack exports** for audit trails and fine-tuning
- 🚫 **Patch hygiene gates** to prevent dangerous changes

---

## Features

### Production Hardening

- **Docker Containerization**: Full isolation with non-root user and command allowlisting
- **Strict GitHub URL Validation**: Regex enforcement for `OWNER/REPO` format only
- **Command Allowlisting**: Blocks dangerous commands (`curl`, `wget`, `ssh`, `sudo`, etc.)
- **Patch Hygiene Gates**: Limits patch size (200 lines, 5 files) and blocks dangerous paths
- **Tool Request Quotas**: Prevents token waste (6 per response, 20 total per run)
- **Request Deduplication**: MD5 signature-based duplicate detection

### Core Capabilities

- **Parallel Patch Evaluation**: Tests 3 candidate patches simultaneously using `ThreadPoolExecutor`
- **Isolated Worktree Testing**: Each patch evaluated in a separate git worktree
- **Multi-Language Support**: Auto-detection for Python, Node.js, Rust, and Go projects
- **Evidence Pack Export**: Complete audit trails with diffs, test outputs, and metadata
- **Runtime Model Selection**: Configurable LLM via CLI flag or environment variable
- **Intelligent Policy Engine**: Regex-based error classification with confidence scoring
- **QuixBugs Integration**: Automatic detection and specialized file collection
- **Structured JSON Output**: Enforced schema for reliable LLM responses
- **Comprehensive Logging**: JSONL logs for full traceability

### Security & Safety

- **Public GitHub Only**: Enforces `https://github.com/OWNER/REPO` format
- **No Credentials**: Blocks tokens, passwords, and authentication
- **Path Traversal Protection**: Validates all file paths against forbidden prefixes
- **Shell Injection Prevention**: Uses `shlex.quote()` for all external command arguments
- **Forbidden Path Blocking**: Prevents edits to `vendor/`, `node_modules/`, `.git/`, etc.
- **Test Deletion Protection**: Blocks deletion of test files
- **Debug Pattern Detection**: Catches `print`, `pdb`, `breakpoint` in patches
- **Skip Pattern Detection**: Blocks `@pytest.mark.skip` and similar decorators

### Smart Heuristics

- **Error Classification**: Automatically categorizes errors (import, type, attribute, syntax, assertion)
- **Context Extraction**: Extracts line numbers, file paths, and error messages from tracebacks
- **Focus Test Selection**: Runs only the first failing test for faster feedback
- **Intent Selection**: Chooses repair strategy based on error type
- **Project Type Detection**: Automatically detects Python, Node.js, Rust, and Go projects

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

### Docker Setup (Recommended for Production)

```bash
# Build the Docker image
docker build -t rfsn .

# Run with environment variables
docker run --rm \
  -e GEMINI_API_KEY=your_api_key_here \
  -v $(pwd)/results:/sandbox/results \
  rfsn \
  --repo "https://github.com/OWNER/REPO" \
  --test "pytest -q"

# Or use docker-compose
docker-compose run quixbugs
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
| `--model` | Gemini model to use | `gemini-2.0-flash-exp` |
| `--fix-all` | Continue until all tests pass | `False` |
| `--max-steps-without-progress` | Early termination threshold | 10 |
| `--collect-finetuning-data` | Export evidence packs | `False` |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GEMINI_MODEL` | Default model (can be overridden by --model) | No |

### Example: Fix QuixBugs Bug

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/jkoppel/QuixBugs" \
  --test "pytest -q python_testcases/test_quicksort.py"
```

### Example: Fix All Bugs in Repository

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/OWNER/REPO" \
  --test "pytest -q" \
  --fix-all \
  --collect-finetuning-data
```

### Example: Use Different Model

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/OWNER/REPO" \
  --test "pytest -q" \
  --model "gemini-2.5-pro"
```

### Docker Usage

```bash
# Build image
docker build -t rfsn .

# Run with environment variables
docker run --rm \
  -e GEMINI_API_KEY=your_api_key_here \
  -v $(pwd)/results:/sandbox/results \
  rfsn \
  --repo "https://github.com/OWNER/REPO" \
  --test "pytest -q"

# Using docker-compose
docker-compose run quixbugs
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

### Evidence Pack Output

When `--collect-finetuning-data` is enabled, successful fixes generate:

```
results/
└── run_20260112_145022_a1b2c3d4/
    ├── winner.diff              # The winning patch
    ├── evidence_pack.json       # Full context and metadata
    └── metadata.json            # Structured metadata
```

**evidence_pack.json** includes:

- Failing test output (before fix)
- Passing test output (after fix)
- Files changed
- Lines added/removed
- Steps taken
- Model used
- Command log
- Tool requests

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

# View URL validation
cat /tmp/rfsn_sb_abc123/run.jsonl | jq 'select(.phase=="url_validation")'
```

---

## Architecture

### Components

```
rfsn_controller/
├── cli.py                   # Command-line interface
├── controller.py            # Main orchestration loop
├── sandbox.py               # Git & filesystem utilities
├── verifier.py              # Test runner integration
├── parsers.py               # Test output parsing
├── policy.py                # Heuristic policy engine
├── prompt.py                # Model input construction
├── llm_gemini.py            # Gemini API client
├── parallel.py              # Parallel patch evaluation
├── log.py                   # JSONL logging
├── url_validation.py        # GitHub URL validation
├── patch_hygiene.py         # Patch quality gates
├── tool_manager.py          # Tool request deduplication & quotas
├── project_detection.py     # Multi-language project detection
├── evidence_export.py       # Winner diff & evidence pack export
└── command_allowlist.py     # Command allowlisting for security
```

### Workflow

```
1. Validate GitHub URL
   ↓
2. Clone Repository (Docker sandbox)
   ↓
3. Detect Project Type (Python/Node/Rust/Go)
   ↓
4. Run Tests (measure baseline)
   ↓
5. Analyze Failure (policy)
   ↓
6. Collect Relevant Files
   ↓
7. Generate 3 Patches (LLM)
   ↓
8. Validate Patch Hygiene
   ↓
9. Evaluate in Parallel (worktrees)
   ↓
10. Apply Winner (if any)
   ↓
11. Export Evidence Pack (if enabled)
   ↓
12. Repeat or Success
```

### Security Layers

```
┌─────────────────────────────────────┐
│  GitHub URL Validation              │
│  - OWNER/REPO format only           │
│  - Blocks blob/, tree/, commit/     │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Docker Isolation                   │
│  - Non-root user                    │
│  - Command allowlist                │
│  - Blocked: curl, wget, ssh, sudo   │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Patch Hygiene Gates                │
│  - Max 200 lines, 5 files           │
│  - Forbidden paths                  │
│  - No test deletion                 │
│  - No debug prints                  │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Tool Request Management            │
│  - Deduplication                    │
│  - Quotas (6 per response, 20 total)│
└─────────────────────────────────────┘
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