"""
Test suite for request_doc Context Steward tool.

Tests documentation routing, visibility rules, and format application.
"""

import json
import shutil
from pathlib import Path

import pytest

from tools.requestdoc import RequestDocRequest, RequestDocTool


@pytest.fixture
def temp_hestai_dir(tmp_path):
    """Create a temporary .hestai directory structure"""
    hestai_dir = tmp_path / ".hestai"
    context_dir = hestai_dir / "context"
    sessions_dir = hestai_dir / "sessions"
    workflow_dir = hestai_dir / "workflow"

    # Create directory structure
    context_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)
    workflow_dir.mkdir(parents=True)

    # Create docs directory (for ADRs)
    docs_dir = tmp_path / "docs"
    adr_dir = docs_dir / "adr"
    adr_dir.mkdir(parents=True)

    yield hestai_dir

    # Cleanup
    if hestai_dir.exists():
        shutil.rmtree(hestai_dir)
    if docs_dir.exists():
        shutil.rmtree(docs_dir)


@pytest.fixture
def requestdoc_tool():
    """Create a RequestDocTool instance"""
    return RequestDocTool()


class TestRequestDocTool:
    """Test suite for RequestDocTool"""

    def test_tool_metadata(self, requestdoc_tool):
        """Test tool has correct name and metadata"""
        assert requestdoc_tool.get_name() == "requestdoc"
        assert "documentation" in requestdoc_tool.get_description().lower()
        assert requestdoc_tool.requires_model() is False

    def test_request_validation_success(self):
        """Test request validation with valid input"""
        request = RequestDocRequest(
            type="adr",
            intent="Document decision to use Context Steward pattern",
            scope="specific",
            priority="blocking",
            content="Full ADR content here",
            working_dir="/Volumes/HestAI-Tools/test-project",
        )
        assert request.type == "adr"
        assert request.intent == "Document decision to use Context Steward pattern"
        assert request.scope == "specific"
        assert request.priority == "blocking"
        assert request.content == "Full ADR content here"

    def test_request_validation_default_values(self):
        """Test request uses default values if not provided"""
        request = RequestDocRequest(
            type="context_update", intent="Update project context", working_dir="/Volumes/HestAI"
        )
        assert request.scope == "specific"
        assert request.priority == "end_of_session"
        assert request.content == ""

    def test_request_validation_missing_required_fields(self):
        """Test request validation fails with missing required fields"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RequestDocRequest(intent="test intent")  # missing type and working_dir

    def test_request_validation_invalid_type_enum(self):
        """Test request validation fails with invalid type enum"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RequestDocRequest(type="invalid_type", intent="test", working_dir="/test")

    @pytest.mark.asyncio
    async def test_requestdoc_routes_adr_to_docs(self, requestdoc_tool, temp_hestai_dir):
        """Test request_doc routes ADR to docs/adr/ directory"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "type": "adr",
            "intent": "Document database selection",
            "scope": "specific",
            "priority": "blocking",
            "content": "ADR content here",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await requestdoc_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["status"] in ["created", "queued"]
        assert "docs/adr/" in content["path"]
        assert content["steward"] == "system-steward"
        assert content["format_applied"] == "ADR_template"

    @pytest.mark.asyncio
    async def test_requestdoc_routes_context_to_hestai(self, requestdoc_tool, temp_hestai_dir):
        """Test request_doc routes context updates to .hestai/context/"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "type": "context_update",
            "intent": "Update project dependencies",
            "scope": "specific",
            "priority": "end_of_session",
            "content": "DEPENDENCIES::[...]",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await requestdoc_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["status"] in ["created", "queued"]
        assert ".hestai/context/" in content["path"]
        assert content["steward"] == "system-steward"
        assert content["format_applied"] == "OCTAVE"

    @pytest.mark.asyncio
    async def test_requestdoc_routes_session_note_correctly(self, requestdoc_tool, temp_hestai_dir):
        """Test request_doc routes session notes to .hestai/sessions/"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "type": "session_note",
            "intent": "Document key decisions from session",
            "scope": "from_marker",
            "priority": "end_of_session",
            "content": "",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await requestdoc_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["status"] in ["created", "queued"]
        assert ".hestai/sessions/" in content["path"]
        assert content["steward"] == "system-steward"
        assert content["format_applied"] == "OCTAVE"

    @pytest.mark.asyncio
    async def test_requestdoc_routes_workflow_update_correctly(self, requestdoc_tool, temp_hestai_dir):
        """Test request_doc routes workflow updates to .hestai/workflow/"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "type": "workflow_update",
            "intent": "Document new deployment workflow",
            "scope": "specific",
            "priority": "end_of_session",
            "content": "WORKFLOW::[...]",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await requestdoc_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["status"] in ["created", "queued"]
        assert ".hestai/workflow/" in content["path"]
        assert content["steward"] == "system-steward"
        assert content["format_applied"] == "OCTAVE"

    @pytest.mark.asyncio
    async def test_requestdoc_queues_for_blocking_priority(self, requestdoc_tool, temp_hestai_dir):
        """Test request_doc queues documentation for blocking priority"""
        working_dir = temp_hestai_dir.parent

        arguments = {
            "type": "adr",
            "intent": "Critical architectural decision",
            "scope": "specific",
            "priority": "blocking",
            "content": "ADR content",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await requestdoc_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        # Blocking priority should create immediately
        assert content["status"] == "created"

    @pytest.mark.asyncio
    async def test_requestdoc_creates_directory_if_missing(self, requestdoc_tool, tmp_path):
        """Test request_doc creates directory structure if missing"""
        working_dir = tmp_path / "new-project"
        working_dir.mkdir()

        arguments = {
            "type": "context_update",
            "intent": "Initialize project context",
            "scope": "specific",
            "priority": "blocking",
            "content": "PROJECT::[...]",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await requestdoc_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Verify .hestai/context directory was created
        context_dir = working_dir / ".hestai" / "context"
        assert context_dir.exists()
