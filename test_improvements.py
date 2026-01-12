"""Test suite for RFSN controller improvements."""

import unittest
from unittest.mock import Mock, patch
from rfsn_controller.policy import (
    _classify_error,
    _extract_error_context,
    _choose_intent_from_categories,
    choose_policy,
    PolicyDecision,
)
from rfsn_controller.verifier import VerifyResult
from rfsn_controller.parallel import PatchResult, find_first_successful_patch


class TestPolicyEnhancements(unittest.TestCase):
    """Test enhanced policy engine with better heuristics."""

    def test_classify_import_error(self):
        """Test import error classification."""
        blob = "ModuleNotFoundError: No module named 'requests'"
        categories = _classify_error(blob)
        self.assertIn("import", categories)

    def test_classify_type_error(self):
        """Test type error classification."""
        blob = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        categories = _classify_error(blob)
        self.assertIn("type", categories)

    def test_classify_attribute_error(self):
        """Test attribute error classification."""
        blob = "AttributeError: 'NoneType' object has no attribute 'split'"
        categories = _classify_error(blob)
        self.assertIn("attribute", categories)

    def test_classify_syntax_error(self):
        """Test syntax error classification."""
        blob = "SyntaxError: invalid syntax"
        categories = _classify_error(blob)
        self.assertIn("syntax", categories)

    def test_classify_multiple_errors(self):
        """Test multiple error classification."""
        blob = "TypeError: bad operand\nAttributeError: no attr"
        categories = _classify_error(blob)
        self.assertIn("type", categories)
        self.assertIn("attribute", categories)

    def test_extract_error_context(self):
        """Test error context extraction."""
        blob = """
Traceback (most recent call last):
  File "test.py", line 42, in <module>
    foo()
TypeError: bad type
"""
        context = _extract_error_context(blob)
        self.assertTrue(context["has_traceback"])
        self.assertEqual(context["line_numbers"], ["line 42"])
        self.assertEqual(context["file_paths"], ["test.py"])

    def test_choose_intent_import(self):
        """Test intent selection for import errors."""
        categories = ["import"]
        context = {}
        intent, subgoal, confidence = _choose_intent_from_categories(
            categories, context
        )
        self.assertEqual(intent, "dependency_or_import_fix")
        self.assertEqual(subgoal, "fix_imports")
        self.assertEqual(confidence, 0.9)

    def test_choose_intent_syntax(self):
        """Test intent selection for syntax errors."""
        categories = ["syntax"]
        context = {}
        intent, subgoal, confidence = _choose_intent_from_categories(
            categories, context
        )
        self.assertEqual(intent, "syntax_fix")
        self.assertEqual(subgoal, "correct_syntax_errors")
        self.assertEqual(confidence, 0.95)

    def test_choose_intent_fallback(self):
        """Test fallback intent for unknown errors."""
        categories = []
        context = {}
        intent, subgoal, confidence = _choose_intent_from_categories(
            categories, context
        )
        self.assertEqual(intent, "general_fix")
        self.assertEqual(subgoal, "reduce_failing_tests")
        self.assertEqual(confidence, 0.5)

    def test_choose_policy_integration(self):
        """Test full policy decision flow."""
        v = VerifyResult(
            ok=False,
            exit_code=1,
            stdout="",
            stderr="AttributeError: 'NoneType' object has no attribute 'x'",
            failing_tests=["test_foo.py::test_bar"],
            sig="abc123",
        )
        decision = choose_policy("pytest -q", v)
        self.assertIsInstance(decision, PolicyDecision)
        self.assertEqual(decision.intent, "attribute_error_fix")
        self.assertEqual(decision.subgoal, "fix_missing_attr")
        self.assertIn("test_foo.py", decision.focus_test_cmd)
        self.assertGreater(decision.confidence, 0.5)

    def test_choose_policy_no_failing_tests(self):
        """Test policy when no failing tests are identified."""
        v = VerifyResult(
            ok=False,
            exit_code=1,
            stdout="",
            stderr="TypeError: bad type",
            failing_tests=[],
            sig="abc123",
        )
        decision = choose_policy("pytest -q", v)
        self.assertEqual(decision.focus_test_cmd, "pytest -q")


class TestParallelEvaluation(unittest.TestCase):
    """Test parallel patch evaluation utilities."""

    def test_patch_result_creation(self):
        """Test PatchResult dataclass."""
        result = PatchResult(
            diff="@@ -1,1 +1,1 @@\n-old\n+new",
            diff_hash="abc123",
            ok=True,
            info="PASS",
            temperature=0.0,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.diff_hash, "abc123")

    def test_find_first_successful_patch(self):
        """Test finding first successful patch."""
        results = [
            PatchResult("diff1", "hash1", False, "fail", 0.0),
            PatchResult("diff2", "hash2", True, "PASS", 0.2),
            PatchResult("diff3", "hash3", True, "PASS", 0.4),
        ]
        winner = find_first_successful_patch(results)
        self.assertIsNotNone(winner)
        self.assertEqual(winner.diff, "diff2")

    def test_find_first_successful_patch_none(self):
        """Test finding winner when all patches fail."""
        results = [
            PatchResult("diff1", "hash1", False, "fail1", 0.0),
            PatchResult("diff2", "hash2", False, "fail2", 0.2),
        ]
        winner = find_first_successful_patch(results)
        self.assertIsNone(winner)


class TestBugFixes(unittest.TestCase):
    """Test that bug fixes work correctly."""

    def test_safe_int_conversion(self):
        """Test that int conversion handles invalid values."""
        from rfsn_controller.controller import _execute_tool
        from rfsn_controller.sandbox import Sandbox

        sb = Sandbox("/tmp/test", "/tmp/test/repo")

        # Test with valid int
        result = _execute_tool(
            sb, "sandbox.run", {"cmd": "echo test", "timeout_sec": "60"}
        )
        self.assertIn("ok", result)

        # Test with invalid int (should use default)
        result = _execute_tool(
            sb, "sandbox.run", {"cmd": "echo test", "timeout_sec": "invalid"}
        )
        self.assertIn("ok", result)

        # Test with None args (should not crash)
        result = _execute_tool(sb, "sandbox.read_file", None)
        self.assertIn("ok", result)


if __name__ == "__main__":
    unittest.main()
