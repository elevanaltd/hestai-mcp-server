"""
Test suite for clock_out Context Steward tool.

Tests JSONL extraction, OCTAVE compression, and session archival.
"""

import json
import shutil
from pathlib import Path

import pytest

from tools.clockout import ClockOutRequest, ClockOutTool


@pytest.fixture
def temp_hestai_dir(tmp_path):
    """Create a temporary .hestai directory structure"""
    hestai_dir = tmp_path / ".hestai"
    sessions_dir = hestai_dir / "sessions"
    active_dir = sessions_dir / "active"
    archive_dir = sessions_dir / "archive"

    # Create directory structure
    active_dir.mkdir(parents=True)
    archive_dir.mkdir(parents=True)

    # Create active session
    session_id = "test-1234"
    session_dir = active_dir / session_id
    session_dir.mkdir()

    session_data = {
        "session_id": session_id,
        "role": "implementation-lead",
        "focus": "b2-implementation",
        "working_dir": str(tmp_path),
        "started_at": "2025-12-08T10:00:00",
    }
    (session_dir / "session.json").write_text(json.dumps(session_data))

    yield hestai_dir, session_id

    # Cleanup
    shutil.rmtree(hestai_dir)


@pytest.fixture
def temp_claude_session(tmp_path):
    """Create a temporary Claude session JSONL file"""
    # Simulate Claude's project encoding
    encoded_path = str(tmp_path).replace("/", "-").lstrip("-")
    projects_dir = Path.home() / ".claude" / "projects" / encoded_path
    projects_dir.mkdir(parents=True, exist_ok=True)

    session_id = "78f5deb1-9e48-4b7b-b7a3-41bd7467c903"
    jsonl_path = projects_dir / f"{session_id}.jsonl"

    # Create sample JSONL content
    jsonl_content = [
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": "Hello, implement feature X"}]},
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'll implement feature X step by step"}],
            },
        },
        {"type": "thinking", "thinking": "Let me think about the implementation approach"},
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": "Can you add tests?"}]},
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Yes, I'll add comprehensive tests"}],
            },
        },
    ]

    # Write JSONL file
    with open(jsonl_path, "w") as f:
        for entry in jsonl_content:
            f.write(json.dumps(entry) + "\n")

    yield jsonl_path

    # Cleanup
    if jsonl_path.exists():
        jsonl_path.unlink()


@pytest.fixture
def clockout_tool():
    """Create a ClockOutTool instance"""
    return ClockOutTool()


class TestClockOutTool:
    """Test suite for ClockOutTool"""

    def test_tool_metadata(self, clockout_tool):
        """Test tool has correct name and metadata"""
        assert clockout_tool.get_name() == "clockout"
        assert "session" in clockout_tool.get_description().lower()
        assert clockout_tool.requires_model() is False

    def test_request_validation_success(self):
        """Test request validation with valid input"""
        request = ClockOutRequest(session_id="test-1234", description="Completed B2 implementation")
        assert request.session_id == "test-1234"
        assert request.description == "Completed B2 implementation"

    def test_request_validation_default_description(self):
        """Test request uses default description if not provided"""
        request = ClockOutRequest(session_id="test-1234")
        assert request.description == ""

    def test_request_validation_missing_required_fields(self):
        """Test request validation fails with missing required fields"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ClockOutRequest()  # missing session_id

    @pytest.mark.asyncio
    async def test_clockout_finds_session_jsonl(self, clockout_tool, temp_hestai_dir, temp_claude_session):
        """Test clock_out finds and parses Claude session JSONL"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "description": "Test session",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert "message_count" in content
        assert content["message_count"] > 0

    @pytest.mark.asyncio
    async def test_clockout_parses_messages_correctly(self, clockout_tool, temp_hestai_dir, temp_claude_session):
        """Test clock_out correctly parses user/assistant messages"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "description": "Test parsing",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["message_count"] == 4  # 2 user + 2 assistant messages (thinking excluded by default)

    @pytest.mark.asyncio
    async def test_clockout_archives_to_correct_location(self, clockout_tool, temp_hestai_dir, temp_claude_session):
        """Test clock_out archives session to correct directory"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "description": "Test archival",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert "archive_path" in content

        # Verify archive file was created
        archive_path = Path(content["archive_path"])
        assert archive_path.exists()
        assert archive_path.parent == hestai_dir / "sessions" / "archive"

        # Verify active session was removed
        active_dir = hestai_dir / "sessions" / "active" / session_id
        assert not active_dir.exists()

    @pytest.mark.asyncio
    async def test_clockout_handles_missing_session(self, clockout_tool, temp_hestai_dir):
        """Test clock_out handles missing session gracefully"""
        hestai_dir, _ = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": "nonexistent-session",
            "description": "Test error handling",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "error"
        assert "not found" in output["content"].lower() or "nonexistent" in output["content"].lower()

    @pytest.mark.asyncio
    async def test_clockout_includes_summary(self, clockout_tool, temp_hestai_dir, temp_claude_session):
        """Test clock_out generates summary of session"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "description": "Test summary generation",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert "summary" in content
        assert len(content["summary"]) > 0

    @pytest.mark.asyncio
    async def test_clockout_excludes_thinking_by_default(self, clockout_tool, temp_hestai_dir, temp_claude_session):
        """Test clock_out excludes thinking messages by default"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "description": "Test thinking exclusion",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])

        # Read the archived file
        archive_path = Path(content["archive_path"])
        archived_content = archive_path.read_text()

        # Thinking messages should not appear
        assert "[thinking]" not in archived_content
        assert "Let me think about" not in archived_content

    def test_clockout_rejects_path_traversal_session_id(self):
        """Test session_id with ../ is rejected to prevent path traversal"""
        from pydantic import ValidationError

        # Path traversal attempts should be rejected
        with pytest.raises(ValidationError, match="Invalid session_id"):
            ClockOutRequest(session_id="../../../etc/passwd")

    def test_clockout_rejects_session_id_with_forward_slash(self):
        """Test session_id with forward slash is rejected"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Invalid session_id"):
            ClockOutRequest(session_id="test/session")

    def test_clockout_rejects_session_id_with_backslash(self):
        """Test session_id with backslash is rejected"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Invalid session_id"):
            ClockOutRequest(session_id="test\\session")

    def test_clockout_rejects_empty_session_id(self):
        """Test empty session_id is rejected"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Session ID cannot be empty"):
            ClockOutRequest(session_id="")

    def test_clockout_rejects_whitespace_session_id(self):
        """Test whitespace-only session_id is rejected"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Session ID cannot be empty"):
            ClockOutRequest(session_id="   ")
