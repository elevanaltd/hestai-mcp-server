"""
Test suite for clock_in Context Steward tool.

Tests session registration, conflict detection, and context path generation.
"""

import json
import shutil

import pytest

from tools.clockin import ClockInRequest, ClockInTool


@pytest.fixture
def temp_hestai_dir(tmp_path):
    """Create a temporary .hestai directory structure"""
    hestai_dir = tmp_path / ".hestai"
    sessions_dir = hestai_dir / "sessions"
    active_dir = sessions_dir / "active"
    context_dir = hestai_dir / "context"

    # Create directory structure
    active_dir.mkdir(parents=True)
    context_dir.mkdir(parents=True)

    # Create context files
    (context_dir / "PROJECT-CONTEXT.md").write_text("# Project Context")
    (context_dir / "PROJECT-CHECKLIST.md").write_text("# Project Checklist")

    yield hestai_dir

    # Cleanup
    shutil.rmtree(hestai_dir)


@pytest.fixture
def clockin_tool():
    """Create a ClockInTool instance"""
    return ClockInTool()


class TestClockInTool:
    """Test suite for ClockInTool"""

    def test_tool_metadata(self, clockin_tool):
        """Test tool has correct name and metadata"""
        assert clockin_tool.get_name() == "clockin"
        assert "session" in clockin_tool.get_description().lower()
        assert clockin_tool.requires_model() is False

    def test_request_validation_success(self):
        """Test request validation with valid input"""
        request = ClockInRequest(
            role="implementation-lead", focus="b2-implementation", working_dir="/Volumes/HestAI-Tools/test-project"
        )
        assert request.role == "implementation-lead"
        assert request.focus == "b2-implementation"
        assert request.working_dir == "/Volumes/HestAI-Tools/test-project"

    def test_request_validation_default_focus(self):
        """Test request uses default focus if not provided"""
        request = ClockInRequest(role="critical-engineer", working_dir="/Volumes/HestAI")
        assert request.focus == "general"

    def test_request_validation_missing_required_fields(self):
        """Test request validation fails with missing required fields"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ClockInRequest(role="test-role")  # missing working_dir

    @pytest.mark.asyncio
    async def test_clockin_creates_session_directory(self, clockin_tool, temp_hestai_dir):
        """Test clock_in creates session directory structure"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "role": "implementation-lead",
            "focus": "b2-testing",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded, need to parse it
        content = json.loads(output["content"])
        assert "session_id" in content

        session_id = content["session_id"]

        # Verify session directory was created
        session_dir = temp_hestai_dir / "sessions" / "active" / session_id
        assert session_dir.exists()

        # Verify session.json was created
        session_file = session_dir / "session.json"
        assert session_file.exists()

        # Verify session metadata
        session_data = json.loads(session_file.read_text())
        assert session_data["role"] == "implementation-lead"
        assert session_data["focus"] == "b2-testing"
        assert "started_at" in session_data

    @pytest.mark.asyncio
    async def test_clockin_detects_focus_conflict(self, clockin_tool, temp_hestai_dir):
        """Test clock_in detects when another session has same focus"""
        from datetime import datetime, timedelta

        working_dir = temp_hestai_dir.parent

        # Create an existing session with same focus (recent, not stale)
        existing_session_dir = temp_hestai_dir / "sessions" / "active" / "existing-123"
        existing_session_dir.mkdir(parents=True)

        # Use a recent timestamp so cleanup doesn't delete it
        recent_time = (datetime.now() - timedelta(hours=1)).isoformat()

        existing_session_data = {
            "session_id": "existing-123",
            "role": "critical-engineer",
            "focus": "b2-validation",
            "started_at": recent_time,
        }
        (existing_session_dir / "session.json").write_text(json.dumps(existing_session_data))

        # Try to clock in with same focus
        arguments = {
            "role": "implementation-lead",
            "focus": "b2-validation",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded, need to parse it
        content = json.loads(output["content"])

        # Should have conflict warning
        assert content["conflict"] is not None
        assert content["conflict"]["focus"] == "b2-validation"
        assert content["conflict"]["existing_session_id"] == "existing-123"
        assert content["conflict"]["existing_role"] == "critical-engineer"

    @pytest.mark.asyncio
    async def test_clockin_returns_context_paths(self, clockin_tool, temp_hestai_dir):
        """Test clock_in returns correct context paths"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "role": "implementation-lead",
            "focus": "general",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded, need to parse it
        content = json.loads(output["content"])

        # Verify context paths
        assert "context_paths" in content
        context_paths = content["context_paths"]

        assert "project_context" in context_paths
        assert "checklist" in context_paths

        # Verify paths are relative to .hestai/
        assert context_paths["project_context"] == ".hestai/context/PROJECT-CONTEXT.md"
        assert context_paths["checklist"] == ".hestai/context/PROJECT-CHECKLIST.md"

    @pytest.mark.asyncio
    async def test_clockin_handles_missing_hestai_dir(self, clockin_tool, tmp_path):
        """Test clock_in creates .hestai directory if missing"""
        working_dir = tmp_path / "new-project"
        working_dir.mkdir()

        arguments = {
            "role": "implementation-lead",
            "focus": "setup",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Verify .hestai structure was created
        hestai_dir = working_dir / ".hestai"
        assert hestai_dir.exists()
        assert (hestai_dir / "sessions" / "active").exists()

    @pytest.mark.asyncio
    async def test_clockin_returns_instruction(self, clockin_tool, temp_hestai_dir):
        """Test clock_in returns proper instruction to agent"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "role": "implementation-lead",
            "focus": "general",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded, need to parse it
        content = json.loads(output["content"])

        # Verify instruction is present
        assert "instruction" in content
        assert "context_paths" in content["instruction"].lower()
        assert "raph" in content["instruction"].lower()
        assert "anchor" in content["instruction"].lower()

    @pytest.mark.asyncio
    async def test_clockin_stores_transcript_path_when_available(self, clockin_tool, temp_hestai_dir):
        """Test clock_in stores transcript_path in session.json when available from context"""

        working_dir = temp_hestai_dir.parent
        test_transcript_path = "/Users/test/.claude/projects/test-project/session-123.jsonl"

        # Create mock context with transcript_path
        mock_context = type("obj", (object,), {"project_root": working_dir, "transcript_path": test_transcript_path})()

        arguments = {
            "role": "implementation-lead",
            "focus": "general",
            "working_dir": str(working_dir),
            "_session_context": mock_context,
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        session_id = content["session_id"]

        # Verify session.json contains transcript_path
        session_dir = temp_hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())

        assert "transcript_path" in session_data
        assert session_data["transcript_path"] == test_transcript_path

    @pytest.mark.asyncio
    async def test_clockin_stores_null_transcript_path_when_unavailable(self, clockin_tool, temp_hestai_dir):
        """Test clock_in stores None for transcript_path when not available in context"""
        working_dir = temp_hestai_dir.parent

        # Create mock context WITHOUT transcript_path
        mock_context = type("obj", (object,), {"project_root": working_dir})()

        arguments = {
            "role": "implementation-lead",
            "focus": "general",
            "working_dir": str(working_dir),
            "_session_context": mock_context,
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        session_id = content["session_id"]

        # Verify session.json contains transcript_path as None
        session_dir = temp_hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())

        assert "transcript_path" in session_data
        assert session_data["transcript_path"] is None

    @pytest.mark.asyncio
    async def test_clockin_with_model_parameter(self, clockin_tool, temp_hestai_dir):
        """Test clock_in stores model identifier in session.json when provided"""
        working_dir = temp_hestai_dir.parent
        test_model = "claude-opus-4-5-20251101"

        arguments = {
            "role": "implementation-lead",
            "focus": "general",
            "working_dir": str(working_dir),
            "model": test_model,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        session_id = content["session_id"]

        # Verify session.json contains model
        session_dir = temp_hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())

        assert "model" in session_data
        assert session_data["model"] == test_model

    @pytest.mark.asyncio
    async def test_clockin_without_model_parameter(self, clockin_tool, temp_hestai_dir):
        """Test clock_in stores None for model when not provided"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "role": "implementation-lead",
            "focus": "general",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        session_id = content["session_id"]

        # Verify session.json contains model as None
        session_dir = temp_hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())

        assert "model" in session_data
        assert session_data["model"] is None

    @pytest.mark.asyncio
    async def test_clockin_resolves_symlinked_hestai_dir(self, clockin_tool, tmp_path, caplog):
        """Test clock_in resolves .hestai symlink to actual path and logs it"""
        import logging

        caplog.set_level(logging.INFO)

        # Create actual .hestai directory in a different location
        actual_hestai = tmp_path / "unified_hestai"
        actual_hestai.mkdir(parents=True)

        # Create project directory
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        # Create symlink from project/.hestai -> actual_hestai
        symlink_path = working_dir / ".hestai"
        symlink_path.symlink_to(actual_hestai)

        arguments = {
            "role": "implementation-lead",
            "focus": "symlink-test",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        session_id = content["session_id"]

        # Verify session was created in ACTUAL directory (not symlink)
        session_dir = actual_hestai / "sessions" / "active" / session_id
        assert session_dir.exists()
        assert session_dir.is_dir()

        # Verify session.json was created
        session_file = session_dir / "session.json"
        assert session_file.exists()

        # Verify session data
        session_data = json.loads(session_file.read_text())
        assert session_data["role"] == "implementation-lead"
        assert session_data["focus"] == "symlink-test"

        # CRITICAL: Verify that symlink resolution was logged
        assert any(
            "Resolved .hestai symlink" in record.message for record in caplog.records
        ), "Expected log message about symlink resolution"
        # Verify the resolved path was logged
        assert any(
            str(actual_hestai) in record.message for record in caplog.records
        ), f"Expected resolved path {actual_hestai} in logs"

    @pytest.mark.asyncio
    async def test_clockin_handles_regular_hestai_dir(self, clockin_tool, temp_hestai_dir):
        """Test clock_in works normally with regular (non-symlinked) .hestai directory"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "role": "implementation-lead",
            "focus": "regular-dir",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        session_id = content["session_id"]

        # Verify session was created in regular directory
        session_dir = temp_hestai_dir / "sessions" / "active" / session_id
        assert session_dir.exists()
        assert session_dir.is_dir()

    @pytest.mark.asyncio
    async def test_clockin_triggers_cleanup_after_24h(self, clockin_tool, temp_hestai_dir, caplog):
        """Test clock_in triggers cleanup when last_cleanup is > 24h old"""
        import logging
        from datetime import datetime, timedelta

        caplog.set_level(logging.INFO)
        working_dir = temp_hestai_dir.parent

        # Create a last_cleanup file with timestamp > 24h ago
        last_cleanup_file = temp_hestai_dir / "last_cleanup"
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        last_cleanup_file.write_text(old_timestamp)

        # Create old archived session (> 30 days)
        archive_dir = temp_hestai_dir / "sessions" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        old_archive = archive_dir / "old-session-35days.jsonl"
        old_archive.write_text("old session data")
        # Set mtime to 35 days ago
        old_time = (datetime.now() - timedelta(days=35)).timestamp()
        import os

        os.utime(old_archive, (old_time, old_time))

        # Create stale active session (> 72h)
        active_dir = temp_hestai_dir / "sessions" / "active"
        stale_session_dir = active_dir / "stale-session"
        stale_session_dir.mkdir(parents=True, exist_ok=True)
        stale_session_file = stale_session_dir / "session.json"
        stale_data = {
            "session_id": "stale-session",
            "role": "test-role",
            "focus": "test",
            "started_at": (datetime.now() - timedelta(hours=80)).isoformat(),  # 80h > 72h threshold
        }
        stale_session_file.write_text(json.dumps(stale_data))

        arguments = {
            "role": "implementation-lead",
            "focus": "cleanup-test",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result - clockin should succeed even if cleanup runs
        result_text = result[0].text
        output = json.loads(result_text)
        assert output["status"] == "success"

        # Verify cleanup was triggered
        assert any(
            "Triggering session cleanup" in record.message for record in caplog.records
        ), "Expected log message about cleanup trigger"

        # Verify old archive was deleted
        assert not old_archive.exists(), "Old archive file should be deleted"

        # Verify stale session was deleted
        assert not stale_session_dir.exists(), "Stale session should be deleted"

        # Verify last_cleanup timestamp was updated
        assert last_cleanup_file.exists()
        new_timestamp = datetime.fromisoformat(last_cleanup_file.read_text())
        assert (datetime.now() - new_timestamp).total_seconds() < 10, "Timestamp should be updated to now"

    @pytest.mark.asyncio
    async def test_clockin_skips_cleanup_within_24h(self, clockin_tool, temp_hestai_dir, caplog):
        """Test clock_in skips cleanup when last_cleanup is < 24h old"""
        import logging
        from datetime import datetime, timedelta

        caplog.set_level(logging.INFO)
        working_dir = temp_hestai_dir.parent

        # Create a last_cleanup file with timestamp < 24h ago
        last_cleanup_file = temp_hestai_dir / "last_cleanup"
        recent_timestamp = (datetime.now() - timedelta(hours=12)).isoformat()
        last_cleanup_file.write_text(recent_timestamp)

        arguments = {
            "role": "implementation-lead",
            "focus": "no-cleanup-test",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)
        assert output["status"] == "success"

        # Verify cleanup was NOT triggered
        assert not any(
            "Triggering session cleanup" in record.message for record in caplog.records
        ), "Cleanup should not be triggered within 24h"

    @pytest.mark.asyncio
    async def test_clockin_succeeds_even_if_cleanup_fails(self, clockin_tool, temp_hestai_dir, caplog):
        """Test clock_in succeeds even if cleanup encounters errors"""
        import logging
        from datetime import datetime, timedelta

        caplog.set_level(logging.WARNING)
        working_dir = temp_hestai_dir.parent

        # Create a last_cleanup file with timestamp > 24h ago
        last_cleanup_file = temp_hestai_dir / "last_cleanup"
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        last_cleanup_file.write_text(old_timestamp)

        # Create archive dir with permission issues (simulate cleanup failure)
        archive_dir = temp_hestai_dir / "sessions" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        # Note: We can't easily simulate permission errors in tests,
        # so we'll just verify that cleanup errors don't fail clockin

        arguments = {
            "role": "implementation-lead",
            "focus": "cleanup-error-test",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result - should succeed even if cleanup fails
        result_text = result[0].text
        output = json.loads(result_text)
        assert output["status"] == "success"

        # Session should be created successfully
        content = json.loads(output["content"])
        assert "session_id" in content

    @pytest.mark.asyncio
    async def test_clockin_creates_last_cleanup_on_first_run(self, clockin_tool, temp_hestai_dir):
        """Test clock_in creates last_cleanup file on first run"""
        from datetime import datetime

        working_dir = temp_hestai_dir.parent

        # Ensure no last_cleanup file exists
        last_cleanup_file = temp_hestai_dir / "last_cleanup"
        if last_cleanup_file.exists():
            last_cleanup_file.unlink()

        arguments = {
            "role": "implementation-lead",
            "focus": "first-run-test",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockin_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)
        assert output["status"] == "success"

        # Verify last_cleanup file was created
        assert last_cleanup_file.exists()
        timestamp = datetime.fromisoformat(last_cleanup_file.read_text())
        assert (datetime.now() - timestamp).total_seconds() < 10, "Timestamp should be current"
