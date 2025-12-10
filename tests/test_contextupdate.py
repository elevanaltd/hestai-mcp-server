"""
Test suite for context_update tool.

Tests AI-driven merge into context files.
"""

import json

import pytest

from tools.contextupdate import ContextUpdateRequest, ContextUpdateTool, validate_ai_response_compaction


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory structure"""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create .hestai/context structure
    context_dir = project_root / ".hestai" / "context"
    context_dir.mkdir(parents=True)

    return project_root


@pytest.fixture
def contextupdate_tool():
    """Create a ContextUpdateTool instance"""
    return ContextUpdateTool()


class TestContextUpdateTool:
    """Test suite for ContextUpdateTool"""

    def test_tool_metadata(self, contextupdate_tool):
        """Test tool has correct name and metadata"""
        assert contextupdate_tool.get_name() == "contextupdate"
        assert "context" in contextupdate_tool.get_description().lower()
        assert contextupdate_tool.requires_model() is False

    def test_request_validation_success(self):
        """Test request validation with valid input"""
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT", intent="Update architecture section", content="New content", working_dir="/tmp"
        )
        assert request.target == "PROJECT-CONTEXT"
        assert request.intent == "Update architecture section"
        assert request.content == "New content"

    def test_request_validation_missing_required_fields(self):
        """Test request validation fails with missing required fields"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ContextUpdateRequest(target="PROJECT-CONTEXT")  # missing intent and working_dir


class TestArtifactTypeSelection:
    """Test suite for Issue 1: Artifact type selection (CRS code review issue)"""

    @pytest.mark.asyncio
    async def test_artifact_selection_by_type_not_order(self, contextupdate_tool, temp_project_dir, monkeypatch):
        """
        Test that AI response artifacts are selected by type, not order.

        REGRESSION TEST: If AI returns history_archive first, then context_update,
        we must select context_update artifact, not artifacts[0].

        This prevents writing archived content to PROJECT-CONTEXT.md.
        """
        # Create existing PROJECT-CONTEXT.md
        context_file = temp_project_dir / ".hestai" / "context" / "PROJECT-CONTEXT.md"
        context_file.write_text("# PROJECT-CONTEXT\n\nExisting content")

        # Mock AI to return artifacts in WRONG order (history_archive first)
        class MockContextStewardAI:
            def is_task_enabled(self, task_name):
                return True

            async def run_task(self, task_key, **kwargs):
                # Create content > MIN_CONTENT_LENGTH (500 chars) to pass defensive check
                long_context_content = """# PROJECT-CONTEXT

## IDENTITY
Project: Test Project
Type: Integration Test

## ARCHITECTURE
Components:
- Component A: Main application
- Component B: Testing framework
- Component C: Integration layer

## CURRENT_STATE
Phase: B2 Implementation
Status: In Progress
Last Updated: 2025-12-10

## TECHNICAL_STACK
- Language: Python
- Framework: FastAPI
- Testing: Pytest
- Database: PostgreSQL

## ACHIEVEMENTS
- Completed Phase 1
- Implemented core features
- Established testing infrastructure

New compacted content that should go to PROJECT-CONTEXT.md
"""
                long_history_content = "Old archived content that should go to PROJECT-HISTORY.md"

                return {
                    "status": "success",
                    "compaction_performed": True,
                    "artifacts": [
                        {
                            "type": "history_archive",
                            "content": long_history_content,
                        },
                        {
                            "type": "context_update",
                            "content": long_context_content,
                        },
                    ],
                }

        monkeypatch.setattr("tools.contextupdate.ContextStewardAI", MockContextStewardAI)

        arguments = {
            "target": "PROJECT-CONTEXT",
            "intent": "Test artifact selection",
            "content": "Some new content",
            "working_dir": str(temp_project_dir),
        }

        await contextupdate_tool.execute(arguments)

        # Verify the CORRECT content was written (context_update, not history_archive)
        updated_content = context_file.read_text()

        # CURRENTLY FAILS: Code writes history_archive content (artifacts[0])
        # EXPECTED: Code should write context_update content
        assert "New compacted content that should go to PROJECT-CONTEXT.md" in updated_content
        assert "Old archived content" not in updated_content

    @pytest.mark.asyncio
    async def test_artifact_selection_raises_if_missing_type(self, contextupdate_tool, temp_project_dir, monkeypatch):
        """Test that missing context_update artifact raises clear error"""
        # Create existing PROJECT-CONTEXT.md
        context_file = temp_project_dir / ".hestai" / "context" / "PROJECT-CONTEXT.md"
        context_file.write_text("# PROJECT-CONTEXT\n\nExisting content")

        # Mock AI to return only history_archive (missing context_update)
        class MockContextStewardAI:
            def is_task_enabled(self, task_name):
                return True

            async def run_task(self, task_key, **kwargs):
                return {
                    "status": "success",
                    "compaction_performed": True,
                    "artifacts": [
                        {
                            "type": "history_archive",
                            "content": "Only history, no context_update",
                        }
                    ],
                }

        monkeypatch.setattr("tools.contextupdate.ContextStewardAI", MockContextStewardAI)

        arguments = {
            "target": "PROJECT-CONTEXT",
            "intent": "Test missing artifact type",
            "content": "Some new content",
            "working_dir": str(temp_project_dir),
        }

        # Should raise ValueError due to missing context_update artifact
        result = await contextupdate_tool.execute(arguments)
        result_text = result[0].text
        output = json.loads(result_text)

        # After fix, this should be an error response
        # Currently might succeed with wrong content or raise during execution
        assert output["status"] == "error" or "missing" in output.get("content", "").lower()


class TestCompactionEnforcementGate:
    """Test suite for COMPACTION_ENFORCEMENT gate validation"""

    def test_validate_compaction_no_compaction_passes(self):
        """Test validation passes when no compaction performed"""
        ai_response = {
            "status": "success",
            "compaction_performed": False,
            "artifacts": [{"type": "context_update", "content": "Simple update"}],
        }

        # Should pass - no compaction means no history_archive required
        result = validate_ai_response_compaction(ai_response)
        assert result is True

    def test_validate_compaction_with_both_artifacts_passes(self):
        """Test validation passes when compaction includes both artifacts"""
        ai_response = {
            "status": "success",
            "compaction_performed": True,
            "artifacts": [
                {"type": "history_archive", "content": "Archived content"},
                {"type": "context_update", "content": "Compacted content"},
            ],
        }

        # Should pass - both required artifacts present
        result = validate_ai_response_compaction(ai_response)
        assert result is True

    def test_validate_compaction_missing_history_archive_fails(self):
        """Test validation fails when compaction performed but history_archive missing"""
        ai_response = {
            "status": "success",
            "compaction_performed": True,
            "artifacts": [{"type": "context_update", "content": "Only context update"}],
        }

        # Should fail - compaction performed but history_archive missing
        with pytest.raises(ValueError, match="COMPACTION_ENFORCEMENT gate failure.*history_archive artifact missing"):
            validate_ai_response_compaction(ai_response)

    def test_validate_compaction_missing_context_update_fails(self):
        """Test validation fails when compaction performed but context_update missing"""
        ai_response = {
            "status": "success",
            "compaction_performed": True,
            "artifacts": [{"type": "history_archive", "content": "Only history"}],
        }

        # Should fail - compaction performed but context_update missing
        with pytest.raises(ValueError, match="COMPACTION_ENFORCEMENT gate failure.*context_update artifact missing"):
            validate_ai_response_compaction(ai_response)
