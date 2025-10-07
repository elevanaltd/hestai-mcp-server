"""
Validation test for Phase 0.5 STEP 2 cleanup.

This test validates that dormant helper methods have been removed from base_tool.py
as per critical-engineer recommendation (continuation_id: 961cbf24-b438-436c-81fc-478f6fe87dca).

DORMANT METHODS TO BE REMOVED (lines ~1117-1304):
1. _format_available_models_list()
2. _collect_ranked_capabilities()
3. _normalize_model_identifier()
4. _get_ranked_model_summaries()
5. _get_restriction_note()
6. _build_model_unavailable_message()
7. _build_auto_mode_required_message()

ACTIVE METHOD TO KEEP:
- _format_context_window() (currently in use)

This test will FAIL (RED) before cleanup, PASS (GREEN) after cleanup.
"""

import os

import pytest


class TestDormantCodeCleanup:
    """Test suite validating dormant code removal from base_tool.py"""

    def test_dormant_helpers_removed(self):
        """Validate that dormant helper methods have been removed from BaseTool."""
        from tools.shared.base_tool import BaseTool

        # List of dormant methods that MUST be removed
        dormant_methods = [
            "_format_available_models_list",
            "_collect_ranked_capabilities",
            "_normalize_model_identifier",
            "_get_ranked_model_summaries",
            "_get_restriction_note",
            "_build_model_unavailable_message",
            "_build_auto_mode_required_message",
        ]

        # Check dormant methods are NOT present
        for method_name in dormant_methods:
            assert not hasattr(
                BaseTool, method_name
            ), f"DORMANT method '{method_name}' still exists - must be removed per critical-engineer"

    def test_active_method_preserved(self):
        """Validate that the active _format_context_window method is preserved."""
        from tools.shared.base_tool import BaseTool

        # Active method that MUST remain
        assert hasattr(
            BaseTool, "_format_context_window"
        ), "ACTIVE method '_format_context_window' is missing - must be preserved"

    def test_format_context_window_still_works(self):
        """Validate that the active _format_context_window method still functions correctly."""
        from tools.shared.base_tool import BaseTool

        # Test various token counts
        test_cases = [
            (1_000_000, "1M ctx"),  # Exact millions
            (1_500_000, "1.5M ctx"),  # Fractional millions
            (128_000, "128K ctx"),  # Exact thousands
            (65_536, "65.5K ctx"),  # Fractional thousands
            (500, "500 ctx"),  # Under 1K
            (0, None),  # Invalid
            (-100, None),  # Invalid
        ]

        for tokens, expected in test_cases:
            result = BaseTool._format_context_window(tokens)
            assert result == expected, f"_format_context_window({tokens}) returned {result}, expected {expected}"

    def test_base_tool_file_line_count_reduced(self):
        """Validate that base_tool.py has been reduced in size after cleanup."""
        base_tool_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "tools",
            "shared",
            "base_tool.py",
        )

        # Count lines in current file
        with open(base_tool_path) as f:
            current_lines = len(f.readlines())

        # Before cleanup: ~1760 lines (actual measurement from RED phase)
        # After cleanup: Should be ~175 lines less (removing ~175 lines of dormant code + comments)
        # We expect < 1600 lines after cleanup
        max_expected_lines = 1600

        assert (
            current_lines < max_expected_lines
        ), f"base_tool.py has {current_lines} lines, expected < {max_expected_lines} after cleanup"

    def test_dormant_code_markers_removed(self):
        """Validate that dormant code section markers have been removed."""
        base_tool_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "tools",
            "shared",
            "base_tool.py",
        )

        with open(base_tool_path) as f:
            content = f.read()

        # Check for dormant code markers that should be removed
        dormant_markers = [
            "# Ported from upstream Zen base_tool.py for STEP 2.3a",
            "# Conservative activation in STEP 2.3b",
            "# Full orchestration helpers remain dormant",
            "# These helpers available for future refactoring",
            "# === END DORMANT HELPER METHODS ===",
        ]

        for marker in dormant_markers:
            assert marker not in content, f"Dormant code marker still present: '{marker}' - must be removed"

    def test_consultation_evidence_added(self):
        """Validate that critical-engineer consultation evidence was added."""
        base_tool_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "tools",
            "shared",
            "base_tool.py",
        )

        with open(base_tool_path) as f:
            content = f.read()

        # Check for consultation evidence comment
        evidence_comment = (
            "# // Critical-Engineer: consulted for Base tool abstraction and upstream divergence strategy"
        )

        assert evidence_comment in content, "Missing critical-engineer consultation evidence comment"


if __name__ == "__main__":
    # Run tests standalone
    pytest.main([__file__, "-v"])
