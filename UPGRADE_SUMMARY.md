# RFSN-CODE Deep Extraction Upgrade - Implementation Summary

## Overview

This upgrade implements the comprehensive RFSN-CODE system prompt and shell idiom validation as specified in the problem statement. The changes align the model's behavior with the controller's actual execution constraints (shell=False, command allowlist, verification requirements).

## Changes Implemented

### 1. System Prompt Upgrade (llm_deepseek.py & llm_gemini.py)

**Changed**: Complete replacement of system prompts with unified comprehensive RFSN-CODE prompt

**Key Sections**:
- **NON-NEGOTIABLE REALITY**: Explicitly states NO SHELL rule, command allowlist constraints, tool quotas, and mode-dependent patch hygiene
- **SHELL-LESS COMMAND RULES**: Teaches the model to never use cd, &&, ||, pipes, redirects, command substitution, or inline env vars
- **ALLOWLIST-FIRST BEHAVIOR**: Model must verify commands work rather than assume they're available
- **FEATURE-MODE VERIFICATION RULES**: completion_status="complete" requires hard verification evidence (tests passed, smoke check, or contract check)
- **HYGIENE PROFILE BEHAVIOR**: Explains repair mode (strict, small changes) vs feature mode (larger, multiple files acceptable)
- **STALL / RETRY POLICY**: Prevents repeated failed actions

**Why**: The previous prompt didn't explicitly forbid shell idioms or teach the model about shell=False execution. Models would repeatedly generate invalid compound commands (e.g., "npm install && npm test"), wasting quota.

### 2. Shell Idiom Validation (model_validator.py)

**Changed**: Enhanced `_validate_tool_request` to detect and reject shell idioms in `sandbox.run` commands

**Detection Patterns**:
- `&&` (command chaining)
- `||` (OR operator)
- `|` (pipe)
- `>` (output redirect)
- `<` (input redirect)
- `$(...)` (command substitution)
- `` `...` `` (backtick substitution)
- `cd` command
- Inline env vars (`FOO=1 cmd`)

**Corrective Feedback**: When a shell idiom is detected, the validator returns a fallback tool_request with helpful guidance:
- Explains that sandbox uses shell=False
- Instructs to split compound commands into separate tool_request calls
- Suggests using explicit paths instead of cd
- Recommends config files or flags instead of inline env vars

**Why**: Validator-level enforcement prevents quota waste and guides the model toward correct single-command patterns.

### 3. Controller Feature Summary Handling (controller.py)

**Status**: Already correct, no changes needed

**Verified**:
- When feature_summary has completion_status="complete", controller sets `current_phase = Phase.FINAL_VERIFY` and breaks from loop
- FINAL_VERIFY phase runs full test suite
- If tests fail, transitions to BAILOUT
- No early returns that skip verification

**Why**: The problem statement required verification-grounded completion. The controller was already implemented correctly.

### 4. Comprehensive Testing

**Added**: `tests/test_shell_idiom_validation.py` (27 tests)
- Test rejection of each shell idiom type
- Test acceptance of valid single commands
- Test corrective feedback content
- Test validator method `_detect_shell_idioms` directly

**Updated**: `tests/test_prompt_upgrade.py` (33 tests)
- Updated to match new prompt structure
- Tests verify key sections exist (MANDATORY WORKFLOW, SHELL-LESS COMMAND RULES, etc.)
- Tests verify semantic content (minimal changes, verification requirements, evidence-based)

**Test Results**: All 171 tests passing

## Impact

### Before
- Model frequently generated compound commands with shell idioms
- Commands failed at sandbox execution with cryptic errors
- Quota wasted on retry loops
- Feature mode could declare "complete" without verification

### After
- Model receives explicit instruction about NO SHELL constraint
- Invalid commands rejected at validation layer with corrective feedback
- Model guided toward correct single-command patterns
- Feature mode requires verification evidence for completion

## Files Modified

1. `rfsn_controller/llm_deepseek.py` - New comprehensive SYSTEM prompt
2. `rfsn_controller/llm_gemini.py` - New comprehensive SYSTEM prompt (same as DeepSeek)
3. `rfsn_controller/model_validator.py` - Shell idiom detection and rejection
4. `tests/test_shell_idiom_validation.py` - New test suite (27 tests)
5. `tests/test_prompt_upgrade.py` - Updated tests for new prompt structure

## Verification

- [x] All 27 shell idiom validation tests pass
- [x] All 33 prompt upgrade tests pass
- [x] All 171 total tests pass
- [x] No regressions in existing functionality
- [x] Controller feature_summary handling verified correct

## Next Steps (Optional Enhancements)

1. **Verify Commands List**: Add optional `verify_cmds` config for multi-step verification (build + test + lint)
2. **Configurable Hygiene Caps**: Allow per-run tuning of max_lines_changed and max_files_changed
3. **Lockfile Behavior**: Add controlled conditions for when lockfile changes are permitted
4. **Language-Specific Test Plans**: Extend buildpacks with language-specific verification strategies

## Summary

This upgrade successfully implements the three critical fixes from the problem statement:

1. ✅ **System Prompt Upgrade**: Comprehensive RFSN-CODE prompt with explicit NO SHELL teaching
2. ✅ **Shell Idiom Rejection**: Validator-level enforcement with corrective feedback
3. ✅ **Verification-Grounded Completion**: Controller properly enforces verification before accepting completion

The changes are minimal, surgical, and well-tested, with no regressions to existing functionality.
