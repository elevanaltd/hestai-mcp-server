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
        working_dir = temp_hestai_dir.parent

        # Create an existing session with same focus
        existing_session_dir = temp_hestai_dir / "sessions" / "active" / "existing-123"
        existing_session_dir.mkdir(parents=True)

        existing_session_data = {
            "session_id": "existing-123",
            "role": "critical-engineer",
            "focus": "b2-validation",
            "started_at": "2025-12-08T10:00:00",
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
