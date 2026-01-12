# rfsn_controller package

"""
This package contains the core modules for the RFSN sandbox controller.

Modules include:
    - cli: command-line entry point
    - controller: the main RFSN controller loop
    - sandbox: utilities for managing disposable git sandboxes
    - verifier: test runner and result wrapper
    - parsers: helper functions for parsing test output
    - policy: heuristics for choosing repair intents and subgoals
    - prompt: helper for building model input strings
    - llm_gemini: Gemini model integration enforcing structured output
    - log: utility for writing JSONL logs
"""
