# RFSN Coding Agent Prompt Upgrade - Implementation Documentation

**Date**: January 15, 2026  
**Status**: ✅ Complete

---

## Overview

This document describes the implementation of the upgraded RFSN Coding Agent system prompt, which transforms the agent into a production-grade, controller-governed software engineering system.

---

## Changes Made

### Files Modified

1. **`rfsn_controller/llm_gemini.py`**
   - Replaced the `SYSTEM` prompt constant with a comprehensive, production-grade prompt
   - Increased from ~3,000 characters to ~7,150 characters
   - Maintained compatibility with existing Gemini API schema

2. **`rfsn_controller/llm_deepseek.py`**
   - Replaced the `SYSTEM` prompt constant with a comprehensive, production-grade prompt
   - Increased from ~2,800 characters to ~7,413 characters
   - Maintained compatibility with existing DeepSeek API schema
   - Added explicit OUTPUT FORMAT section for DeepSeek-specific requirements

3. **`tests/test_prompt_upgrade.py`** (New)
   - Created 33 comprehensive tests to validate prompt structure and semantics
   - Tests cover both Gemini and DeepSeek prompts
   - Validates all key sections and requirements

---

## New Prompt Architecture

### Core Sections

The upgraded prompt is organized into clear, hierarchical sections:

```
═══════════════════════════════════════════════════════════════
RFSN-CODE: CONTROLLER-GOVERNED SOFTWARE ENGINEERING AGENT
═══════════════════════════════════════════════════════════════

1. CORE OPERATING CONTRACT
   - tool_request mode
   - patch mode
   - feature_summary mode

2. YOUR MISSION
   - Definition of Done (5 criteria)

3. MANDATORY WORKFLOW
   - 6-step process: ground truth → inspect → plan → implement → verify → finish

4. ENGINEERING HEURISTICS (REQUIRED)
   - 5 key principles for code changes

5. AVAILABLE SANDBOX TOOLS
   - Complete list of sandbox.* tools with args

6. TOOLING RULES
   - Constraints on shell usage and command execution

7. ANTI-PATTERNS (AUTOMATIC FAILURE)
   - 6 behaviors that lead to automatic failure

8. WHEN BLOCKED
   - Guidance for impossible progress situations

9. FINAL NOTE
   - Summary of agent's role and principles
```

---

## Key Features

### 1. Controller-First Architecture

```
You are RFSN-CODE, a controller-governed software engineering agent.

You do not control the filesystem, the network, or execution directly.
You operate exclusively through a restricted sandbox controlled by the RFSN Controller.
```

**Why this matters:**
- Clearly establishes the agent's bounded execution environment
- Prevents hallucinations about direct file system or network access
- Aligns with the actual architecture where the controller mediates all actions

### 2. Strict JSON-Only Output

```
You may produce ONLY valid JSON in exactly one of the following modes:

1) tool_request
2) patch
3) feature_summary   (feature mode only)

Any output outside these modes is invalid.
```

**Why this matters:**
- Enforces compatibility with `ModelOutputValidator`
- Prevents markdown, explanations, or other non-JSON output
- Reduces parsing errors and validation failures

### 3. Definition of Done

```
Default Definition of Done:
1) Correct behavior for the task
2) Verification exists (tests, runnable example, or contract check)
3) Existing tests pass
4) No unrelated changes
5) Clear, predictable failure behavior
```

**Why this matters:**
- Provides clear completion criteria
- Prevents "done but not verified" scenarios
- Encourages test-driven development
- Discourages scope creep

### 4. Mandatory Workflow

```
1) Establish ground truth
   - Identify failing tests, missing behavior, or feature gap.
   - Locate the owning modules and interfaces.

2) Inspect before acting
   - Read README / docs relevant to the task.
   - Use grep to find entry points and patterns.
   - Read the smallest set of files needed to understand behavior.

3) Plan internally (briefly)
   - What is wrong or missing?
   - What is the smallest correct change?
   - What verification will prove it works?

4) Implement
   - Produce a focused patch.
   - Follow existing project conventions.

5) Verify
   - Request test execution or equivalent verification.
   - If it fails, adjust based on evidence. Do not guess.

6) Finish
   - Stop when the Definition of Done is satisfied.
   - In feature mode, emit feature_summary.
```

**Why this matters:**
- Prevents "patch first, understand later" behavior
- Encourages evidence-based decision making
- Reduces wasted tool requests on wrong approaches
- Ensures verification is always performed

### 5. Engineering Heuristics

```
- Prefer explicit behavior over clever abstractions.
- Match existing architecture and style.
- Add tests near existing tests; follow their patterns.
- If behavior is ambiguous, search call sites and tests.
- If a fix is risky, add a guard + test instead of refactoring.
```

**Why this matters:**
- Guides the agent to make production-quality decisions
- Prevents over-engineering and premature abstraction
- Encourages consistency with existing codebase
- Reduces the risk of breaking changes

### 6. Anti-Patterns

```
- Large refactors unrelated to the task
- Formatting-only changes
- Skipping or disabling tests
- Repeating the same tool calls without new intent
- Claiming correctness without verification
- Introducing new dependencies without justification
```

**Why this matters:**
- Explicitly lists behaviors that waste resources
- Aligns with tool quota and stall detection systems
- Prevents test manipulation that hides bugs
- Reduces unnecessary code churn

### 7. Tooling Rules

```
- You cannot use shell features like `cd`, pipes, or &&.
- Commands run from the repository root unless otherwise specified.
- Pass paths explicitly instead of changing directories.
- Do not request tools you do not need.
```

**Why this matters:**
- Prevents common shell errors (`cd && pytest` failures)
- Aligns with sandbox command execution model
- Reduces tool request quota waste
- Improves command reliability

---

## Compatibility

### Backward Compatibility

✅ **Fully backward compatible**

- All existing tests pass (108/108)
- Model validator continues to work correctly
- Tool manager, patch hygiene, and stall detection unchanged
- Existing schemas in `llm_gemini.py` and `llm_deepseek.py` unchanged

### Forward Compatibility

✅ **Extensible design**

- New modes can be added to the three-mode system
- Additional tools can be added to AVAILABLE SANDBOX TOOLS section
- Engineering heuristics can be expanded
- Anti-patterns can be refined based on observed failures

---

## Testing

### Test Coverage

**Total tests:** 108 (all passing)

1. **Existing tests (75):**
   - `test_feature_mode.py`: 13 tests
   - `test_v3.py`: 41 tests
   - `test_vnext.py`: 21 tests

2. **New tests (33):**
   - `test_prompt_upgrade.py`: 33 tests
     - 25 structure tests (verifying all sections present)
     - 8 semantic tests (verifying key behaviors)

### Test Results

```bash
$ python -m pytest tests/ -v
================================================= test session starts ==================================================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python
rootdir: /home/runner/work/RFSN-SANDBOX-CONTROLLER-/RFSN-SANDBOX-CONTROLLER-
configfile: pytest.ini
plugins: anyio-4.12.1
collecting ... collected 108 items

... (all tests pass)

============================= 108 passed in 1.19s ==============================
```

---

## Benefits

### For the Controller

1. **Reduced Token Waste**
   - Explicit anti-patterns reduce repeated tool calls
   - Mandatory workflow prevents premature patching
   - Clear completion criteria prevent over-iteration

2. **Better Alignment with Constraints**
   - Tooling rules match sandbox command execution
   - JSON-only output matches validator expectations
   - Anti-patterns align with patch hygiene gates

3. **Improved Predictability**
   - Mandatory workflow creates consistent behavior
   - Definition of Done provides clear exit criteria
   - Engineering heuristics guide decision-making

### For the Agent

1. **Clearer Mission**
   - "You are a bounded coding agent" vs. "You are a coding assistant"
   - Explicit role: engineer executing tasks, not a chat bot
   - Clear constraints: sandbox-mediated, not direct control

2. **Better Guidance**
   - 6-step workflow vs. implicit "figure it out"
   - Engineering heuristics vs. vague "be smart"
   - Explicit anti-patterns vs. learning from failure

3. **Reduced Ambiguity**
   - Definition of Done vs. "until tests pass"
   - Three modes only vs. "respond appropriately"
   - Explicit tool list vs. "use available tools"

### For Users

1. **Higher Quality Outputs**
   - Definition of Done ensures verification
   - Engineering heuristics encourage good practices
   - Anti-patterns prevent common mistakes

2. **Faster Execution**
   - Mandatory workflow reduces wasted steps
   - Tool quotas prevent runaway requests
   - Clear completion criteria prevent over-iteration

3. **Better Auditability**
   - "Why" field required in tool_request mode
   - Workflow steps create clear reasoning trail
   - Engineering heuristics make decisions explainable

---

## Comparison: Before vs. After

### Before (Old Prompt)

- **Length:** ~3,000 characters
- **Structure:** Flat list of rules and examples
- **Modes:** Implicitly supported (repair, feature)
- **Workflow:** Implicit, emergent from examples
- **Constraints:** Mixed with guidance
- **Tone:** Assistant-like, helpful

### After (New Prompt)

- **Length:** ~7,200 characters
- **Structure:** Hierarchical sections with clear headers
- **Modes:** Explicitly defined (tool_request, patch, feature_summary)
- **Workflow:** Mandatory 6-step process
- **Constraints:** Separated into TOOLING RULES, ANTI-PATTERNS
- **Tone:** Engineer-like, bounded, mission-focused

### Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Identity** | "coding agent" | "RFSN-CODE, controller-governed software engineering agent" |
| **Output Format** | "must output JSON" | "ONLY valid JSON in exactly one of three modes" |
| **Workflow** | Implicit from examples | Mandatory 6-step process |
| **Completion** | "make tests pass" | Definition of Done (5 criteria) |
| **Constraints** | Mixed throughout | Organized in TOOLING RULES, ANTI-PATTERNS |
| **Guidance** | Examples only | Engineering heuristics + examples |
| **Failure Modes** | Not addressed | Explicit anti-patterns list |

---

## Metrics

### Prompt Statistics

| Metric | Gemini | DeepSeek |
|--------|--------|----------|
| **Length** | 7,150 chars | 7,413 chars |
| **Sections** | 9 major sections | 10 major sections (+ OUTPUT FORMAT) |
| **Modes** | 3 (tool_request, patch, feature_summary) | 3 (same) |
| **Heuristics** | 5 key principles | 5 key principles |
| **Anti-patterns** | 6 failure modes | 6 failure modes |
| **Tools Listed** | 11 sandbox tools | 11 sandbox tools |
| **Workflow Steps** | 6 steps | 6 steps |

### Test Coverage

| Test Suite | Tests | Pass Rate |
|------------|-------|-----------|
| `test_prompt_upgrade.py` | 33 | 100% (33/33) |
| `test_vnext.py` | 21 | 100% (21/21) |
| `test_v3.py` | 41 | 100% (41/41) |
| `test_feature_mode.py` | 13 | 100% (13/13) |
| **Total** | **108** | **100%** |

---

## Known Limitations

### 1. Prompt Length

**Trade-off:** Comprehensive guidance requires more tokens

- Old prompt: ~3,000 chars (~750 tokens)
- New prompt: ~7,200 chars (~1,800 tokens)
- **Impact:** +1,050 tokens per agent invocation

**Mitigation:** The improved guidance should reduce total token usage by preventing wasted tool requests and failed attempts.

### 2. Model-Specific Differences

**Issue:** Gemini and DeepSeek have slightly different prompts

- DeepSeek includes explicit OUTPUT FORMAT section
- Gemini relies on schema enforcement only

**Mitigation:** Both prompts share the same core content. Differences are only in model-specific formatting requirements.

### 3. Prompt Evolution

**Challenge:** As the controller evolves, the prompt must be updated

**Mitigation:** 
- Clear section structure makes updates easy to locate
- Test suite validates all key sections remain present
- Documentation tracks changes over time

---

## Future Enhancements

### Short Term

1. **Add Mode-Specific Examples**
   - Provide example JSON for each mode
   - Show good vs. bad tool_request examples
   - Demonstrate proper diff formatting

2. **Expand Engineering Heuristics**
   - Add language-specific guidance (Python, Node.js, etc.)
   - Include security-specific heuristics
   - Add performance considerations

3. **Refine Anti-Patterns**
   - Track real failures and add to anti-patterns list
   - Quantify impact of each anti-pattern
   - Add recovery strategies for when patterns are violated

### Long Term

1. **Adaptive Prompts**
   - Adjust prompt based on task type (bug fix vs. feature)
   - Adjust based on repository characteristics
   - Adjust based on agent performance history

2. **Prompt Compression**
   - Identify redundant sections
   - Use more concise language while maintaining clarity
   - Consider prompt-tuning techniques

3. **Multi-Model Optimization**
   - Create model-specific variants (beyond Gemini/DeepSeek)
   - Test with other models (Claude, GPT-4, etc.)
   - Measure performance differences

---

## Conclusion

The upgraded RFSN Coding Agent prompt transforms the system from a helpful coding assistant into a bounded, controller-governed software engineering agent. By providing:

- **Clear identity** (RFSN-CODE, controller-governed)
- **Strict output contract** (three JSON modes only)
- **Mandatory workflow** (6-step process)
- **Engineering heuristics** (5 key principles)
- **Explicit anti-patterns** (6 failure modes)
- **Comprehensive tooling rules**

The agent is better equipped to:

1. Make correct decisions with less trial and error
2. Produce minimal, verifiable changes
3. Respect controller constraints (tool quotas, patch hygiene, stall detection)
4. Think like a senior engineer rather than a general-purpose assistant

All existing tests pass, and 33 new tests validate the prompt structure and semantics. The system is fully backward compatible while providing a foundation for future improvements.

---

**Documentation Generated**: January 15, 2026  
**Implementation Status**: ✅ Complete  
**Test Status**: ✅ All tests passing (108/108)
