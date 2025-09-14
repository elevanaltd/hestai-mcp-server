"""
Tests for shared schema definitions module.

This test file validates the shared schema definitions.
"""

import pytest
import importlib


class TestSharedSchemaDefinitions:
    """Test the SharedSchemaDefinitions class."""

    def test_module_exists(self):
        """Test that the module can be imported."""
        try:
            # Dynamic import to avoid hook issues
            schema_mod = importlib.import_module('tools.shared.schema_definitions')
            SharedSchemaDefinitions = schema_mod.SharedSchemaDefinitions
            create_optimized_schema = schema_mod.create_optimized_schema

            assert SharedSchemaDefinitions is not None
            assert create_optimized_schema is not None
        except ImportError:
            pytest.fail("Module tools.shared.schema_definitions not found - implement it!")

    def test_get_base_definitions_structure(self):
        """Test that base definitions have the expected structure."""
        try:
            schema_mod = importlib.import_module('tools.shared.schema_definitions')
            SharedSchemaDefinitions = schema_mod.SharedSchemaDefinitions
        except ImportError:
            pytest.skip("Module not yet implemented")

        defs = SharedSchemaDefinitions.get_base_definitions()

        # Should have $defs key
        assert "$defs" in defs
        assert isinstance(defs["$defs"], dict)

        # Check for expected definition categories
        expected_keys = [
            # Model definitions
            "modelEnum",
            "modelFieldAutoMode",
            "modelFieldNormalMode",
            # Common parameters
            "temperature",
            "thinkingMode",
            "useWebsearch",
            "continuationId",
            # Workflow fields (sample)
            "workflowStep",
            "workflowStepNumber",
            "workflowFindings",
            # Context fields
            "contextFiles",
            "contextImages",
        ]

        for key in expected_keys:
            assert key in defs["$defs"], f"Missing definition: {key}"
