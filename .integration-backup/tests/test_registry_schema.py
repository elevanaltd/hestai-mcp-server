"""Test registry tool MCP schema exposure."""

# TECHNICAL-ARCHITECT-APPROVED: TECHNICAL-ARCHITECT-20250904-0dd4d8cd
# Testing MCP schema completeness after registry fix

# Context7: consulted for pytest

# Context7: consulted for tools.registry - internal module
from tools.registry import RegistryTool


class TestRegistryMCPSchema:
    """Test registry tool MCP schema for parameter exposure."""

    def test_all_parameters_exposed_in_schema(self):
        """Verify all required parameters are exposed in get_tool_fields()."""
        tool = RegistryTool(db_path=":memory:")
        fields = tool.get_tool_fields()

        # Core field must be present
        assert "action" in fields
        assert fields["action"]["type"] == "string"
        assert set(fields["action"]["enum"]) == {
            "create_blocked",
            "approve",
            "reject",
            "validate",
            "list_pending",
            "cleanup",
        }

        # Approve/reject parameters
        assert "uuid" in fields
        assert "specialist" in fields
        assert "reason" in fields
        assert "education" in fields

        # Validate parameters
        assert "token" in fields

        # Create_blocked parameters
        assert "description" in fields
        assert "file_path" in fields
        assert "specialist_type" in fields
        assert "blocked_content" in fields

    def test_field_descriptions_indicate_requirements(self):
        """Verify field descriptions indicate which actions require them."""
        tool = RegistryTool(db_path=":memory:")
        fields = tool.get_tool_fields()

        # Check that descriptions indicate requirements
        assert "required for approve, reject, validate" in fields["uuid"]["description"]
        assert "required for approve, reject" in fields["specialist"]["description"]
        assert "required for reject" in fields["education"]["description"]
        assert "required for validate" in fields["token"]["description"]
        assert "required for create_blocked" in fields["description"]["description"]

    def test_get_input_schema_includes_all_fields(self):
        """Verify get_input_schema() includes all tool fields."""
        tool = RegistryTool(db_path=":memory:")
        schema = tool.get_input_schema()

        # Schema should have properties with all our fields
        assert "properties" in schema
        properties = schema["properties"]

        # All fields from get_tool_fields should be in schema
        tool_fields = tool.get_tool_fields()
        for field_name in tool_fields:
            assert field_name in properties, f"Field {field_name} missing from input schema"

    def test_only_action_is_required_in_base_schema(self):
        """Verify only 'action' is marked as required in base schema."""
        tool = RegistryTool(db_path=":memory:")

        # get_required_fields should only require 'action'
        required = tool.get_required_fields()
        assert required == ["action"]

        # Input schema should reflect this
        schema = tool.get_input_schema()
        if "required" in schema:
            # Only action should be globally required
            # Other fields are conditionally required based on action value
            assert "action" in schema["required"]
