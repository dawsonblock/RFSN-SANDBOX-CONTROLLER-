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

Rules:
- Public GitHub only. No tokens. No credentials.
- If patch mode, diff must apply with git apply from repo root.
- No markdown. No commentary in diff.
- Minimal edits only. No refactors.
- Always edit implementation files, NEVER edit test files.
- For QuixBugs-style repos: edit python_programs/*.py, NOT python_testcases/*.py.
- Focus on fixing the bug in the implementation, not changing tests.
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