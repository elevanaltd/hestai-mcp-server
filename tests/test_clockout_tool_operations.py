"""
Test suite for tool operation extraction in clockout pipeline.

Tests that tool_use and tool_result entries are preserved in session archives,
addressing Issue #120 - 98.6% content loss due to filtering.
"""

import json
import shutil
from pathlib import Path

import pytest

from tools.clockout import ClockOutTool


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

    # Create active session - use unique session_id for testing
    session_id = "test-tool-ops-00000000-0000-0000-0000-000000000002"
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
    shutil.rmtree(hestai_dir, ignore_errors=True)


@pytest.fixture
def temp_jsonl_with_tools(tmp_path):
    """Create a JSONL file with tool operations"""
    jsonl_path = tmp_path / "session-with-tools.jsonl"

    # Realistic session with tool operations
    jsonl_content = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Read the clockout.py file"}],
            },
        },
        {
            "type": "tool_use",
            "id": "toolu_01ABC123",
            "name": "Read",
            "input": {"file_path": "/Volumes/HestAI-Tools/hestai-mcp-server/tools/clockout.py"},
        },
        {
            "type": "tool_result",
            "tool_use_id": "toolu_01ABC123",
            "content": [
                {
                    "type": "text",
                    "text": "File contents: def execute()...",
                }
            ],
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I've read the clockout.py file. Here's what I found..."}],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Now run the tests"}],
            },
        },
        {
            "type": "tool_use",
            "id": "toolu_02DEF456",
            "name": "Bash",
            "input": {"command": "python -m pytest tests/test_clockout.py -v"},
        },
        {
            "type": "tool_result",
            "tool_use_id": "toolu_02DEF456",
            "content": [
                {
                    "type": "text",
                    "text": "===== test session starts =====\ncollected 15 items\ntests/test_clockout.py::test_parse PASSED\n===== 15 passed in 2.3s =====",
                }
            ],
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "All tests passed successfully!"}],
            },
        },
    ]

    with open(jsonl_path, "w") as f:
        for entry in jsonl_content:
            f.write(json.dumps(entry) + "\n")

    return jsonl_path


class TestToolOperationExtraction:
    """Test suite for extracting tool operations from JSONL"""

    def test_parse_session_includes_tool_use_entries(self, temp_jsonl_with_tools):
        """
        Test that _parse_session_transcript() includes tool_use entries.

        CURRENT BEHAVIOR: tool_use entries are skipped (line 625 filter)
        EXPECTED BEHAVIOR: tool_use entries should be extracted with tool name and params
        """
        tool = ClockOutTool()
        messages = tool._parse_session_transcript(temp_jsonl_with_tools)

        # Find tool_use entries
        tool_uses = [msg for msg in messages if msg.get("type") == "tool_use"]

        # RED: Should have 2 tool_use entries (Read and Bash)
        assert len(tool_uses) == 2, f"Expected 2 tool_use entries, got {len(tool_uses)}"

        # Verify first tool_use (Read)
        read_tool = tool_uses[0]
        assert read_tool["name"] == "Read"
        assert "file_path" in read_tool.get("params", {})

        # Verify second tool_use (Bash)
        bash_tool = tool_uses[1]
        assert bash_tool["name"] == "Bash"
        assert "command" in bash_tool.get("params", {})

    def test_parse_session_includes_tool_result_entries(self, temp_jsonl_with_tools):
        """
        Test that _parse_session_transcript() includes tool_result entries.

        CURRENT BEHAVIOR: tool_result entries are skipped
        EXPECTED BEHAVIOR: tool_result entries should be extracted with status and output summary
        """
        tool = ClockOutTool()
        messages = tool._parse_session_transcript(temp_jsonl_with_tools)

        # Find tool_result entries
        tool_results = [msg for msg in messages if msg.get("type") == "tool_result"]

        # RED: Should have 2 tool_result entries
        assert len(tool_results) == 2, f"Expected 2 tool_result entries, got {len(tool_results)}"

        # Verify results include output summary
        assert all("output" in result or "content" in result for result in tool_results)

    def test_parse_session_preserves_user_assistant_messages(self, temp_jsonl_with_tools):
        """
        Test that existing user/assistant message extraction still works.

        This ensures we don't break existing functionality.
        """
        tool = ClockOutTool()
        messages = tool._parse_session_transcript(temp_jsonl_with_tools)

        # Find user/assistant messages
        user_msgs = [msg for msg in messages if msg.get("role") == "user"]
        assistant_msgs = [msg for msg in messages if msg.get("role") == "assistant"]

        # Should have 2 user messages and 2 assistant messages
        assert len(user_msgs) == 2
        assert len(assistant_msgs) == 2

    def test_parse_session_maintains_chronological_order(self, temp_jsonl_with_tools):
        """
        Test that messages maintain chronological order with tool operations interleaved.

        Expected sequence:
        1. user: "Read the clockout.py file"
        2. tool_use: Read
        3. tool_result: Read result
        4. assistant: "I've read the clockout.py file..."
        5. user: "Now run the tests"
        6. tool_use: Bash
        7. tool_result: Bash result
        8. assistant: "All tests passed successfully!"
        """
        tool = ClockOutTool()
        messages = tool._parse_session_transcript(temp_jsonl_with_tools)

        # Should have all 8 entries in order
        assert len(messages) == 8

        # Verify sequence
        assert messages[0]["role"] == "user"
        assert messages[1]["type"] == "tool_use"
        assert messages[2]["type"] == "tool_result"
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "user"
        assert messages[5]["type"] == "tool_use"
        assert messages[6]["type"] == "tool_result"
        assert messages[7]["role"] == "assistant"

    def test_format_transcript_includes_tool_operations(self, temp_jsonl_with_tools):
        """
        Test that _format_transcript() includes tool operations in output.

        CURRENT BEHAVIOR: Tool operations are not formatted
        EXPECTED BEHAVIOR: Tool operations appear as [TOOL: name] with params/results
        """
        tool = ClockOutTool()
        messages = tool._parse_session_transcript(temp_jsonl_with_tools)

        session_data = {
            "session_id": "test-123",
            "role": "implementation-lead",
            "focus": "b2-implementation",
            "started_at": "2025-12-11T10:00:00",
            "working_dir": "/tmp/test",
        }

        formatted = tool._format_transcript(messages, session_data, "Test session")

        # RED: Formatted output should include tool operations
        assert "[TOOL: Read]" in formatted, "Tool use should be marked in transcript"
        assert "[TOOL: Bash]" in formatted, "Bash tool should be marked in transcript"
        assert "[RESULT:" in formatted or "[TOOL_RESULT:" in formatted, "Tool results should be included"

    def test_tool_params_are_summarized_not_dumped(self, tmp_path):
        """
        Test that large tool parameters are summarized, not dumped verbatim.

        Security/Performance: Don't expose sensitive params or huge outputs.
        """
        # Create JSONL with large tool output
        jsonl_path = tmp_path / "large-output.jsonl"
        large_content = "x" * 10000  # 10KB of content

        jsonl_content = [
            {
                "type": "tool_use",
                "id": "toolu_large",
                "name": "Read",
                "input": {"file_path": "/very/long/path/to/file.py"},
            },
            {
                "type": "tool_result",
                "tool_use_id": "toolu_large",
                "content": [{"type": "text", "text": large_content}],
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        tool = ClockOutTool()
        messages = tool._parse_session_transcript(jsonl_path)

        # Tool result should be summarized, not 10KB
        tool_result = next((msg for msg in messages if msg.get("type") == "tool_result"), None)
        assert tool_result is not None

        # Result should be truncated/summarized (< 1KB)
        result_text = str(tool_result.get("output", ""))
        assert len(result_text) < 1000, "Large tool results should be summarized, not dumped verbatim"

    def test_sensitive_params_are_redacted(self, tmp_path):
        """
        Test that sensitive parameters (API keys, passwords) are redacted.

        Security: Don't expose credentials in session archives.
        """
        jsonl_path = tmp_path / "sensitive-params.jsonl"

        jsonl_content = [
            {
                "type": "tool_use",
                "id": "toolu_sensitive",
                "name": "Bash",
                "input": {
                    "command": "curl -H 'Authorization: Bearer sk-abc123xyz789' https://api.example.com",
                    "env": {"API_KEY": "secret-key-12345"},
                },
            },
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        tool = ClockOutTool()
        messages = tool._parse_session_transcript(jsonl_path)

        tool_use = next((msg for msg in messages if msg.get("type") == "tool_use"), None)
        assert tool_use is not None

        # Sensitive data should be redacted
        params_str = str(tool_use.get("params", {}))
        assert "sk-abc123xyz789" not in params_str, "API keys should be redacted"
        assert "secret-key-12345" not in params_str, "Secret keys should be redacted"
        assert "REDACTED" in params_str or "***" in params_str, "Redaction marker should be present"


class TestRawJSONLPreservation:
    """Test suite for raw JSONL preservation in archive"""

    @pytest.mark.asyncio
    async def test_clockout_preserves_raw_jsonl(
        self, temp_hestai_dir, temp_jsonl_with_tools, monkeypatch  # noqa: F811
    ):
        """
        Test that clockout preserves raw JSONL file in archive before parsing.

        CURRENT BEHAVIOR: Raw JSONL is not preserved
        EXPECTED BEHAVIOR: {session_id}-raw.jsonl should exist in archive/
        """

        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Copy temp_jsonl to expected location
        claude_projects = Path.home() / ".claude" / "projects"
        encoded_path = str(working_dir).replace("/", "-").lstrip("-")
        project_dir = claude_projects / encoded_path
        project_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = project_dir / f"{session_id}.jsonl"
        shutil.copy(temp_jsonl_with_tools, jsonl_path)

        # Mock validation
        def mock_validate(path, allowed_root=None):
            return path.resolve() if isinstance(path, Path) else Path(path).resolve()

        tool = ClockOutTool()
        monkeypatch.setattr(tool, "_validate_path_containment", mock_validate)

        # Update session with transcript path
        session_dir = hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())
        session_data["transcript_path"] = str(jsonl_path)
        session_file.write_text(json.dumps(session_data))

        arguments = {
            "session_id": session_id,
            "description": "Test raw JSONL preservation",
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        # Disable AI compression for this test to focus on JSONL preservation
        class MockContextStewardAI:
            def is_task_enabled(self, task_name):
                return False

        monkeypatch.setattr("tools.context_steward.ai.ContextStewardAI", MockContextStewardAI)

        result = await tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # RED: Raw JSONL should be preserved in archive
        archive_dir = hestai_dir / "sessions" / "archive"
        raw_jsonl_path = archive_dir / f"{session_id}-raw.jsonl"
        assert raw_jsonl_path.exists(), "Raw JSONL should be preserved in archive"

        # Verify it's a complete copy
        raw_content = raw_jsonl_path.read_text()
        original_content = temp_jsonl_with_tools.read_text()
        assert raw_content == original_content, "Raw JSONL should be complete copy"

        # Cleanup
        if jsonl_path.exists():
            jsonl_path.unlink()
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)

    def test_raw_jsonl_is_gitignored(self, tmp_path):
        """
        Test that *-raw.jsonl pattern is in .hestai/.gitignore.

        Raw JSONL files can be large (>1MB) and should not be tracked by git.
        """
        # This is a documentation test - verify .gitignore pattern exists
        gitignore_path = Path("/Volumes/HestAI-Tools/hestai-mcp-server/.hestai/.gitignore")

        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            assert (
                "*-raw.jsonl" in gitignore_content
            ), ".gitignore should include *-raw.jsonl pattern for raw session archives"
        else:
            pytest.skip(".hestai/.gitignore not found in this project")
