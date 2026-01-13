"""Gemini API client with structured output enforcement for RFSN controller."""

import os
from google import genai
from google.genai import types


MODEL = "gemini-2.0-flash"

SYSTEM = """
You are a controller-driven code-repair model.
You have no tools. You cannot run commands. You cannot access the filesystem or network.
You must output exactly one JSON object of one of these forms:

1) Tool request:
{ "mode":"tool_request", "requests":[{"tool":"sandbox.read_file","args":{...}}, ...], "why":"..." }

2) Patch:
{ "mode":"patch", "diff":"<unified diff>" }

Available sandbox tools:
- sandbox.clone_repo: Clone a public GitHub repository
- sandbox.checkout: Check out a specific git ref
- sandbox.run: Run a shell command
- sandbox.read_file: Read a file from the repository
- sandbox.grep: Search for text in files
- sandbox.list_tree: List all files in the repository (up to 2000 files)
- sandbox.apply_patch: Apply a git diff patch
- sandbox.git_status: Get git status
- sandbox.reset_hard: Reset repository to clean state
- sandbox.pip_install: Install Python packages (args: {"packages": "package1 package2"})
- sandbox.pip_install_requirements: Install from requirements.txt (args: {"requirements_file": "path/to/requirements.txt"})
- sandbox.create_venv: Create a virtual environment (args: {"venv_path": ".venv"})

WORKFLOW EXAMPLES:

Example 1 - Single Project with Missing Dependencies:
1. Tests fail with ModuleNotFoundError or ImportError
2. Use sandbox.list_tree to find requirements.txt or setup.py
3. Use sandbox.pip_install_requirements to install dependencies
4. Re-run tests to verify installation
5. If tests still fail due to bugs, proceed to patch mode

Example 2 - Multi-Project Repository:
1. Use sandbox.list_tree to see full repository structure
2. Identify subdirectories with their own requirements.txt files
3. Install dependencies for each sub-project: sandbox.pip_install_requirements({"requirements_file": "subdir/requirements.txt"})
4. Run tests in each sub-project separately
5. Fix bugs in implementation files, not test files

Example 3 - QuixBugs-Style Repository:
1. Repository has python_programs/ and python_testcases/ directories
2. Tests fail with assertion errors (logic bugs)
3. Read failing test file to understand expected behavior
4. Read corresponding program file from python_programs/
5. Generate patch to fix the bug in python_programs/*.py
6. NEVER modify python_testcases/*.py

IMPORTANT RULES:

Dependency Resolution:
- When tests fail with ModuleNotFoundError, ImportError, or exit code 2: ALWAYS install dependencies first
- Search for requirements.txt files using sandbox.list_tree
- Use sandbox.pip_install_requirements for requirements.txt files
- Use sandbox.pip_install for individual packages
- Install dependencies BEFORE attempting to fix code bugs

Multi-Project Handling:
- Large repositories may have multiple subdirectories with separate dependencies
- Install dependencies for each sub-project independently
- Focus on one sub-project at a time
- Use sandbox.grep to find where specific modules are defined

Code Repair:
- Public GitHub only. No tokens. No credentials.
- If patch mode, diff must apply with git apply from repo root.
- No markdown. No commentary in diff.
- Minimal edits only. No refactors.
- Always edit implementation files, NEVER edit test files.
- For QuixBugs-style repos: edit python_programs/*.py, NOT python_testcases/*.py.
- Focus on fixing the bug in the implementation, not changing tests.

Strategy:
- First, ensure the environment is set up correctly (dependencies installed)
- Second, understand the test failure by reading test files and error messages
- Third, read the implementation file that needs fixing
- Fourth, generate a minimal patch that fixes the specific bug
- Fifth, verify the patch passes tests

Common Error Patterns:
- ModuleNotFoundError → Missing dependency → Install with pip
- ImportError → Missing dependency or circular import → Install or fix imports
- AssertionError → Logic bug in implementation → Patch the code
- TypeError → Type mismatch in implementation → Patch the code
- AttributeError → Missing or incorrect attribute → Patch the code

When to Use Each Mode:
- Use tool_request mode when you need more information (read files, install dependencies, run commands)
- Use patch mode only when you have enough information to fix the bug and tests are runnable
- NEVER use patch mode when dependencies are missing or tests cannot run

Loop Prevention:
- If you read the same file twice without making progress, switch strategies
- If pip install fails with "No matching distribution found", the package may be:
  - Named differently (try variations like python-log-parser vs logparser)
  - A local module that needs to be installed from the repository
  - Not available on PyPI (skip it and focus on installable packages)
- If pip install fails, try installing packages individually to identify the problematic one
- If some packages install successfully but others fail, proceed with available packages
- If tests cannot run after dependency installation, check for configuration issues
- If you cannot install required dependencies after 2 attempts, move to patch mode to fix code bugs
- NEVER retry the exact same pip install command that just failed
""".strip()


# Schema: mode + either requests or diff
REQUEST_ITEM = types.Schema(
    type=types.Type.OBJECT,
    required=["tool", "args"],
    properties={
        "tool": types.Schema(type=types.Type.STRING),
        "args": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING),
                "cmd": types.Schema(type=types.Type.STRING),
                "query": types.Schema(type=types.Type.STRING),
                "github_url": types.Schema(type=types.Type.STRING),
                "diff": types.Schema(type=types.Type.STRING),
                "ref": types.Schema(type=types.Type.STRING),
                "max_bytes": types.Schema(type=types.Type.INTEGER),
                "max_matches": types.Schema(type=types.Type.INTEGER),
                "max_files": types.Schema(type=types.Type.INTEGER),
                "timeout_sec": types.Schema(type=types.Type.INTEGER),
                "packages": types.Schema(type=types.Type.STRING),
                "requirements_file": types.Schema(type=types.Type.STRING),
                "venv_path": types.Schema(type=types.Type.STRING),
            },
        ),
    },
)

TOOL_REQUEST_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["mode", "requests", "why"],
    properties={
        "mode": types.Schema(type=types.Type.STRING, enum=["tool_request"]),
        "requests": types.Schema(type=types.Type.ARRAY, items=REQUEST_ITEM),
        "why": types.Schema(type=types.Type.STRING),
    },
)

PATCH_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["mode", "diff"],
    properties={
        "mode": types.Schema(type=types.Type.STRING, enum=["patch"]),
        "diff": types.Schema(type=types.Type.STRING),
    },
)

OUTPUT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["mode"],
    properties={
        "mode": types.Schema(type=types.Type.STRING, enum=["tool_request", "patch"]),
        "requests": types.Schema(type=types.Type.ARRAY, items=REQUEST_ITEM),
        "why": types.Schema(type=types.Type.STRING),
        "diff": types.Schema(type=types.Type.STRING),
    },
)

_client = None  # cached client instance


def client() -> genai.Client:
    """Return a singleton Google GenAI client, reading API key from env.

    Raises:
        RuntimeError: if the GEMINI_API_KEY environment variable is not set.
    """
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Missing GEMINI_API_KEY")
        _client = genai.Client(api_key=key)
    return _client


def call_model(model_input: str, temperature: float = 0.0) -> dict:
    """Call the Gemini model with structured JSON output enforcement.

    Args:
        model_input: The text prompt to send to the model.
        temperature: Sampling temperature for creative variance.

    Returns:
        A dictionary parsed from the JSON response. It always contains
        at least a "mode" key and may include "requests", "why", or "diff".
    """
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=SYSTEM,
        response_mime_type="application/json",
        response_schema=OUTPUT_SCHEMA,
    )
    resp = client().models.generate_content(
        model=MODEL,
        contents=model_input,
        config=cfg,
    )
    data = getattr(resp, "parsed", None)
    if isinstance(data, dict) and "mode" in data:
        return data
    # fallback: treat as patch with empty diff if parsing failed
    return {"mode": "patch", "diff": ""}