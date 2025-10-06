"""
Schema Snapshot Tests for Base Tool

Purpose: Capture current schema generation behavior before base_tool.py changes.
Validates that upstream merge preserves schema generation functionality.

Safety Net: If schema generation changes, these tests fail immediately.
"""

import json
import os
from pathlib import Path

import pytest

from tools.consensus import ConsensusTool
from tools.critical_engineer import CriticalEngineerTool
from tools.debug import DebugIssueTool


class TestBaseToolSchemaSnapshot:
    """Schema snapshot validation for base_tool.py changes."""

    @pytest.fixture
    def snapshot_dir(self) -> Path:
        """Get snapshots directory."""
        return Path(__file__).parent / "snapshots"

    def _normalize_schema(self, schema: dict) -> dict:
        """Normalize schema for comparison (remove volatile fields)."""
        # Create a deep copy to avoid modifying original
        normalized = json.loads(json.dumps(schema))

        # Remove fields that might change between runs but aren't structural
        # (Currently none, but framework in place for future needs)

        return normalized

    def _save_snapshot(self, tool_name: str, schema: dict, snapshot_dir: Path) -> None:
        """Save schema snapshot to file."""
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{tool_name}_schema.json"

        normalized = self._normalize_schema(schema)

        with open(snapshot_file, "w") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)

    def _load_snapshot(self, tool_name: str, snapshot_dir: Path) -> dict:
        """Load schema snapshot from file."""
        snapshot_file = snapshot_dir / f"{tool_name}_schema.json"

        if not snapshot_file.exists():
            pytest.fail(
                f"Snapshot file not found: {snapshot_file}\n" "Run test with UPDATE_SNAPSHOTS=1 to create baseline."
            )

        with open(snapshot_file) as f:
            return json.load(f)

    def _validate_schema_structure(self, schema: dict, tool_name: str) -> None:
        """Validate basic schema structure (sanity check)."""
        assert isinstance(schema, dict), f"{tool_name}: Schema must be a dictionary"
        assert "type" in schema, f"{tool_name}: Schema must have 'type' field"
        assert "properties" in schema, f"{tool_name}: Schema must have 'properties' field"
        assert isinstance(schema["properties"], dict), f"{tool_name}: 'properties' must be a dictionary"

    def test_critical_engineer_schema_snapshot(self, snapshot_dir: Path) -> None:
        """Validate critical-engineer tool schema generation."""
        tool = CriticalEngineerTool()
        schema = tool.get_input_schema()

        # Sanity check
        self._validate_schema_structure(schema, "critical-engineer")

        # Check for expected fields
        assert "prompt" in schema["properties"], "critical-engineer must have 'prompt' field"
        assert "model" in schema["properties"], "critical-engineer must have 'model' field"
        assert "thinking_mode" in schema["properties"], "critical-engineer must have 'thinking_mode' field"

        # Snapshot comparison
        if os.environ.get("UPDATE_SNAPSHOTS") == "1":
            self._save_snapshot("critical_engineer", schema, snapshot_dir)
            pytest.skip("Snapshot updated - rerun without UPDATE_SNAPSHOTS to validate")
        else:
            expected = self._load_snapshot("critical_engineer", snapshot_dir)
            normalized = self._normalize_schema(schema)

            assert normalized == expected, (
                "critical-engineer schema changed!\n"
                "Expected schema to match baseline snapshot.\n"
                "If this change is intentional, update snapshots with: UPDATE_SNAPSHOTS=1 pytest"
            )

    def test_consensus_schema_snapshot(self, snapshot_dir: Path) -> None:
        """Validate consensus tool schema generation."""
        tool = ConsensusTool()
        schema = tool.get_input_schema()

        # Sanity check
        self._validate_schema_structure(schema, "consensus")

        # Check for expected fields
        assert "step" in schema["properties"], "consensus must have 'step' field"
        assert "models" in schema["properties"], "consensus must have 'models' field"
        assert "step_number" in schema["properties"], "consensus must have 'step_number' field"

        # Snapshot comparison
        if os.environ.get("UPDATE_SNAPSHOTS") == "1":
            self._save_snapshot("consensus", schema, snapshot_dir)
            pytest.skip("Snapshot updated - rerun without UPDATE_SNAPSHOTS to validate")
        else:
            expected = self._load_snapshot("consensus", snapshot_dir)
            normalized = self._normalize_schema(schema)

            assert normalized == expected, (
                "consensus schema changed!\n"
                "Expected schema to match baseline snapshot.\n"
                "If this change is intentional, update snapshots with: UPDATE_SNAPSHOTS=1 pytest"
            )

    def test_debug_schema_snapshot(self, snapshot_dir: Path) -> None:
        """Validate debug tool schema generation."""
        tool = DebugIssueTool()
        schema = tool.get_input_schema()

        # Sanity check
        self._validate_schema_structure(schema, "debug")

        # Check for expected fields
        assert "step" in schema["properties"], "debug must have 'step' field"
        assert "findings" in schema["properties"], "debug must have 'findings' field"
        assert "hypothesis" in schema["properties"], "debug must have 'hypothesis' field"

        # Snapshot comparison
        if os.environ.get("UPDATE_SNAPSHOTS") == "1":
            self._save_snapshot("debug", schema, snapshot_dir)
            pytest.skip("Snapshot updated - rerun without UPDATE_SNAPSHOTS to validate")
        else:
            expected = self._load_snapshot("debug", snapshot_dir)
            normalized = self._normalize_schema(schema)

            assert normalized == expected, (
                "debug schema changed!\n"
                "Expected schema to match baseline snapshot.\n"
                "If this change is intentional, update snapshots with: UPDATE_SNAPSHOTS=1 pytest"
            )

    def test_schema_snapshot_integration(self, snapshot_dir: Path) -> None:
        """Integration test: Ensure all snapshot files exist or can be created."""
        tools = [
            ("critical_engineer", CriticalEngineerTool()),
            ("consensus", ConsensusTool()),
            ("debug", DebugIssueTool()),
        ]

        update_mode = os.environ.get("UPDATE_SNAPSHOTS") == "1"

        for tool_name, tool in tools:
            schema = tool.get_input_schema()

            if update_mode:
                self._save_snapshot(tool_name, schema, snapshot_dir)
            else:
                # Verify snapshot exists
                snapshot_file = snapshot_dir / f"{tool_name}_schema.json"
                assert snapshot_file.exists(), f"Snapshot missing: {snapshot_file} (run with UPDATE_SNAPSHOTS=1)"

        if update_mode:
            pytest.skip("All snapshots updated - rerun without UPDATE_SNAPSHOTS to validate")
