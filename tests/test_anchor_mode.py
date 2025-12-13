"""
Test suite for Anchor Architecture migration.

Tests anchor mode detection, event emission, and backward compatibility
with legacy .hestai/context/ structure.

TDD RED Phase - These tests MUST fail initially.
"""

import json

import pytest

from tools.clockin import ClockInTool
from tools.contextupdate import ContextUpdateTool


@pytest.fixture
def temp_anchor_project(tmp_path):
    """Create a temporary project with anchor structure (.hestai/snapshots/)"""
    project_root = tmp_path / "anchor_project"
    project_root.mkdir()

    # Create anchor structure
    hestai_dir = project_root / ".hestai"
    snapshots_dir = hestai_dir / "snapshots"
    events_dir = hestai_dir / "events"
    sessions_dir = hestai_dir / "sessions" / "active"

    snapshots_dir.mkdir(parents=True)
    events_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    # Create READ-ONLY snapshot files
    (snapshots_dir / "PROJECT-CONTEXT.md").write_text("# Anchor Project Context")
    (snapshots_dir / "PROJECT-CHECKLIST.md").write_text("# Anchor Checklist")

    return project_root


@pytest.fixture
def temp_legacy_project(tmp_path):
    """Create a temporary project with legacy structure (.hestai/context/)"""
    project_root = tmp_path / "legacy_project"
    project_root.mkdir()

    # Create legacy structure
    hestai_dir = project_root / ".hestai"
    context_dir = hestai_dir / "context"
    sessions_dir = hestai_dir / "sessions" / "active"

    context_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    # Create legacy context files
    (context_dir / "PROJECT-CONTEXT.md").write_text("# Legacy Project Context")
    (context_dir / "PROJECT-CHECKLIST.md").write_text("# Legacy Checklist")

    return project_root


class TestAnchorModeDetection:
    """Test anchor vs legacy mode detection"""

    @pytest.mark.asyncio
    async def test_clockin_detects_anchor_mode(self, temp_anchor_project):
        """
        TEST: ClockInTool detects anchor mode when .hestai/snapshots/ exists

        Expected behavior:
        - Detect snapshots/ directory exists
        - Return context_paths pointing to snapshots/
        - Set is_anchor_mode=true in session metadata
        """
        clockin_tool = ClockInTool()

        arguments = {
            "role": "implementation-lead",
            "focus": "anchor-test",
            "working_dir": str(temp_anchor_project),
        }

        result = await clockin_tool.execute(arguments)
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        content = json.loads(output["content"])

        # TEST: context_paths should point to snapshots/
        assert content["context_paths"]["project_context"] == ".hestai/snapshots/PROJECT-CONTEXT.md"
        assert content["context_paths"]["checklist"] == ".hestai/snapshots/PROJECT-CHECKLIST.md"

        # TEST: Session metadata should include is_anchor_mode flag
        session_id = content["session_id"]
        hestai_dir = temp_anchor_project / ".hestai"
        session_file = hestai_dir / "sessions" / "active" / session_id / "session.json"

        session_data = json.loads(session_file.read_text())
        assert session_data.get("is_anchor_mode") is True

    @pytest.mark.asyncio
    async def test_clockin_detects_legacy_mode(self, temp_legacy_project):
        """
        TEST: ClockInTool detects legacy mode when only .hestai/context/ exists

        Expected behavior:
        - Detect only context/ directory exists
        - Return context_paths pointing to context/
        - Set is_anchor_mode=false in session metadata
        """
        clockin_tool = ClockInTool()

        arguments = {
            "role": "implementation-lead",
            "focus": "legacy-test",
            "working_dir": str(temp_legacy_project),
        }

        result = await clockin_tool.execute(arguments)
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        content = json.loads(output["content"])

        # TEST: context_paths should point to context/
        assert content["context_paths"]["project_context"] == ".hestai/context/PROJECT-CONTEXT.md"
        assert content["context_paths"]["checklist"] == ".hestai/context/PROJECT-CHECKLIST.md"

        # TEST: Session metadata should include is_anchor_mode flag
        session_id = content["session_id"]
        hestai_dir = temp_legacy_project / ".hestai"
        session_file = hestai_dir / "sessions" / "active" / session_id / "session.json"

        session_data = json.loads(session_file.read_text())
        assert session_data.get("is_anchor_mode") is False


class TestEventEmission:
    """Test event-sourced context updates in anchor mode"""

    @pytest.mark.asyncio
    async def test_contextupdate_emits_event_in_anchor_mode(self, temp_anchor_project):
        """
        TEST: ContextUpdateTool emits event to events/ instead of writing to snapshots/

        CRITICAL CONSTRAINT: snapshots/ is READ-ONLY

        Expected behavior:
        - Detect anchor mode (snapshots/ exists)
        - Emit event to .hestai/events/YYYY-MM-DD/
        - Do NOT write directly to snapshots/
        - Return success without file modification
        """
        contextupdate_tool = ContextUpdateTool()

        arguments = {
            "target": "PROJECT-CONTEXT",
            "intent": "Update architecture section",
            "content": "New architecture details",
            "working_dir": str(temp_anchor_project),
        }

        # Capture original snapshot content (should not change)
        snapshots_dir = temp_anchor_project / ".hestai" / "snapshots"
        original_content = (snapshots_dir / "PROJECT-CONTEXT.md").read_text()

        result = await contextupdate_tool.execute(arguments)
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        content = json.loads(output["content"])

        # TEST: Event file was created
        events_dir = temp_anchor_project / ".hestai" / "events"
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        daily_events_dir = events_dir / today

        assert daily_events_dir.exists()
        event_files = list(daily_events_dir.glob("*-context_update.json"))
        assert len(event_files) == 1

        # TEST: Event contains correct structure per spec/CONTEXT-ANCHOR-STRUCTURE.md
        event_data = json.loads(event_files[0].read_text())
        assert "id" in event_data
        assert "timestamp" in event_data
        assert "session_id" in event_data
        assert "role" in event_data
        assert event_data["type"] == "context_update"
        assert event_data["payload"]["target_file"] == "PROJECT-CONTEXT.md"
        assert event_data["payload"]["section"] is None
        assert event_data["payload"]["operation"] == "append"
        assert event_data["payload"]["content"] == "New architecture details"

        # TEST: Snapshot was NOT modified (READ-ONLY enforcement)
        current_content = (snapshots_dir / "PROJECT-CONTEXT.md").read_text()
        assert current_content == original_content

        # TEST: Response indicates event emission, not direct write
        assert content.get("mode") == "event_emitted"

    @pytest.mark.asyncio
    async def test_contextupdate_writes_directly_in_legacy_mode(self, temp_legacy_project):
        """
        TEST: ContextUpdateTool writes directly to context/ in legacy mode

        Expected behavior:
        - Detect legacy mode (no snapshots/ directory)
        - Write directly to .hestai/context/
        - No event emission
        - Return success with file modification
        """
        contextupdate_tool = ContextUpdateTool()

        # Create inbox directory (required for contextupdate)
        inbox_dir = temp_legacy_project / ".hestai" / "inbox"
        inbox_dir.mkdir(parents=True)

        arguments = {
            "target": "PROJECT-CONTEXT",
            "intent": "Update architecture section",
            "content": "New architecture details",
            "working_dir": str(temp_legacy_project),
        }

        result = await contextupdate_tool.execute(arguments)
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        content = json.loads(output["content"])

        # TEST: File was modified directly
        context_dir = temp_legacy_project / ".hestai" / "context"
        updated_content = (context_dir / "PROJECT-CONTEXT.md").read_text()
        assert "New architecture details" in updated_content

        # TEST: No events directory created
        events_dir = temp_legacy_project / ".hestai" / "events"
        assert not events_dir.exists()

        # TEST: Response indicates direct write
        assert content.get("merged") is True


class TestFileLookup:
    """Test file lookup prioritizes snapshots/ over context/"""

    def test_find_context_file_prefers_snapshots(self, temp_anchor_project):
        """
        TEST: find_context_file searches snapshots/ before context/

        Expected behavior:
        - Search .hestai/snapshots/ first (anchor)
        - Fallback to .hestai/context/ (legacy)
        - Return first match
        """
        from tools.context_steward.file_lookup import find_context_file

        # Should find in snapshots/
        result = find_context_file(temp_anchor_project, "PROJECT-CONTEXT.md")
        assert result is not None
        assert "snapshots" in str(result)

    def test_find_context_file_fallback_to_context(self, temp_legacy_project):
        """
        TEST: find_context_file falls back to context/ when snapshots/ doesn't exist

        Expected behavior:
        - snapshots/ doesn't exist
        - Find in .hestai/context/
        """
        from tools.context_steward.file_lookup import find_context_file

        # Should find in context/
        result = find_context_file(temp_legacy_project, "PROJECT-CONTEXT.md")
        assert result is not None
        assert "context" in str(result)


class TestBackwardCompatibility:
    """Test backward compatibility with legacy structure"""

    @pytest.mark.asyncio
    async def test_both_modes_coexist(self, tmp_path):
        """
        TEST: System handles projects with both anchor and legacy structures

        Scenario: Migration in progress, both structures exist
        Expected: Anchor (snapshots/) takes precedence
        """
        project_root = tmp_path / "mixed_project"
        project_root.mkdir()

        # Create BOTH structures
        hestai_dir = project_root / ".hestai"
        snapshots_dir = hestai_dir / "snapshots"
        context_dir = hestai_dir / "context"
        sessions_dir = hestai_dir / "sessions" / "active"

        snapshots_dir.mkdir(parents=True)
        context_dir.mkdir(parents=True)
        sessions_dir.mkdir(parents=True)

        # Both have files
        (snapshots_dir / "PROJECT-CONTEXT.md").write_text("# Anchor Version")
        (context_dir / "PROJECT-CONTEXT.md").write_text("# Legacy Version")

        from tools.context_steward.file_lookup import find_context_file

        # Should prefer anchor/snapshots
        result = find_context_file(project_root, "PROJECT-CONTEXT.md")
        content = result.read_text()
        assert "Anchor Version" in content
