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

    # Create active session - use unique session_id for testing to avoid conflicts
    # Using a different UUID than production sessions to prevent temporal beacon collisions
    session_id = "test-clockout-00000000-0000-0000-0000-000000000001"
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

    # Use the same unique test session_id to match temp_hestai_dir fixture
    session_id = "test-clockout-00000000-0000-0000-0000-000000000001"
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
        # With layered resolution, temporal beacon may find test fixture with known messages
        # Just verify we got some messages (at least the fixture's 4 messages)
        assert content["message_count"] >= 4  # At minimum: 2 user + 2 assistant (thinking excluded)

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

    @pytest.mark.asyncio
    async def test_clockout_uses_transcript_path_from_session(self, clockout_tool, temp_hestai_dir, monkeypatch):
        """Test clock_out prefers transcript_path from session.json when available"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Create a real transcript file at the path stored in session.json
        test_transcript_path = working_dir / "test-transcript.jsonl"

        # Create sample JSONL content
        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "Test message"}]},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Test response"}],
                },
            },
        ]

        # Write JSONL file
        with open(test_transcript_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Update session.json to include transcript_path
        session_dir = hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())
        session_data["transcript_path"] = str(test_transcript_path)
        session_file.write_text(json.dumps(session_data))

        # Mock validation to allow test path (simulates valid hook-provided path)
        def mock_validate(path, allowed_root=None):
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        monkeypatch.setattr(clockout_tool, "_validate_path_containment", mock_validate)

        arguments = {
            "session_id": session_id,
            "description": "Test transcript_path usage",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["message_count"] == 2  # Should have found the messages

        # Cleanup
        test_transcript_path.unlink()

    @pytest.mark.asyncio
    async def test_clockout_falls_back_to_discovery_when_path_missing(
        self, clockout_tool, temp_hestai_dir, temp_claude_session
    ):
        """Test clock_out falls back to path discovery when transcript_path is missing or invalid"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Update session.json with an invalid transcript_path
        session_dir = hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())
        session_data["transcript_path"] = "/nonexistent/path/to/transcript.jsonl"
        session_file.write_text(json.dumps(session_data))

        arguments = {
            "session_id": session_id,
            "description": "Test fallback to discovery",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await clockout_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        # Should have fallen back to discovery and found the temp_claude_session JSONL
        assert content["message_count"] > 0


class TestTranscriptPathResolution:
    """Test suite for layered transcript path resolution"""

    def test_temporal_beacon_finds_recent_jsonl_with_session_id(self, clockout_tool, tmp_path, monkeypatch):
        """Test temporal beacon finds JSONL file modified in last 24h containing session_id"""
        # Create Claude projects directory
        claude_projects = tmp_path / ".claude" / "projects"
        claude_projects.mkdir(parents=True)

        # Create project directory
        project_dir = claude_projects / "test-project-path"
        project_dir.mkdir()

        # Create JSONL file with session_id in content
        session_id = "test-session-12345"
        jsonl_path = project_dir / "session-abc123.jsonl"

        jsonl_content = [
            {"type": "session_start", "session_id": session_id},
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Mock _validate_path_containment to allow test path
        def mock_validate(path, allowed_root=None):
            # For tests, just return resolved path
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        monkeypatch.setattr(clockout_tool, "_validate_path_containment", mock_validate)

        # Test temporal beacon discovery
        found_path = clockout_tool._find_by_temporal_beacon(session_id, claude_projects)

        assert found_path == jsonl_path
        assert found_path.exists()

    def test_temporal_beacon_ignores_old_files(self, clockout_tool, tmp_path, monkeypatch):
        """Test temporal beacon ignores files older than 24h"""
        import os
        import time

        claude_projects = tmp_path / ".claude" / "projects"
        claude_projects.mkdir(parents=True)

        project_dir = claude_projects / "test-project-path"
        project_dir.mkdir()

        session_id = "test-session-67890"
        old_jsonl = project_dir / "old-session.jsonl"

        jsonl_content = [{"type": "session_start", "session_id": session_id}]

        with open(old_jsonl, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Make file appear old (modify timestamp to 25h ago)
        old_time = time.time() - (25 * 60 * 60)
        old_jsonl.touch()
        os.utime(old_jsonl, (old_time, old_time))

        # Mock validation
        def mock_validate(path, allowed_root=None):
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        monkeypatch.setattr(clockout_tool, "_validate_path_containment", mock_validate)

        # Should not find old file
        with pytest.raises(FileNotFoundError):
            clockout_tool._find_by_temporal_beacon(session_id, claude_projects)

    def test_metadata_inversion_finds_via_project_config(self, clockout_tool, tmp_path, monkeypatch):
        """Test metadata inversion finds transcript via project_config.json"""
        # Create project root
        project_root = tmp_path / "my-project"
        project_root.mkdir()

        # Create Claude projects directory
        claude_projects = tmp_path / ".claude" / "projects"
        claude_projects.mkdir(parents=True)

        # Create encoded project directory
        encoded_path = str(project_root).replace("/", "-").lstrip("-")
        project_dir = claude_projects / encoded_path
        project_dir.mkdir()

        # Create project_config.json
        project_config = {"rootPath": str(project_root)}
        (project_dir / "project_config.json").write_text(json.dumps(project_config))

        # Create JSONL file
        session_id = "metadata-test-session"
        jsonl_path = project_dir / "session-xyz789.jsonl"

        jsonl_content = [{"type": "session_start", "session_id": session_id}]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Mock validation
        def mock_validate(path, allowed_root=None):
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        monkeypatch.setattr(clockout_tool, "_validate_path_containment", mock_validate)

        # Test metadata inversion
        found_path = clockout_tool._find_by_metadata_inversion(project_root, claude_projects)

        assert found_path == jsonl_path

    def test_metadata_inversion_respects_max_projects_limit(self, clockout_tool, tmp_path, monkeypatch):
        """Test metadata inversion stops after MAX_PROJECTS_SCAN directories"""
        claude_projects = tmp_path / ".claude" / "projects"
        claude_projects.mkdir(parents=True)

        # Create 60 project directories (exceeds MAX_PROJECTS_SCAN=50)
        for i in range(60):
            (claude_projects / f"project-{i}").mkdir()

        project_root = tmp_path / "target-project"

        # Mock validation
        def mock_validate(path, allowed_root=None):
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        monkeypatch.setattr(clockout_tool, "_validate_path_containment", mock_validate)

        # Should raise error after hitting limit
        with pytest.raises(FileNotFoundError, match="MAX_PROJECTS_SCAN"):
            clockout_tool._find_by_metadata_inversion(project_root, claude_projects)

    def test_explicit_config_uses_env_variable(self, clockout_tool, tmp_path, monkeypatch):
        """Test explicit config uses CLAUDE_TRANSCRIPT_DIR environment variable"""
        # Create custom transcript directory
        custom_dir = tmp_path / "custom-transcripts"
        custom_dir.mkdir()

        session_id = "explicit-config-session"
        jsonl_path = custom_dir / "my-session.jsonl"

        jsonl_content = [{"type": "session_start", "session_id": session_id}]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Set environment variable
        monkeypatch.setenv("CLAUDE_TRANSCRIPT_DIR", str(custom_dir))

        # Mock validation
        def mock_validate(path, allowed_root=None):
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        monkeypatch.setattr(clockout_tool, "_validate_path_containment", mock_validate)

        # Test explicit config
        found_path = clockout_tool._find_by_explicit_config(session_id)

        assert found_path == jsonl_path

    def test_path_containment_rejects_traversal_attempts(self, clockout_tool):
        """Test path containment validation rejects path traversal attempts"""
        # Attempt to access file outside allowed root
        malicious_path = Path("~/.claude/../../etc/passwd").expanduser()

        with pytest.raises(Exception, match="Path traversal"):
            clockout_tool._validate_path_containment(malicious_path)

    def test_path_containment_allows_valid_paths(self, clockout_tool, tmp_path):
        """Test path containment validation allows valid paths within allowed root"""
        # Create valid path within allowed root
        allowed_root = tmp_path / ".claude" / "projects"
        allowed_root.mkdir(parents=True)

        valid_path = allowed_root / "my-project" / "session.jsonl"

        # Should not raise exception
        validated = clockout_tool._validate_path_containment(valid_path, allowed_root)
        assert validated == valid_path.resolve()

    def test_path_containment_rejects_symlinks_outside_sandbox(self, clockout_tool, tmp_path):
        """Test path containment rejects symlinks pointing outside sandbox"""
        allowed_root = tmp_path / ".claude" / "projects"
        allowed_root.mkdir(parents=True)

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Create symlink from allowed area to outside
        symlink_path = allowed_root / "malicious-link"
        symlink_path.symlink_to(outside_dir)

        with pytest.raises(Exception, match="Path traversal"):
            clockout_tool._validate_path_containment(symlink_path, allowed_root)

    def test_hook_path_outside_sandbox_rejected(self, clockout_tool, tmp_path, monkeypatch):
        """Test hook-provided transcript_path pointing outside sandbox is rejected and falls back"""
        # Create malicious transcript outside allowed area
        malicious_dir = tmp_path / "evil"
        malicious_dir.mkdir()
        malicious_transcript = malicious_dir / "evil.jsonl"

        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "Malicious content"}]},
            }
        ]

        with open(malicious_transcript, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Session data with transcript_path pointing to malicious file
        session_data = {"session_id": "test-session", "transcript_path": str(malicious_transcript)}

        # Mock all fallback methods to fail, forcing the error to surface
        def mock_temporal_beacon(*args, **kwargs):
            raise FileNotFoundError("Temporal beacon failed")

        def mock_metadata_inversion(*args, **kwargs):
            raise FileNotFoundError("Metadata inversion failed")

        def mock_explicit_config(*args, **kwargs):
            raise FileNotFoundError("Explicit config failed")

        def mock_legacy_fallback(*args, **kwargs):
            raise FileNotFoundError("Legacy fallback failed")

        monkeypatch.setattr(clockout_tool, "_find_by_temporal_beacon", mock_temporal_beacon)
        monkeypatch.setattr(clockout_tool, "_find_by_metadata_inversion", mock_metadata_inversion)
        monkeypatch.setattr(clockout_tool, "_find_by_explicit_config", mock_explicit_config)
        monkeypatch.setattr(clockout_tool, "_find_session_jsonl", mock_legacy_fallback)

        # Should raise FileNotFoundError because malicious path was rejected and all fallbacks failed
        # This proves the security check is working - malicious path is NOT used
        with pytest.raises(FileNotFoundError):
            result = clockout_tool._resolve_transcript_path(session_data, tmp_path)
            # If we get here without error, malicious path was used - that's a security failure
            if result == malicious_transcript:
                pytest.fail("SECURITY FAILURE: Malicious path was used despite being outside sandbox")

    def test_explicit_config_with_custom_root_works(self, clockout_tool, tmp_path, monkeypatch):
        """Test CLAUDE_TRANSCRIPT_DIR escape hatch works with custom root outside default"""
        # Create custom transcript directory OUTSIDE ~/.claude/projects
        custom_dir = tmp_path / "custom-transcripts"
        custom_dir.mkdir()

        session_id = "custom-root-session"
        jsonl_path = custom_dir / "custom-session.jsonl"

        jsonl_content = [
            {"type": "session_start", "session_id": session_id},
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "Custom location test"}]},
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Set environment variable to custom location
        monkeypatch.setenv("CLAUDE_TRANSCRIPT_DIR", str(custom_dir))

        # Should find the file successfully
        found_path = clockout_tool._find_by_explicit_config(session_id)

        assert found_path == jsonl_path
        assert found_path.exists()

    def test_hook_path_respects_custom_transcript_dir(self, clockout_tool, tmp_path, monkeypatch):
        """Test that hook-provided paths are accepted when within CLAUDE_TRANSCRIPT_DIR custom root"""
        # Create a custom transcript directory outside ~/.claude/projects
        custom_dir = tmp_path / "custom_transcripts"
        custom_dir.mkdir(parents=True)

        # Create a transcript file in the custom location
        jsonl_path = custom_dir / "my-session.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "Test"}]},
            },
        ]
        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Set CLAUDE_TRANSCRIPT_DIR to custom location
        monkeypatch.setenv("CLAUDE_TRANSCRIPT_DIR", str(custom_dir))

        # Session data with hook-provided path pointing to custom location
        session_data = {
            "session_id": "test-hook-custom",
            "transcript_path": str(jsonl_path),
        }

        # Should accept the hook path since it's within the custom root
        result = clockout_tool._resolve_transcript_path(session_data, tmp_path)

        assert result == jsonl_path


class TestContentFormatHandling:
    """Test suite for handling different Claude JSONL content formats"""

    def test_parse_messages_with_string_content_format(self, clockout_tool, tmp_path):
        """Test parsing messages with string content format (not list)"""
        # Create JSONL with string content format
        jsonl_path = tmp_path / "string-format.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": "Hello, this is a string"},
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": "I understand the request"},
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Parse messages
        messages = clockout_tool._parse_session_transcript(jsonl_path)

        # Should successfully parse string content
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, this is a string"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "I understand the request"

    def test_parse_messages_with_mixed_content_formats(self, clockout_tool, tmp_path):
        """Test parsing messages with mixed string and list content formats"""
        jsonl_path = tmp_path / "mixed-format.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": "String format message"},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "List format response"}],
                },
            },
            {
                "type": "user",
                "message": {"role": "user", "content": "Another string"},
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Parse messages
        messages = clockout_tool._parse_session_transcript(jsonl_path)

        # Should handle both formats
        assert len(messages) == 3
        assert messages[0]["content"] == "String format message"
        assert messages[1]["content"] == "List format response"
        assert messages[2]["content"] == "Another string"

    def test_parse_messages_with_empty_string_content(self, clockout_tool, tmp_path):
        """Test parsing messages with empty string content does not crash"""
        jsonl_path = tmp_path / "empty-string.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": ""},
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": "Valid response"},
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Parse messages - should not crash
        messages = clockout_tool._parse_session_transcript(jsonl_path)

        # Empty string should be filtered out (if text:)
        # Only valid response should remain
        assert len(messages) == 1
        assert messages[0]["content"] == "Valid response"

    def test_parse_messages_ignores_non_text_content_blocks(self, clockout_tool, tmp_path):
        """Test parsing messages ignores non-text content blocks in list format"""
        jsonl_path = tmp_path / "non-text-blocks.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": "data:image/png;base64,abc123"},
                        {"type": "text", "text": "What's in this image?"},
                    ],
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "I see a diagram"},
                        {"type": "tool_use", "id": "tool_1", "name": "analyze"},
                    ],
                },
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Parse messages
        messages = clockout_tool._parse_session_transcript(jsonl_path)

        # Should only extract text content, ignore image and tool_use
        assert len(messages) == 2
        assert messages[0]["content"] == "What's in this image?"
        assert messages[1]["content"] == "I see a diagram"

    def test_parse_messages_with_null_text_value(self, clockout_tool, tmp_path):
        """Test parsing handles null text value without TypeError"""
        jsonl_path = tmp_path / "null-text.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": None}]},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Valid response"}],
                },
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Should not raise TypeError, should skip null and keep valid
        messages = clockout_tool._parse_session_transcript(jsonl_path)

        # Null text should be coerced to empty string and filtered out (if text:)
        # Only valid response should remain
        assert len(messages) == 1
        assert messages[0]["content"] == "Valid response"
