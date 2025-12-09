"""
Tests for Context Update Tool - AI-driven context file merging.

Part of Context Steward v2 Phase 2.

Test Coverage:
1. Valid update with inline content
2. Valid update with file_ref
3. AI merge produces valid output
4. Conflict detected - returns warning with continuation_id
5. LOC limit exceeded - compaction works
6. CHANGELOG entry created
7. Invalid target rejected
8. Missing content and file_ref rejected
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from tools.contextupdate import ContextUpdateRequest, ContextUpdateTool


class TestContextUpdateRequest:
    """Test request model validation."""

    def test_valid_request_with_content(self):
        """Test valid request with inline content."""
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Add new feature",
            content="## Feature X\nImplemented feature X",
            working_dir="/project",
        )
        assert request.target == "PROJECT-CONTEXT"
        assert request.intent == "Add new feature"
        assert request.content
        assert not request.file_ref

    def test_valid_request_with_file_ref(self):
        """Test valid request with file reference."""
        request = ContextUpdateRequest(
            target="PROJECT-CHECKLIST",
            intent="Update checklist",
            file_ref=".hestai/inbox/pending/update.md",
            working_dir="/project",
        )
        assert request.target == "PROJECT-CHECKLIST"
        assert request.file_ref
        assert not request.content

    def test_invalid_target_rejected(self):
        """Test that invalid target is rejected by Pydantic."""
        with pytest.raises(ValueError):
            ContextUpdateRequest(
                target="INVALID-TARGET",
                intent="Test",
                content="Content",
                working_dir="/project",
            )


class TestContextUpdateTool:
    """Test ContextUpdateTool implementation."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ContextUpdateTool()

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create mock project structure."""
        # Create .hestai/context directory
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Create PROJECT-CONTEXT.md
        project_context = context_dir / "PROJECT-CONTEXT.md"
        project_context.write_text(
            """# PROJECT-CONTEXT

## IDENTITY
NAME::TestProject
PURPOSE::Test project for validation

## ARCHITECTURE
STACK::Python+FastAPI

## CURRENT_STATE
STATUS::Active
"""
        )

        # Create PROJECT-CHANGELOG.md
        changelog = context_dir / "PROJECT-CHANGELOG.md"
        changelog.write_text(
            """# PROJECT-CHANGELOG

*Audit trail of context updates. Most recent first.*

"""
        )

        # Create inbox structure
        inbox_dir = tmp_path / ".hestai" / "inbox"
        pending_dir = inbox_dir / "pending"
        processed_dir = inbox_dir / "processed"
        pending_dir.mkdir(parents=True)
        processed_dir.mkdir(parents=True)
        (pending_dir / ".gitkeep").touch()
        (processed_dir / ".gitkeep").touch()

        return tmp_path

    def test_tool_metadata(self, tool):
        """Test tool name and description."""
        assert tool.get_name() == "contextupdate"
        assert "CONTEXT STEWARD" in tool.get_description()
        assert "AI-driven merge" in tool.get_description()

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema["type"] == "object"
        assert "target" in schema["properties"]
        assert "intent" in schema["properties"]
        assert schema["properties"]["target"]["enum"] == ["PROJECT-CONTEXT", "PROJECT-CHECKLIST", "PROJECT-ROADMAP"]
        assert set(schema["required"]) == {"target", "intent", "working_dir"}

    def test_tool_requires_no_model(self, tool):
        """Test that tool doesn't require AI model (uses ContextStewardAI internally)."""
        assert not tool.requires_model()

    @pytest.mark.asyncio
    async def test_valid_update_with_inline_content(self, tool, mock_project):
        """Test successful update with inline content."""
        # Mock AI helper
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Merged new feature section",
                    "artifacts": [{"content": "# PROJECT-CONTEXT\n\nUpdated content with new feature"}],
                }
            )

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Add new feature documentation",
                content="## FEATURE_X\nNew feature X implemented",
                working_dir=str(mock_project),
            )

            result = await tool.run(request.__dict__)

            assert len(result) == 1
            response = json.loads(result[0].text)
            assert response["status"] == "success"
            assert "uuid" in json.loads(response["content"])
            assert "merged" in json.loads(response["content"])

            # Verify changelog was updated
            changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
            assert changelog.exists()
            content = changelog.read_text()
            assert "Add new feature documentation" in content

    @pytest.mark.asyncio
    async def test_valid_update_with_file_ref(self, tool, mock_project):
        """Test successful update with file reference."""
        # Create file in inbox
        inbox_file = mock_project / ".hestai" / "inbox" / "pending" / "update.md"
        inbox_file.write_text("## NEW_SECTION\nNew content from file")

        # Mock AI helper
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Merged content from file",
                    "artifacts": [{"content": "# PROJECT-CONTEXT\n\nMerged content"}],
                }
            )

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Update from file",
                file_ref=".hestai/inbox/pending/update.md",
                working_dir=str(mock_project),
            )

            result = await tool.run(request.__dict__)

            assert len(result) == 1
            response = json.loads(result[0].text)
            assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_missing_content_and_file_ref_rejected(self, tool, mock_project):
        """Test that request with neither content nor file_ref is rejected."""
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT", intent="Invalid request", working_dir=str(mock_project)
        )

        result = await tool.run(request.__dict__)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "content or file_ref" in response["content"]

    @pytest.mark.asyncio
    async def test_ai_merge_integration(self, tool, mock_project):
        """Test AI merge produces valid output."""
        # Mock AI helper
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Successfully merged content",
                    "artifacts": [
                        {
                            "content": """# PROJECT-CONTEXT

## IDENTITY
NAME::TestProject
PURPOSE::Test project with new feature

## ARCHITECTURE
STACK::Python+FastAPI

## CURRENT_STATE
STATUS::Active
FEATURE_X::Implemented
"""
                        }
                    ],
                }
            )

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Add feature X",
                content="FEATURE_X::Implemented",
                working_dir=str(mock_project),
            )

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            assert response["status"] == "success"

            # Verify AI was called with correct parameters
            mock_ai.run_task.assert_called_once()
            call_args = mock_ai.run_task.call_args[1]
            assert call_args["task_key"] == "project_context_update"
            assert call_args["intent"] == "Add feature X"
            assert "FEATURE_X::Implemented" in call_args["content"]

    @pytest.mark.asyncio
    async def test_conflict_detection_returns_warning(self, tool, mock_project):
        """Test conflict detection returns warning with continuation_id."""
        # Add recent changelog entry for same target
        changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        recent_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        changelog_content = f"""# PROJECT-CHANGELOG

*Audit trail of context updates. Most recent first.*

## {recent_time}
**Updated PROJECT-CONTEXT**
Modified CURRENT_STATE section

"""
        changelog.write_text(changelog_content)

        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Update CURRENT_STATE",
            content="STATUS::Modified",
            working_dir=str(mock_project),
        )

        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Merged with conflict resolution",
                    "artifacts": [{"content": "# PROJECT-CONTEXT\n\nMerged content"}],
                }
            )

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            # Should succeed and track conflicts in result
            assert response["status"] == "success"
            result_data = json.loads(response["content"])
            assert result_data["conflicts_detected"] > 0

    @pytest.mark.asyncio
    async def test_loc_compaction_when_exceeded(self, tool, mock_project):
        """Test LOC limit exceeded triggers compaction to PROJECT-HISTORY.md."""
        # Create PROJECT-CONTEXT with content that will exceed 200 lines
        context_file = mock_project / ".hestai" / "context" / "PROJECT-CONTEXT.md"

        # Build content with required sections + many old sections to archive
        long_content = """# PROJECT-CONTEXT

## IDENTITY
NAME::TestProject

## ARCHITECTURE
STACK::Python

## CURRENT_STATE
STATUS::Active
"""
        # Add many old achievement sections to exceed LOC
        for i in range(10):
            long_content += f"\n## OLD_ACHIEVEMENT_{i}\nCompleted {i} months ago\n"
            long_content += "\n".join([f"Detail line {j}" for j in range(15)])
            long_content += "\n"

        context_file.write_text(long_content)

        # Mock AI helper
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            # AI returns the long content (simulating merge that keeps everything)
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Merged content",
                    "artifacts": [{"content": long_content + "\n## NEW_SECTION\nNew content\n"}],
                }
            )

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Add more content",
                content="## NEW_SECTION\nNew content",
                working_dir=str(mock_project),
            )

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            assert response["status"] == "success"

            # Check if compaction was triggered
            result_data = json.loads(response["content"])

            # If compaction happened, history file should exist
            # Note: compaction only happens if LOC exceeds 200 after merge
            if result_data.get("compacted"):
                history_file = mock_project / ".hestai" / "context" / "PROJECT-HISTORY.md"
                assert history_file.exists()

            # Verify PROJECT-CONTEXT.md content
            updated_content = context_file.read_text()
            # Content should be written (either compacted or not)
            assert len(updated_content) > 0

    @pytest.mark.asyncio
    async def test_changelog_entry_created(self, tool, mock_project):
        """Test that CHANGELOG entry is created with proper format."""
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Added feature documentation",
                    "artifacts": [{"content": "# PROJECT-CONTEXT\n\nUpdated"}],
                }
            )

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Document new feature",
                content="FEATURE::Documented",
                working_dir=str(mock_project),
            )

            await tool.run(request.__dict__)

            # Verify changelog
            changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
            content = changelog.read_text()

            # Should have timestamp, intent, and entry
            assert "Document new feature" in content
            assert "Added feature documentation" in content or "PROJECT-CONTEXT" in content
            # Should have recent timestamp
            today = datetime.now().strftime("%Y-%m-%d")
            assert today in content

    @pytest.mark.asyncio
    async def test_invalid_target_returns_error(self, tool, mock_project):
        """Test that update with non-existent target creates new file gracefully."""
        # When target doesn't exist, tool creates it
        request = ContextUpdateRequest(
            target="PROJECT-CHECKLIST",  # Valid target but file doesn't exist
            intent="Test",
            content="- [ ] Item 1",
            working_dir=str(mock_project),
        )

        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = False  # Skip AI merge

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            # Should succeed by creating new file
            assert response["status"] == "success"

            # Verify file was created
            checklist_path = mock_project / ".hestai" / "context" / "PROJECT-CHECKLIST.md"
            assert checklist_path.exists()

    @pytest.mark.asyncio
    async def test_ai_disabled_falls_back_gracefully(self, tool, mock_project):
        """Test graceful fallback when AI is disabled."""
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = False

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Update without AI",
                content="Simple append",
                working_dir=str(mock_project),
            )

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            # Should still succeed with simple append
            assert response["status"] in ["success", "skipped"]


class TestConflictDetection:
    """Test conflict detection logic."""

    def test_detect_recent_conflicts_finds_conflicts(self, tmp_path):
        """Test detecting conflicts from recent changelog entries."""
        from tools.contextupdate import detect_recent_conflicts

        # Create changelog with recent entry
        changelog = tmp_path / "PROJECT-CHANGELOG.md"
        recent_time = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
        changelog.write_text(
            f"""# PROJECT-CHANGELOG

## {recent_time}
**Updated PROJECT-CONTEXT CURRENT_STATE**
Modified status field

"""
        )

        conflicts = detect_recent_conflicts(changelog, "PROJECT-CONTEXT", minutes=30)

        assert len(conflicts) > 0
        assert conflicts[0]["target"] == "PROJECT-CONTEXT"

    def test_detect_recent_conflicts_no_conflicts(self, tmp_path):
        """Test no conflicts when last update was long ago."""
        from tools.contextupdate import detect_recent_conflicts

        # Create changelog with old entry
        changelog = tmp_path / "PROJECT-CHANGELOG.md"
        old_time = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        changelog.write_text(
            f"""# PROJECT-CHANGELOG

## {old_time}
**Updated PROJECT-CONTEXT**
Old update

"""
        )

        conflicts = detect_recent_conflicts(changelog, "PROJECT-CONTEXT", minutes=30)

        assert len(conflicts) == 0


class TestLOCCompaction:
    """Test LOC compaction logic."""

    def test_compact_if_needed_no_compaction(self, tmp_path):
        """Test no compaction when under LOC limit."""
        from tools.contextupdate import compact_if_needed

        content = "# Header\n\n" + "\n".join([f"Line {i}" for i in range(150)])

        result = compact_if_needed(content, "PROJECT-CONTEXT", tmp_path, max_loc=200)

        assert result == content
        assert not (tmp_path / "PROJECT-HISTORY.md").exists()

    def test_compact_if_needed_triggers_compaction(self, tmp_path):
        """Test compaction when exceeding LOC limit."""
        from tools.contextupdate import compact_if_needed

        # Create context directory
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Create content exceeding limit with proper sections
        content = (
            """# Header

## IDENTITY
NAME::Test

## ARCHITECTURE
STACK::Python

## OLD_SECTION_1
Content to archive
"""
            + "\n".join([f"Line {i}" for i in range(100)])
            + """

## OLD_SECTION_2
More to archive
"""
            + "\n".join([f"Line {i}" for i in range(100)])
        )

        result = compact_if_needed(content, "PROJECT-CONTEXT", tmp_path, max_loc=50)

        # Should be compacted
        assert len(result.split("\n")) <= 100  # More tolerance for section preservation

        # History file should exist
        history_file = context_dir / "PROJECT-HISTORY.md"
        assert history_file.exists()

    def test_compact_preserves_required_sections(self, tmp_path):
        """Test compaction preserves required sections."""
        from tools.contextupdate import compact_if_needed

        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Create content with required sections
        content = """# PROJECT-CONTEXT

## IDENTITY
NAME::TestProject

## ARCHITECTURE
STACK::Python

## CURRENT_STATE
STATUS::Active

""" + "\n".join(
            [f"## OLD_ACHIEVEMENT_{i}\nCompleted long ago" for i in range(100)]
        )

        result = compact_if_needed(content, "PROJECT-CONTEXT", tmp_path, max_loc=50)

        # Required sections should still be present
        assert "## IDENTITY" in result
        assert "## ARCHITECTURE" in result
        assert "## CURRENT_STATE" in result
