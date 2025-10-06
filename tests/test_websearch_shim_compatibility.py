"""
Test STEP 2.2 backward compatibility shim for use_websearch parameter.

Validates that the shim correctly handles use_websearch parameter backward compatibility
for critical-engineer tool.
"""

from tools.critical_engineer import CriticalEngineerTool


class TestWebSearchShimCompatibility:
    """Test use_websearch backward compatibility shim."""

    def test_critical_engineer_shim_false_returns_empty(self):
        """Test critical-engineer shim returns empty string when use_websearch=False."""
        tool = CriticalEngineerTool()
        result = tool.get_websearch_instruction(use_websearch=False)
        assert result == "", "Shim must return empty string when use_websearch=False"

    def test_critical_engineer_shim_true_returns_instruction(self):
        """Test critical-engineer shim returns instruction when use_websearch=True."""
        tool = CriticalEngineerTool()
        result = tool.get_websearch_instruction(use_websearch=True)
        assert "WEB SEARCH CAPABILITY" in result, "Shim must delegate to internal method"

    def test_critical_engineer_shim_tool_specific_parameter(self):
        """Test critical-engineer shim passes through tool-specific parameter."""
        tool = CriticalEngineerTool()
        custom_guidance = "Custom web search guidance for testing"
        result = tool.get_websearch_instruction(use_websearch=True, tool_specific=custom_guidance)
        assert custom_guidance in result, "Tool-specific parameter must be passed through"

    def test_critical_engineer_shim_none_uses_default(self):
        """Test critical-engineer shim uses default when use_websearch=None."""
        tool = CriticalEngineerTool()
        result = tool.get_websearch_instruction(use_websearch=None)
        # Default is True, so should return instruction
        assert "WEB SEARCH CAPABILITY" in result, "Shim must use default True when use_websearch=None"

    def test_backward_compatibility_with_old_callers(self):
        """Test that old code calling with use_websearch param still works."""
        # Simulate old caller code that explicitly passes use_websearch
        tool = CriticalEngineerTool()

        # Old caller: use_websearch=True
        result = tool.get_websearch_instruction(use_websearch=True)
        assert "WEB SEARCH CAPABILITY" in result

        # Old caller: use_websearch=False
        result = tool.get_websearch_instruction(use_websearch=False)
        assert result == ""

    def test_forward_compatibility_new_callers_omit_param(self):
        """Test that new code omitting use_websearch param works (uses default)."""
        # Simulate new caller code that omits use_websearch parameter
        tool = CriticalEngineerTool()

        # New caller: use_websearch parameter omitted entirely
        result = tool.get_websearch_instruction()
        # Should use default (True) and return instruction
        assert "WEB SEARCH CAPABILITY" in result

        # Can still override with explicit False if needed
        result = tool.get_websearch_instruction(use_websearch=False)
        assert result == ""
