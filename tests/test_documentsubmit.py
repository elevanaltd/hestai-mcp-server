"""
Tests for document_submit tool - Context Steward v2 Shell layer.

Tests the 6-step document submission flow:
1. ACCEPT: Validate request, write to inbox
2. CLASSIFY: Determine destination from DOCUMENT_TYPES
3. PROCESS: OCTAVE compress if needed
4. PLACE: Write to destination directory
5. ARCHIVE: Move to processed/
6. NOTIFY: Update index.json, return result
"""

import json

import pytest

from tools.documentsubmit import DocumentSubmitRequest, DocumentSubmitTool
from tools.models import ToolOutput


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def tool():
    """Create document_submit tool instance."""
    return DocumentSubmitTool()


class TestDocumentSubmitRequest:
    """Test DocumentSubmitRequest model validation."""

    def test_valid_adr_request(self):
        """Test valid ADR document submission request."""
        request = DocumentSubmitRequest(
            type="adr",
            intent="Add user authentication",
            content="# ADR: User Authentication\n\nContext...",
            working_dir="/tmp/project",
        )
        assert request.type == "adr"
        assert request.intent == "Add user authentication"
        assert request.priority == "normal"
        assert request.content != ""

    def test_valid_session_note_request(self):
        """Test valid session note submission request."""
        request = DocumentSubmitRequest(
            type="session_note",
            intent="Sprint planning session",
            content="NOTES::[sprint_planning]",
            working_dir="/tmp/project",
        )
        assert request.type == "session_note"
        assert request.intent == "Sprint planning session"

    def test_valid_workflow_request(self):
        """Test valid workflow document submission request."""
        request = DocumentSubmitRequest(
            type="workflow",
            intent="Update deployment process",
            file_ref=".hestai/inbox/pending/12345.json",
            working_dir="/tmp/project",
        )
        assert request.type == "workflow"
        assert request.file_ref != ""

    def test_valid_config_request(self):
        """Test valid config document submission request."""
        request = DocumentSubmitRequest(
            type="config",
            intent="Update Claude settings",
            content="{}",
            working_dir="/tmp/project",
        )
        assert request.type == "config"

    def test_invalid_document_type(self):
        """Test invalid document type raises error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DocumentSubmitRequest(
                type="invalid_type",
                intent="Test",
                working_dir="/tmp/project",
            )

    def test_missing_required_fields(self):
        """Test missing required fields raises error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DocumentSubmitRequest(intent="Test")


class TestDocumentSubmitTool:
    """Test DocumentSubmitTool functionality."""

    def test_tool_metadata(self, tool):
        """Test tool name and description."""
        assert tool.get_name() == "documentsubmit"
        assert "CONTEXT STEWARD" in tool.get_description()
        assert "Submit documents" in tool.get_description()

    def test_input_schema(self, tool):
        """Test input schema generation."""
        schema = tool.get_input_schema()
        assert schema["type"] == "object"
        assert "type" in schema["properties"]
        assert "intent" in schema["properties"]
        assert "content" in schema["properties"]
        assert "file_ref" in schema["properties"]
        assert "working_dir" in schema["required"]

    def test_model_category(self, tool):
        """Test tool returns FAST_RESPONSE category."""
        from tools.models import ToolModelCategory

        assert tool.get_model_category() == ToolModelCategory.FAST_RESPONSE

    def test_requires_model(self, tool):
        """Test tool does not require AI model."""
        assert tool.requires_model() is False


class TestDocumentSubmitFlow:
    """Test the 6-step document submission flow."""

    @pytest.mark.asyncio
    async def test_submit_adr_with_inline_content(self, tool, temp_project):
        """Test submitting ADR with inline content."""
        # Arrange
        arguments = {
            "type": "adr",
            "intent": "Add user authentication",
            "content": "# ADR: User Authentication\n\nContext: Need secure login.",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"

        result_data = json.loads(output.content)
        assert result_data["status"] == "success"
        assert "uuid" in result_data
        assert "docs/adr/" in result_data["destination"]
        assert result_data["format"] == "ADR_template"
        assert "archived" in result_data

        # Verify destination file exists
        dest_path = temp_project / result_data["destination"]
        assert dest_path.exists()
        assert "User Authentication" in dest_path.read_text()

        # Verify inbox processed
        uuid = result_data["uuid"]
        processed_file = temp_project / ".hestai" / "inbox" / "processed" / f"{uuid}.json"
        assert processed_file.exists()

        # Verify index updated
        index_file = temp_project / ".hestai" / "inbox" / "processed" / "index.json"
        assert index_file.exists()
        index_data = json.loads(index_file.read_text())
        assert len(index_data["processed_items"]) == 1
        assert index_data["processed_items"][0]["uuid"] == uuid

    @pytest.mark.asyncio
    async def test_submit_session_note_with_file_ref(self, tool, temp_project):
        """Test submitting session note with file reference."""
        # Arrange - create a file in inbox
        inbox_path = temp_project / ".hestai" / "inbox" / "pending"
        inbox_path.mkdir(parents=True, exist_ok=True)
        test_file = inbox_path / "test-note.txt"
        test_file.write_text("SESSION_NOTES::[planning_session]")

        arguments = {
            "type": "session_note",
            "intent": "Sprint planning session",
            "file_ref": str(test_file),
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"

        result_data = json.loads(output.content)
        assert ".hestai/sessions/notes/" in result_data["destination"]
        assert result_data["format"] == "OCTAVE"

    @pytest.mark.asyncio
    async def test_submit_workflow_document(self, tool, temp_project):
        """Test submitting workflow document."""
        # Arrange
        arguments = {
            "type": "workflow",
            "intent": "Update deployment process",
            "content": "WORKFLOW::[deploy→test→release]",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"

        result_data = json.loads(output.content)
        assert ".hestai/workflow/" in result_data["destination"]
        assert result_data["format"] == "OCTAVE"

    @pytest.mark.asyncio
    async def test_submit_config_document(self, tool, temp_project):
        """Test submitting config document."""
        # Arrange
        arguments = {
            "type": "config",
            "intent": "Update Claude settings",
            "content": '{"temperature": 0.7}',
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"

        result_data = json.loads(output.content)
        assert ".claude/" in result_data["destination"]
        assert result_data["format"] == "preserve"

    @pytest.mark.asyncio
    async def test_invalid_document_type(self, tool, temp_project):
        """Test error on invalid document type."""
        # Arrange
        arguments = {
            "type": "invalid_type",
            "intent": "Test",
            "content": "Content",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "error"
        assert "type" in output.content.lower()

    @pytest.mark.asyncio
    async def test_missing_content_and_file_ref(self, tool, temp_project):
        """Test error when both content and file_ref are missing."""
        # Arrange
        arguments = {
            "type": "adr",
            "intent": "Test",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "error"
        assert "content" in output.content.lower() or "file_ref" in output.content.lower()

    @pytest.mark.asyncio
    async def test_changelog_entry_created(self, tool, temp_project):
        """Test that changelog entry is created."""
        # Arrange
        arguments = {
            "type": "adr",
            "intent": "Add user authentication",
            "content": "# ADR Content",
            "working_dir": str(temp_project),
        }

        # Act
        await tool.run(arguments)

        # Assert
        changelog_path = temp_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        assert changelog_path.exists()
        changelog_content = changelog_path.read_text()
        assert "Add user authentication" in changelog_content
        assert "Document submitted" in changelog_content

    @pytest.mark.asyncio
    async def test_continuation_id_support(self, tool, temp_project):
        """Test continuation_id is tracked in submission."""
        # Arrange
        arguments = {
            "type": "session_note",
            "intent": "Test session",
            "content": "Session notes",
            "continuation_id": "test-session-123",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"

        result_data = json.loads(output.content)
        uuid = result_data["uuid"]

        # Check inbox item has session_id
        processed_file = temp_project / ".hestai" / "inbox" / "processed" / f"{uuid}.json"
        processed_data = json.loads(processed_file.read_text())
        assert processed_data["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_priority_normal_default(self, tool, temp_project):
        """Test normal priority is default."""
        # Arrange
        arguments = {
            "type": "adr",
            "intent": "Test",
            "content": "Content",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_blocking_priority(self, tool, temp_project):
        """Test blocking priority processing."""
        # Arrange
        arguments = {
            "type": "adr",
            "intent": "Urgent decision",
            "content": "Content",
            "priority": "blocking",
            "working_dir": str(temp_project),
        }

        # Act
        result = await tool.run(arguments)

        # Assert
        assert len(result) == 1
        output = ToolOutput.model_validate_json(result[0].text)
        assert output.status == "success"
        # Should process immediately regardless of priority
        # (actual priority handling will be implemented later)
