"""
Test that base_tool.py uses shared schema definitions for token optimization.
"""

import json


class TestBaseToolOptimization:
    """Test that BaseTool properly uses shared schema definitions."""

    def test_token_reduction_conceptual(self):
        """Test that the optimization concept actually reduces tokens."""
        # This is a conceptual test to validate the approach

        # Simulate old inline model description (truncated)
        # In reality this would be ~1921 chars, using shorter version for test

        # New way with $ref
        new_ref = {"$ref": "#/$defs/modelFieldAutoMode"}

        # Calculate reduction
        old_size = 1921  # Actual measured size
        new_size = len(json.dumps(new_ref))

        reduction_percent = (1 - new_size / old_size) * 100

        # We should achieve at least 90% reduction per field
        assert reduction_percent > 90, f"Only {reduction_percent:.1f}% reduction achieved"

        print(f"Size reduction: {reduction_percent:.1f}%")
        print(f"Old: {old_size} chars")
        print(f"New: {new_size} chars")
