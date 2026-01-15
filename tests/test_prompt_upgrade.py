"""Unit tests for upgraded RFSN coding agent prompt.

Tests verify that the new prompt:
- Contains required sections
- Defines all three modes correctly
- Includes engineering heuristics
- Documents anti-patterns
- Specifies tooling rules
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rfsn_controller.llm_gemini import SYSTEM as GEMINI_SYSTEM
from rfsn_controller.llm_deepseek import SYSTEM as DEEPSEEK_SYSTEM


class TestPromptStructure:
    """Tests for prompt structure and content."""

    def test_gemini_prompt_contains_rfsn_code_header(self):
        """Test that Gemini prompt contains RFSN-CODE header."""
        assert "RFSN-CODE" in GEMINI_SYSTEM
        assert "CONTROLLER-GOVERNED SOFTWARE ENGINEERING AGENT" in GEMINI_SYSTEM

    def test_deepseek_prompt_contains_rfsn_code_header(self):
        """Test that DeepSeek prompt contains RFSN-CODE header."""
        assert "RFSN-CODE" in DEEPSEEK_SYSTEM
        assert "CONTROLLER-GOVERNED SOFTWARE ENGINEERING AGENT" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_defines_three_modes(self):
        """Test that Gemini prompt defines tool_request, patch, and feature_summary."""
        assert "tool_request" in GEMINI_SYSTEM
        assert "patch" in GEMINI_SYSTEM
        assert "feature_summary" in GEMINI_SYSTEM
        assert "mode" in GEMINI_SYSTEM

    def test_deepseek_prompt_defines_three_modes(self):
        """Test that DeepSeek prompt defines tool_request, patch, and feature_summary."""
        assert "tool_request" in DEEPSEEK_SYSTEM
        assert "patch" in DEEPSEEK_SYSTEM
        assert "feature_summary" in DEEPSEEK_SYSTEM
        assert "mode" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_definition_of_done(self):
        """Test that Gemini prompt includes Definition of Done."""
        assert "Definition of Done" in GEMINI_SYSTEM
        assert "Correct behavior" in GEMINI_SYSTEM
        assert "Verification exists" in GEMINI_SYSTEM
        assert "Existing tests pass" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_definition_of_done(self):
        """Test that DeepSeek prompt includes Definition of Done."""
        assert "Definition of Done" in DEEPSEEK_SYSTEM
        assert "Correct behavior" in DEEPSEEK_SYSTEM
        assert "Verification exists" in DEEPSEEK_SYSTEM
        assert "Existing tests pass" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_mandatory_workflow(self):
        """Test that Gemini prompt includes mandatory workflow steps."""
        assert "MANDATORY WORKFLOW" in GEMINI_SYSTEM
        assert "Establish ground truth" in GEMINI_SYSTEM
        assert "Inspect before acting" in GEMINI_SYSTEM
        assert "Plan internally" in GEMINI_SYSTEM
        assert "Implement" in GEMINI_SYSTEM
        assert "Verify" in GEMINI_SYSTEM
        assert "Finish" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_mandatory_workflow(self):
        """Test that DeepSeek prompt includes mandatory workflow steps."""
        assert "MANDATORY WORKFLOW" in DEEPSEEK_SYSTEM
        assert "Establish ground truth" in DEEPSEEK_SYSTEM
        assert "Inspect before acting" in DEEPSEEK_SYSTEM
        assert "Plan internally" in DEEPSEEK_SYSTEM
        assert "Implement" in DEEPSEEK_SYSTEM
        assert "Verify" in DEEPSEEK_SYSTEM
        assert "Finish" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_engineering_heuristics(self):
        """Test that Gemini prompt includes engineering heuristics."""
        assert "ENGINEERING HEURISTICS" in GEMINI_SYSTEM
        assert "explicit behavior" in GEMINI_SYSTEM
        assert "Match existing architecture" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_engineering_heuristics(self):
        """Test that DeepSeek prompt includes engineering heuristics."""
        assert "ENGINEERING HEURISTICS" in DEEPSEEK_SYSTEM
        assert "explicit behavior" in DEEPSEEK_SYSTEM
        assert "Match existing architecture" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_anti_patterns(self):
        """Test that Gemini prompt documents anti-patterns."""
        assert "ANTI-PATTERNS" in GEMINI_SYSTEM
        assert "Large refactors" in GEMINI_SYSTEM
        assert "Formatting-only changes" in GEMINI_SYSTEM
        assert "Skipping or disabling tests" in GEMINI_SYSTEM
        assert "Repeating the same tool calls" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_anti_patterns(self):
        """Test that DeepSeek prompt documents anti-patterns."""
        assert "ANTI-PATTERNS" in DEEPSEEK_SYSTEM
        assert "Large refactors" in DEEPSEEK_SYSTEM
        assert "Formatting-only changes" in DEEPSEEK_SYSTEM
        assert "Skipping or disabling tests" in DEEPSEEK_SYSTEM
        assert "Repeating the same tool calls" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_tooling_rules(self):
        """Test that Gemini prompt specifies tooling rules."""
        assert "TOOLING RULES" in GEMINI_SYSTEM
        assert "cannot use shell features" in GEMINI_SYSTEM
        assert "Commands run from the repository root" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_tooling_rules(self):
        """Test that DeepSeek prompt specifies tooling rules."""
        assert "TOOLING RULES" in DEEPSEEK_SYSTEM
        assert "cannot use shell features" in DEEPSEEK_SYSTEM
        assert "Commands run from the repository root" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_sandbox_tools(self):
        """Test that Gemini prompt lists available sandbox tools."""
        assert "AVAILABLE SANDBOX TOOLS" in GEMINI_SYSTEM
        assert "sandbox.list_tree" in GEMINI_SYSTEM
        assert "sandbox.read_file" in GEMINI_SYSTEM
        assert "sandbox.grep" in GEMINI_SYSTEM
        assert "sandbox.run" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_sandbox_tools(self):
        """Test that DeepSeek prompt lists available sandbox tools."""
        assert "AVAILABLE SANDBOX TOOLS" in DEEPSEEK_SYSTEM
        assert "sandbox.list_tree" in DEEPSEEK_SYSTEM
        assert "sandbox.read_file" in DEEPSEEK_SYSTEM
        assert "sandbox.grep" in DEEPSEEK_SYSTEM
        assert "sandbox.run" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_mentions_controller_governance(self):
        """Test that Gemini prompt emphasizes controller governance."""
        assert "controller-governed" in GEMINI_SYSTEM.lower()
        assert "sandbox controlled by the RFSN Controller" in GEMINI_SYSTEM

    def test_deepseek_prompt_mentions_controller_governance(self):
        """Test that DeepSeek prompt emphasizes controller governance."""
        assert "controller-governed" in DEEPSEEK_SYSTEM.lower()
        assert "sandbox controlled by the RFSN Controller" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_requires_json_only(self):
        """Test that Gemini prompt enforces JSON-only output."""
        assert "valid JSON" in GEMINI_SYSTEM
        assert "Any output outside these modes is invalid" in GEMINI_SYSTEM

    def test_deepseek_prompt_requires_json_only(self):
        """Test that DeepSeek prompt enforces JSON-only output."""
        assert "valid JSON" in DEEPSEEK_SYSTEM
        # DeepSeek has additional OUTPUT FORMAT section
        assert "OUTPUT FORMAT" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_when_blocked_guidance(self):
        """Test that Gemini prompt includes guidance for blocked situations."""
        assert "WHEN BLOCKED" in GEMINI_SYSTEM
        assert "Do NOT invent requirements" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_when_blocked_guidance(self):
        """Test that DeepSeek prompt includes guidance for blocked situations."""
        assert "WHEN BLOCKED" in DEEPSEEK_SYSTEM
        assert "Do NOT invent requirements" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_length_reasonable(self):
        """Test that Gemini prompt length is reasonable (not too short or too long)."""
        # Should be comprehensive but not excessive
        # Lower bound: Must contain all sections (>5000 chars)
        # Upper bound: Should not exceed 15000 chars to avoid excessive token usage
        # This allows ~2-3x the old prompt length while preventing bloat
        assert 5000 < len(GEMINI_SYSTEM) < 15000, f"Prompt length: {len(GEMINI_SYSTEM)}"

    def test_deepseek_prompt_length_reasonable(self):
        """Test that DeepSeek prompt length is reasonable (not too short or too long)."""
        # Should be comprehensive but not excessive
        # Lower bound: Must contain all sections (>5000 chars)
        # Upper bound: Should not exceed 15000 chars to avoid excessive token usage
        # This allows ~2-3x the old prompt length while preventing bloat
        assert 5000 < len(DEEPSEEK_SYSTEM) < 15000, f"Prompt length: {len(DEEPSEEK_SYSTEM)}"

    def test_prompts_are_similar_but_not_identical(self):
        """Test that Gemini and DeepSeek prompts are similar but account for differences."""
        # Core sections should match
        assert "RFSN-CODE" in GEMINI_SYSTEM and "RFSN-CODE" in DEEPSEEK_SYSTEM
        assert "MANDATORY WORKFLOW" in GEMINI_SYSTEM and "MANDATORY WORKFLOW" in DEEPSEEK_SYSTEM
        
        # But they should have some differences (DeepSeek has OUTPUT FORMAT section)
        assert "OUTPUT FORMAT" in DEEPSEEK_SYSTEM
        
        # Length should be similar but not identical
        # DeepSeek has additional OUTPUT FORMAT section (~300-400 chars)
        # Allow up to 1000 chars difference to accommodate model-specific variations
        length_diff = abs(len(GEMINI_SYSTEM) - len(DEEPSEEK_SYSTEM))
        assert length_diff < 1000, f"Prompt lengths too different: {length_diff}"


class TestPromptSemantics:
    """Tests for prompt semantic content and instructions."""

    def test_gemini_prompt_emphasizes_minimal_changes(self):
        """Test that Gemini prompt emphasizes minimal, targeted changes."""
        assert "minimal" in GEMINI_SYSTEM.lower()
        assert "targeted" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_emphasizes_minimal_changes(self):
        """Test that DeepSeek prompt emphasizes minimal, targeted changes."""
        assert "minimal" in DEEPSEEK_SYSTEM.lower()
        assert "targeted" in DEEPSEEK_SYSTEM.lower()

    def test_gemini_prompt_forbids_guessing(self):
        """Test that Gemini prompt forbids guessing."""
        # Should explicitly forbid guessing in tool_request rules
        assert "Never guess when the answer is in the repo" in GEMINI_SYSTEM

    def test_deepseek_prompt_forbids_guessing(self):
        """Test that DeepSeek prompt forbids guessing."""
        # Should explicitly forbid guessing in tool_request rules
        assert "Never guess when the answer is in the repo" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_requires_verification(self):
        """Test that Gemini prompt requires verification."""
        assert "Verify" in GEMINI_SYSTEM
        assert "verification" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_requires_verification(self):
        """Test that DeepSeek prompt requires verification."""
        assert "Verify" in DEEPSEEK_SYSTEM
        assert "verification" in DEEPSEEK_SYSTEM.lower()

    def test_gemini_prompt_encourages_senior_engineer_mindset(self):
        """Test that Gemini prompt encourages senior engineer thinking."""
        assert "senior engineer" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_encourages_senior_engineer_mindset(self):
        """Test that DeepSeek prompt encourages senior engineer thinking."""
        assert "senior engineer" in DEEPSEEK_SYSTEM.lower()
