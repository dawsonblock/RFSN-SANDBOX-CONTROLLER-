"""Tests for feature mode functionality.

Tests model validation, goal creation, prompt building, and feature workflow for the
feature engineering mode that enables the agent to implement new features from scratch.
"""

import pytest
from rfsn_controller.model_validator import ModelOutputValidator
from rfsn_controller.goals import GoalFactory, FeatureGoal, GoalType, DEFAULT_FEATURE_SUBGOALS
from rfsn_controller.prompt import build_model_input, MODE_FEATURE


class TestModelValidator:
    """Test model validator with feature_summary mode."""

    def test_feature_summary_valid(self):
        """Test valid feature_summary mode."""
        validator = ModelOutputValidator()
        output = '{"mode": "feature_summary", "summary": "Implemented user authentication", "completion_status": "complete"}'
        result = validator.validate(output)
        
        assert result.is_valid
        assert result.mode == "feature_summary"
        assert result.summary == "Implemented user authentication"
        assert result.completion_status == "complete"

    def test_feature_summary_empty_summary(self):
        """Test feature_summary with empty summary."""
        validator = ModelOutputValidator()
        output = '{"mode": "feature_summary", "summary": "", "completion_status": "complete"}'
        result = validator.validate(output)
        
        assert not result.is_valid
        assert result.mode == "tool_request"
        assert "summary cannot be empty" in result.validation_error

    def test_feature_summary_invalid_status(self):
        """Test feature_summary with invalid completion_status."""
        validator = ModelOutputValidator()
        output = '{"mode": "feature_summary", "summary": "Test", "completion_status": "invalid"}'
        result = validator.validate(output)
        
        assert not result.is_valid
        assert result.mode == "tool_request"
        assert "Invalid completion_status" in result.validation_error

    def test_feature_summary_all_statuses(self):
        """Test all valid completion statuses."""
        validator = ModelOutputValidator()
        statuses = ["complete", "partial", "blocked", "in_progress"]
        
        for status in statuses:
            output = f'{{"mode": "feature_summary", "summary": "Test summary", "completion_status": "{status}"}}'
            result = validator.validate(output)
            assert result.is_valid
            assert result.completion_status == status


class TestFeatureGoals:
    """Test feature goal creation."""

    def test_create_feature_goal(self):
        """Test creating a feature goal."""
        goal = GoalFactory.create_feature_goal(
            description="Add user authentication",
            acceptance_criteria=["Users can log in", "Users can log out"],
            timeout=600
        )
        
        assert isinstance(goal, FeatureGoal)
        assert goal.description == "Add user authentication"
        assert len(goal.acceptance_criteria) == 2
        assert goal.timeout == 600
        assert len(goal.subgoals) == 4  # Default subgoals

    def test_feature_goal_default_subgoals(self):
        """Test default subgoals are created."""
        goal = GoalFactory.create_feature_goal(
            description="Test feature",
            acceptance_criteria=["Must work"]
        )
        
        # Should match the centralized constant
        assert goal.subgoals == DEFAULT_FEATURE_SUBGOALS
        assert "scaffold" in goal.subgoals[0]
        assert "implement" in goal.subgoals[1]
        assert "tests" in goal.subgoals[2]
        assert "docs" in goal.subgoals[3]


class TestPromptBuilding:
    """Test prompt building for feature mode."""

    def test_build_feature_mode_prompt(self):
        """Test building prompt in feature mode."""
        state = {
            "mode": MODE_FEATURE,
            "goal": "Implement feature: User authentication",
            "feature_description": "Add login/logout functionality",
            "acceptance_criteria": ["Users can log in", "Sessions persist"],
            "completed_subgoals": ["scaffold: Created auth module"],
            "current_subgoal": "implement: Write login logic",
            "test_cmd": "pytest -q",
            "focus_test_cmd": "pytest -q tests/test_auth.py",
            "failure_output": "",
            "repo_tree": "src/\ntests/",
            "constraints": "Follow security best practices",
            "files_block": "",
            "observations": "",
        }
        
        prompt = build_model_input(state)
        
        assert "FEATURE_DESCRIPTION" in prompt
        assert "ACCEPTANCE_CRITERIA" in prompt
        assert "COMPLETED_SUBGOALS" in prompt
        assert "CURRENT_SUBGOAL" in prompt
        assert "User authentication" in prompt
        assert "login/logout functionality" in prompt
        assert "Users can log in" in prompt

    def test_build_repair_mode_prompt(self):
        """Test building prompt in repair mode (original behavior)."""
        state = {
            "goal": "Make tests pass",
            "intent": "fix_bug",
            "subgoal": "Fix import error",
            "test_cmd": "pytest -q",
            "focus_test_cmd": "pytest -q tests/test_main.py",
            "failure_output": "ImportError: No module named 'foo'",
            "repo_tree": "src/\ntests/",
            "constraints": "Minimal changes",
            "files_block": "",
            "observations": "",
        }
        
        prompt = build_model_input(state)
        
        assert "INTENT" in prompt
        assert "SUBGOAL" in prompt
        assert "fix_bug" in prompt
        assert "Fix import error" in prompt
        # Feature mode sections should not be present
        assert "FEATURE_DESCRIPTION" not in prompt
        assert "ACCEPTANCE_CRITERIA" not in prompt


class TestGoalType:
    """Test GoalType enum includes FEATURE."""

    def test_feature_goal_type_exists(self):
        """Test FEATURE goal type exists."""
        assert hasattr(GoalType, "FEATURE")
        assert GoalType.FEATURE.value == "feature"
