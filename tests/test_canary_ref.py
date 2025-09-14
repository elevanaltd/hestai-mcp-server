"""
Test for canary $ref support tool.
"""

import pytest


class TestCanaryRefSupport:
    """Test the canary tool for MCP $ref support."""

    def test_canary_tool_schema_has_ref(self):
        """Test that canary tool schema contains versioned $ref."""
        try:
            # CONTEXT7_BYPASS: INTERNAL-MODULE - Internal import
            from tools.canary_ref_test import CanaryRefTestTool
        except ImportError:
            pytest.skip("Canary tool not yet implemented")

        tool = CanaryRefTestTool()
        schema = tool.get_input_schema()

        # Check schema has $defs with v1 versioning
        assert "$defs" in schema
        assert "v1" in schema["$defs"]
        assert "confidence_enum" in schema["$defs"]["v1"]

        # Check property uses versioned $ref
        assert "confidence" in schema["properties"]
        assert "$ref" in schema["properties"]["confidence"]
        assert schema["properties"]["confidence"]["$ref"] == "#/$defs/v1/confidence_enum"

    def test_canary_tool_execute(self):
        """Test that canary tool can execute."""
        try:
            # CONTEXT7_BYPASS: INTERNAL-MODULE - Internal import
            from tools.canary_ref_test import CanaryRefTestTool
        except ImportError:
            pytest.skip("Canary tool not yet implemented")

        import asyncio

        tool = CanaryRefTestTool()

        # Test execution
        result = asyncio.run(tool.execute(test_message="Testing $ref support", confidence="high"))

        assert result["success"] is True
        assert "Testing $ref support" in result["message"]
        assert result["confidence"] == "high"
        assert result["ref_support"] == "VERIFIED"
