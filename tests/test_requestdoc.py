"""
Test suite for request_doc Context Steward tool.

Tests documentation routing, visibility rules, and format application.
"""

import json
import shutil

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


class TestRequestDocPR77Fixes:
    """Test suite for PR #77 P1 fixes - variable mapping, file write, content field"""

    @pytest.mark.asyncio
    async def test_workflow_update_uses_existing_checklist_key(self, requestdoc_tool, monkeypatch):
        """
        Test Issue 1: workflow_update should use 'existing_checklist' key not 'existing_context'

        When AI is enabled and type is workflow_update, the ai_context dict should contain
        'existing_checklist' to match the template placeholder {{existing_checklist}}.
        """
        # Track what context was passed to AI
        captured_context = {}

        async def mock_run_task(self, task_key, **kwargs):
            captured_context.update(kwargs)
            return {"status": "failure", "error": "mock"}

        # Mock AI helper to capture context
        mock_ai = type("obj", (object,), {"is_task_enabled": lambda self, task: True, "run_task": mock_run_task})()

        # Replace AI helper
        requestdoc_tool._ai_helper = mock_ai

        arguments = {
            "type": "workflow_update",
            "intent": "Test checklist update",
            "scope": "specific",
            "priority": "end_of_session",
            "content": "Test content",
            "working_dir": "/tmp/test",
            "_session_context": type("obj", (object,), {"project_root": "/tmp/test"})(),
        }

        await requestdoc_tool.execute(arguments)

        # Verify 'existing_checklist' key exists (not 'existing_context')
        assert "existing_checklist" in captured_context, "workflow_update should use 'existing_checklist' key"
        assert "existing_context" not in captured_context, "workflow_update should NOT use 'existing_context' key"

    @pytest.mark.asyncio
    async def test_context_update_uses_existing_context_key(self, requestdoc_tool, monkeypatch):
        """
        Test Issue 1: context_update should use 'existing_context' key

        When AI is enabled and type is context_update, the ai_context dict should contain
        'existing_context' to match the template placeholder {{existing_context}}.
        """
        # Track what context was passed to AI
        captured_context = {}

        async def mock_run_task(self, task_key, **kwargs):
            captured_context.update(kwargs)
            return {"status": "failure", "error": "mock"}

        # Mock AI helper to capture context
        mock_ai = type("obj", (object,), {"is_task_enabled": lambda self, task: True, "run_task": mock_run_task})()

        # Replace AI helper
        requestdoc_tool._ai_helper = mock_ai

        arguments = {
            "type": "context_update",
            "intent": "Test context update",
            "scope": "specific",
            "priority": "end_of_session",
            "content": "Test content",
            "working_dir": "/tmp/test",
            "_session_context": type("obj", (object,), {"project_root": "/tmp/test"})(),
        }

        await requestdoc_tool.execute(arguments)

        # Verify 'existing_context' key exists (not 'existing_checklist')
        assert "existing_context" in captured_context, "context_update should use 'existing_context' key"
        assert "existing_checklist" not in captured_context, "context_update should NOT use 'existing_checklist' key"

    @pytest.mark.asyncio
    async def test_ai_success_writes_artifact_with_content_to_disk(self, requestdoc_tool, tmp_path):
        """
        Test Issue 2: AI success path should actually write files (not just log)

        When AI returns artifacts with 'content' field, those files should be written to disk.
        """
        working_dir = tmp_path / "test-project"
        working_dir.mkdir()

        # Create .hestai/context directory
        context_dir = working_dir / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Mock AI helper that returns success with artifact containing content
        async def mock_run_task(self, task_key, **kwargs):
            return {
                "status": "success",
                "summary": "Updated context",
                "changes": ["Added new section"],
                "artifacts": [
                    {
                        "type": "context_update",
                        "path": ".hestai/context/PROJECT-CONTEXT.md",
                        "action": "merged",
                        "content": "NEW_CONTEXT_CONTENT",
                    }
                ],
            }

        mock_ai = type("obj", (object,), {"is_task_enabled": lambda self, task: True, "run_task": mock_run_task})()

        requestdoc_tool._ai_helper = mock_ai

        arguments = {
            "type": "context_update",
            "intent": "Test file write",
            "scope": "specific",
            "priority": "end_of_session",
            "content": "Test content",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        await requestdoc_tool.execute(arguments)

        # Verify file was actually written to disk
        artifact_path = working_dir / ".hestai" / "context" / "PROJECT-CONTEXT.md"
        assert artifact_path.exists(), "AI artifact file should be written to disk"
        assert artifact_path.read_text() == "NEW_CONTEXT_CONTENT", "AI artifact content should match what AI returned"

    @pytest.mark.asyncio
    async def test_ai_success_logs_warning_for_artifact_without_content(self, requestdoc_tool, tmp_path, caplog):
        """
        Test Issue 2: AI artifacts without 'content' field should log warning (not error)

        When AI returns artifacts without 'content' field, should log warning and continue.
        """
        import logging

        caplog.set_level(logging.WARNING)

        working_dir = tmp_path / "test-project"
        working_dir.mkdir()

        # Create .hestai/context directory
        context_dir = working_dir / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Mock AI helper that returns success with artifact missing content field
        async def mock_run_task(self, task_key, **kwargs):
            return {
                "status": "success",
                "summary": "Updated context",
                "changes": ["Added new section"],
                "artifacts": [
                    {
                        "type": "context_update",
                        "path": ".hestai/context/PROJECT-CONTEXT.md",
                        "action": "merged",
                        # Missing 'content' field
                    }
                ],
            }

        mock_ai = type("obj", (object,), {"is_task_enabled": lambda self, task: True, "run_task": mock_run_task})()

        requestdoc_tool._ai_helper = mock_ai

        arguments = {
            "type": "context_update",
            "intent": "Test missing content",
            "scope": "specific",
            "priority": "end_of_session",
            "content": "Test content",
            "working_dir": str(working_dir),
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        await requestdoc_tool.execute(arguments)

        # Verify warning was logged
        assert any(
            "missing content" in record.message.lower() for record in caplog.records
        ), "Should log warning when artifact is missing content field"

        # Verify file was NOT created
        artifact_path = working_dir / ".hestai" / "context" / "PROJECT-CONTEXT.md"
        assert not artifact_path.exists(), "File should not be created when artifact is missing content field"
