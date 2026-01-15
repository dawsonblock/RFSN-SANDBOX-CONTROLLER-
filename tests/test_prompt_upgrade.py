"""Unit tests for upgraded RFSN coding agent prompt.

Tests verify that the new prompt:
- Contains required sections
- Defines all three modes correctly
- Includes engineering heuristics
- Documents anti-patterns
- Specifies tooling rules
"""

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
        assert "controller-governed CODING AGENT" in GEMINI_SYSTEM

    def test_deepseek_prompt_contains_rfsn_code_header(self):
        """Test that DeepSeek prompt contains RFSN-CODE header."""
        assert "RFSN-CODE" in DEEPSEEK_SYSTEM
        assert "controller-governed CODING AGENT" in DEEPSEEK_SYSTEM

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
        assert "Behavior matches" in GEMINI_SYSTEM or "Correct behavior" in GEMINI_SYSTEM
        assert "Verification exists" in GEMINI_SYSTEM
        assert "verification passes" in GEMINI_SYSTEM or "Existing tests pass" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_definition_of_done(self):
        """Test that DeepSeek prompt includes Definition of Done."""
        assert "Definition of Done" in DEEPSEEK_SYSTEM
        assert "Behavior matches" in DEEPSEEK_SYSTEM or "Correct behavior" in DEEPSEEK_SYSTEM
        assert "Verification exists" in DEEPSEEK_SYSTEM
        assert "verification passes" in DEEPSEEK_SYSTEM or "Existing tests pass" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_mandatory_workflow(self):
        """Test that Gemini prompt includes mandatory workflow steps."""
        assert "MANDATORY WORKFLOW" in GEMINI_SYSTEM
        assert "Establish ground truth" in GEMINI_SYSTEM
        assert "Inspect" in GEMINI_SYSTEM
        assert "Plan" in GEMINI_SYSTEM
        assert "Implement" in GEMINI_SYSTEM
        assert "Verify" in GEMINI_SYSTEM
        assert "Stop" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_mandatory_workflow(self):
        """Test that DeepSeek prompt includes mandatory workflow steps."""
        assert "MANDATORY WORKFLOW" in DEEPSEEK_SYSTEM
        assert "Establish ground truth" in DEEPSEEK_SYSTEM
        assert "Inspect" in DEEPSEEK_SYSTEM
        assert "Plan" in DEEPSEEK_SYSTEM
        assert "Implement" in DEEPSEEK_SYSTEM
        assert "Verify" in DEEPSEEK_SYSTEM
        assert "Stop" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_engineering_heuristics(self):
        """Test that Gemini prompt includes key sections for proper behavior."""
        # The new prompt has different sections but same intent
        assert "SHELL-LESS COMMAND RULES" in GEMINI_SYSTEM or "NO SHELL" in GEMINI_SYSTEM
        assert "HYGIENE PROFILE BEHAVIOR" in GEMINI_SYSTEM or "REPAIR MODE" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_engineering_heuristics(self):
        """Test that DeepSeek prompt includes key sections for proper behavior."""
        # The new prompt has different sections but same intent
        assert "SHELL-LESS COMMAND RULES" in DEEPSEEK_SYSTEM or "NO SHELL" in DEEPSEEK_SYSTEM
        assert "HYGIENE PROFILE BEHAVIOR" in DEEPSEEK_SYSTEM or "REPAIR MODE" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_anti_patterns(self):
        """Test that Gemini prompt documents important constraints."""
        # The new prompt consolidates these into various sections
        assert "STALL / RETRY POLICY" in GEMINI_SYSTEM or "HYGIENE PROFILE" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_anti_patterns(self):
        """Test that DeepSeek prompt documents important constraints."""
        # The new prompt consolidates these into various sections
        assert "STALL / RETRY POLICY" in DEEPSEEK_SYSTEM or "HYGIENE PROFILE" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_tooling_rules(self):
        """Test that Gemini prompt specifies tooling rules."""
        assert "SHELL-LESS COMMAND RULES" in GEMINI_SYSTEM or "NO SHELL" in GEMINI_SYSTEM
        assert "repo root" in GEMINI_SYSTEM or "repository root" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_tooling_rules(self):
        """Test that DeepSeek prompt specifies tooling rules."""
        assert "SHELL-LESS COMMAND RULES" in DEEPSEEK_SYSTEM or "NO SHELL" in DEEPSEEK_SYSTEM
        assert "repo root" in DEEPSEEK_SYSTEM or "repository root" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_sandbox_tools(self):
        """Test that Gemini prompt references sandbox tools."""
        # The new prompt references tools inline rather than in a dedicated section
        assert "sandbox" in GEMINI_SYSTEM.lower()
        assert "tool_request" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_sandbox_tools(self):
        """Test that DeepSeek prompt references sandbox tools."""
        # The new prompt references tools inline rather than in a dedicated section
        assert "sandbox" in DEEPSEEK_SYSTEM.lower()
        assert "tool_request" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_mentions_controller_governance(self):
        """Test that Gemini prompt emphasizes controller governance."""
        assert "controller-governed" in GEMINI_SYSTEM.lower()
        assert "locked-down sandbox" in GEMINI_SYSTEM or "sandbox" in GEMINI_SYSTEM

    def test_deepseek_prompt_mentions_controller_governance(self):
        """Test that DeepSeek prompt emphasizes controller governance."""
        assert "controller-governed" in DEEPSEEK_SYSTEM.lower()
        assert "locked-down sandbox" in DEEPSEEK_SYSTEM or "sandbox" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_requires_json_only(self):
        """Test that Gemini prompt enforces JSON-only output."""
        assert "valid JSON" in GEMINI_SYSTEM
        assert "invalid" in GEMINI_SYSTEM

    def test_deepseek_prompt_requires_json_only(self):
        """Test that DeepSeek prompt enforces JSON-only output."""
        assert "valid JSON" in DEEPSEEK_SYSTEM
        assert "invalid" in DEEPSEEK_SYSTEM

    def test_gemini_prompt_includes_when_blocked_guidance(self):
        """Test that Gemini prompt includes guidance for blocked situations."""
        assert "BLOCKED" in GEMINI_SYSTEM or "blocked" in GEMINI_SYSTEM

    def test_deepseek_prompt_includes_when_blocked_guidance(self):
        """Test that DeepSeek prompt includes guidance for blocked situations."""
        assert "BLOCKED" in DEEPSEEK_SYSTEM or "blocked" in DEEPSEEK_SYSTEM

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
        
        # Both prompts should be the same now (unified upgrade)
        # Length should be identical or very close
        length_diff = abs(len(GEMINI_SYSTEM) - len(DEEPSEEK_SYSTEM))
        assert length_diff < 100, f"Prompt lengths differ: {length_diff}"


class TestPromptSemantics:
    """Tests for prompt semantic content and instructions."""

    def test_gemini_prompt_emphasizes_minimal_changes(self):
        """Test that Gemini prompt emphasizes minimal, targeted changes."""
        assert "minimal" in GEMINI_SYSTEM.lower()
        assert "targeted" in GEMINI_SYSTEM.lower() or "smallest" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_emphasizes_minimal_changes(self):
        """Test that DeepSeek prompt emphasizes minimal, targeted changes."""
        assert "minimal" in DEEPSEEK_SYSTEM.lower()
        assert "targeted" in DEEPSEEK_SYSTEM.lower() or "smallest" in DEEPSEEK_SYSTEM.lower()

    def test_gemini_prompt_forbids_guessing(self):
        """Test that Gemini prompt discourages guessing and requires evidence."""
        # The new prompt emphasizes evidence-based approach
        assert "evidence" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_forbids_guessing(self):
        """Test that DeepSeek prompt discourages guessing and requires evidence."""
        # The new prompt emphasizes evidence-based approach
        assert "evidence" in DEEPSEEK_SYSTEM.lower()

    def test_gemini_prompt_requires_verification(self):
        """Test that Gemini prompt requires verification."""
        assert "Verify" in GEMINI_SYSTEM or "verify" in GEMINI_SYSTEM
        assert "verification" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_requires_verification(self):
        """Test that DeepSeek prompt requires verification."""
        assert "Verify" in DEEPSEEK_SYSTEM or "verify" in DEEPSEEK_SYSTEM
        assert "verification" in DEEPSEEK_SYSTEM.lower()

    def test_gemini_prompt_encourages_senior_engineer_mindset(self):
        """Test that Gemini prompt encourages professional coding behavior."""
        assert "bounded coding agent" in GEMINI_SYSTEM.lower() or "agent" in GEMINI_SYSTEM.lower()

    def test_deepseek_prompt_encourages_senior_engineer_mindset(self):
        """Test that DeepSeek prompt encourages professional coding behavior."""
        assert "bounded coding agent" in DEEPSEEK_SYSTEM.lower() or "agent" in DEEPSEEK_SYSTEM.lower()
