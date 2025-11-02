"""Tests for DISABLED_TOOLS environment variable functionality."""

import logging
import os
from unittest.mock import patch

import pytest

from server import (
    apply_tool_filter,
    parse_disabled_tools_env,
    validate_disabled_tools,
)


# Mock the tool classes since we're testing the filtering logic
class MockTool:
    def __init__(self, name):
        self.name = name


class TestDisabledTools:
    """Test suite for DISABLED_TOOLS functionality."""

    def test_parse_disabled_tools_empty(self):
        """Empty string returns empty set (no tools disabled)."""
        with patch.dict(os.environ, {"DISABLED_TOOLS": ""}):
            assert parse_disabled_tools_env() == set()

    def test_parse_disabled_tools_not_set(self):
        """Unset variable returns empty set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure DISABLED_TOOLS is not in environment
            if "DISABLED_TOOLS" in os.environ:
                del os.environ["DISABLED_TOOLS"]
            assert parse_disabled_tools_env() == set()

    def test_parse_disabled_tools_single(self):
        """Single tool name parsed correctly."""
        with patch.dict(os.environ, {"DISABLED_TOOLS": "debug"}):
            assert parse_disabled_tools_env() == {"debug"}

    def test_parse_disabled_tools_multiple(self):
        """Multiple tools with spaces parsed correctly."""
        with patch.dict(os.environ, {"DISABLED_TOOLS": "debug, analyze, refactor"}):
            assert parse_disabled_tools_env() == {"debug", "analyze", "refactor"}

    def test_parse_disabled_tools_extra_spaces(self):
        """Extra spaces and empty items handled correctly."""
        with patch.dict(os.environ, {"DISABLED_TOOLS": " debug , , analyze ,  "}):
            assert parse_disabled_tools_env() == {"debug", "analyze"}

    def test_parse_disabled_tools_duplicates(self):
        """Duplicate entries handled correctly (set removes duplicates)."""
        with patch.dict(os.environ, {"DISABLED_TOOLS": "debug,analyze,debug"}):
            assert parse_disabled_tools_env() == {"debug", "analyze"}

    def test_tool_filtering_logic(self):
        """Test the complete filtering logic using the actual server functions."""
        # Simulate ALL_TOOLS
        ALL_TOOLS = {
            "chat": MockTool("chat"),
            "debug": MockTool("debug"),
            "analyze": MockTool("analyze"),
            "version": MockTool("version"),
            "listmodels": MockTool("listmodels"),
        }

        # Test case 1: No tools disabled
        disabled_tools = set()
        enabled_tools = apply_tool_filter(ALL_TOOLS, disabled_tools)

        assert len(enabled_tools) == 5  # All tools included
        assert set(enabled_tools.keys()) == set(ALL_TOOLS.keys())

        # Test case 2: Disable some operational tools
        disabled_tools = {"debug", "analyze"}
        enabled_tools = apply_tool_filter(ALL_TOOLS, disabled_tools)

        assert len(enabled_tools) == 3  # chat, version, listmodels
        assert "debug" not in enabled_tools
        assert "analyze" not in enabled_tools
        assert "chat" in enabled_tools
        assert "version" in enabled_tools
        assert "listmodels" in enabled_tools

        # Test case 3: Disable diagnostic tools (now allowed in three-tier model)
        disabled_tools = {"version", "chat"}
        enabled_tools = apply_tool_filter(ALL_TOOLS, disabled_tools)

        assert "version" not in enabled_tools  # Diagnostic tool CAN be disabled
        assert "chat" not in enabled_tools  # Operational tool disabled
        assert "listmodels" in enabled_tools  # Other diagnostic tool not disabled

    def test_unknown_tools_warning(self, caplog):
        """Test that unknown tool names generate appropriate warnings."""
        ALL_TOOLS = {
            "chat": MockTool("chat"),
            "debug": MockTool("debug"),
            "analyze": MockTool("analyze"),
            "version": MockTool("version"),
            "listmodels": MockTool("listmodels"),
        }
        disabled_tools = {"chat", "unknown_tool", "another_unknown"}

        with caplog.at_level(logging.WARNING):
            validate_disabled_tools(disabled_tools, ALL_TOOLS)
            assert "Unknown tools in DISABLED_TOOLS: ['another_unknown', 'unknown_tool']" in caplog.text

    def test_diagnostic_tools_warning(self, caplog):
        """Test warning when disabling diagnostic tools (three-tier model)."""
        ALL_TOOLS = {
            "chat": MockTool("chat"),
            "debug": MockTool("debug"),
            "analyze": MockTool("analyze"),
            "version": MockTool("version"),
            "listmodels": MockTool("listmodels"),
        }
        disabled_tools = {"version", "listmodels", "chat"}

        with caplog.at_level(logging.WARNING):
            validate_disabled_tools(disabled_tools, ALL_TOOLS)
            # Should warn about diagnostic tools being disabled
            assert "Disabling diagnostic tools: ['listmodels', 'version']" in caplog.text
            assert "troubleshooting visibility reduced" in caplog.text

    def test_diagnostic_tools_can_be_disabled(self):
        """Test that diagnostic tools can actually be disabled in three-tier model."""
        ALL_TOOLS = {
            "chat": MockTool("chat"),
            "version": MockTool("version"),
            "listmodels": MockTool("listmodels"),
        }
        disabled_tools = {"version", "listmodels"}

        enabled_tools = apply_tool_filter(ALL_TOOLS, disabled_tools)

        # Diagnostic tools CAN be disabled (unlike old behavior)
        assert "version" not in enabled_tools
        assert "listmodels" not in enabled_tools
        assert "chat" in enabled_tools
        assert len(enabled_tools) == 1

    def test_no_mandatory_tools_currently(self):
        """Test that MANDATORY_TOOLS is empty (no tools have technical dependencies)."""
        from server import MANDATORY_TOOLS

        assert len(MANDATORY_TOOLS) == 0, "MANDATORY_TOOLS should be empty - no current technical dependencies"

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("", set()),  # Empty string
            ("   ", set()),  # Only spaces
            (",,,", set()),  # Only commas
            ("chat", {"chat"}),  # Single tool
            ("chat,debug", {"chat", "debug"}),  # Multiple tools
            ("chat, debug, analyze", {"chat", "debug", "analyze"}),  # With spaces
            ("chat,debug,chat", {"chat", "debug"}),  # Duplicates
        ],
    )
    def test_parse_disabled_tools_parametrized(self, env_value, expected):
        """Parametrized tests for various input formats."""
        with patch.dict(os.environ, {"DISABLED_TOOLS": env_value}):
            assert parse_disabled_tools_env() == expected
