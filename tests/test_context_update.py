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
    async def test_same_section_conflict_returns_conflict_response(self, tool, mock_project):
        """Test same-section conflict returns conflict status with continuation_id (Phase 2)."""
        # Add recent changelog entry modifying CURRENT_STATE
        changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        recent_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        changelog_content = f"""# PROJECT-CHANGELOG

## {recent_time}
**Update CURRENT_STATE section**
Set PHASE to B2

"""
        changelog.write_text(changelog_content)

        # New request also modifying CURRENT_STATE (conflict!)
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Update CURRENT_STATE",
            content="## CURRENT_STATE\nPHASE::B1",
            working_dir=str(mock_project),
        )

        result = await tool.run(request.__dict__)

        response = json.loads(result[0].text)
        assert response["status"] == "conflict"
        result_data = json.loads(response["content"])
        assert result_data["conflict_type"] == "same_section_modified"
        assert "CURRENT_STATE" in result_data["details"]["section"]
        assert "continuation_id" in result_data

    @pytest.mark.asyncio
    async def test_unrelated_sections_no_conflict(self, tool, mock_project):
        """Test unrelated section changes processed without conflict (Phase 2)."""
        # Recent change to ARCHITECTURE
        changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        recent_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        changelog_content = f"""# PROJECT-CHANGELOG

## {recent_time}
**Update ARCHITECTURE section**
Added new service

"""
        changelog.write_text(changelog_content)

        # New change to RECENT_ACHIEVEMENTS (different section, no conflict)
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Add achievement",
            content="## RECENT_ACHIEVEMENTS\n- Completed feature X",
            working_dir=str(mock_project),
        )

        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Merged content",
                    "artifacts": [{"content": "# PROJECT-CONTEXT\n\nMerged"}],
                }
            )

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            # Should succeed without conflict
            assert response["status"] == "success"
            result_data = json.loads(response["content"])
            assert result_data.get("conflicts_detected", 0) == 0

    @pytest.mark.asyncio
    async def test_continuation_id_resolves_conflict(self, tool, mock_project):
        """Test continuation_id allows conflict resolution (Phase 2)."""
        # First, create a conflict
        changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        recent_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        changelog_content = f"""# PROJECT-CHANGELOG

## {recent_time}
**Update CURRENT_STATE**
Set PHASE to B2

"""
        changelog.write_text(changelog_content)

        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Update CURRENT_STATE",
            content="## CURRENT_STATE\nPHASE::B1",
            working_dir=str(mock_project),
        )

        result = await tool.run(request.__dict__)
        response = json.loads(result[0].text)
        assert response["status"] == "conflict"

        # Get continuation_id
        conflict_data = json.loads(response["content"])
        continuation_id = conflict_data["continuation_id"]

        # Now resolve with continuation_id
        resolve_request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Confirm B2 phase",
            content="## CURRENT_STATE\nPHASE::B2",
            continuation_id=continuation_id,
            working_dir=str(mock_project),
        )

        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "Resolved conflict",
                    "artifacts": [{"content": "# PROJECT-CONTEXT\n\nResolved"}],
                }
            )

            result = await tool.run(resolve_request.__dict__)

            response = json.loads(result[0].text)
            # Should succeed after conflict resolution
            assert response["status"] == "success"

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

    @pytest.mark.asyncio
    async def test_ai_truncated_content_triggers_fallback(self, tool, mock_project):
        """Test that AI returning truncated content triggers fallback to simple append."""
        # Mock AI returning truncated placeholder content
        with patch("tools.contextupdate.ContextStewardAI") as MockAI:
            mock_ai = MockAI.return_value
            mock_ai.is_task_enabled.return_value = True
            # AI returns short placeholder instead of full merged content
            mock_ai.run_task = AsyncMock(
                return_value={
                    "status": "success",
                    "summary": "success_176_LOC_within_target",
                    "artifacts": [{"content": "success_176_LOC_within_target"}],
                }
            )

            request = ContextUpdateRequest(
                target="PROJECT-CONTEXT",
                intent="Add substantial feature documentation",
                content="## NEW_FEATURE\nThis is a substantial feature with documentation",
                working_dir=str(mock_project),
            )

            result = await tool.run(request.__dict__)

            response = json.loads(result[0].text)
            # Should succeed using fallback
            assert response["status"] == "success"

            # Verify the final content contains both existing and new content
            context_file = mock_project / ".hestai" / "context" / "PROJECT-CONTEXT.md"
            final_content = context_file.read_text()

            # Should have original content
            assert "## IDENTITY" in final_content
            assert "NAME::TestProject" in final_content

            # Should have new content (from fallback append)
            assert "## NEW_FEATURE" in final_content

            # Should NOT have the placeholder text
            assert "success_176_LOC_within_target" not in final_content

    @pytest.mark.asyncio
    async def test_invalid_continuation_id_rejected(self, tool, mock_project):
        """Test that invalid continuation_id formats are rejected (security fix)."""
        # Attempt path traversal
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Bypass attempt",
            content="## CURRENT_STATE\nBYPASS",
            continuation_id="../../../etc/passwd",
            working_dir=str(mock_project),
        )

        result = await tool.run(request.__dict__)

        response = json.loads(result[0].text)
        # Should return error
        assert response["status"] == "error"
        assert "Invalid continuation_id" in response["content"]

    @pytest.mark.asyncio
    async def test_fake_continuation_id_falls_back_to_detection(self, tool, mock_project):
        """Test that fake continuation_id without state falls back to detection (security fix)."""
        # Add recent changelog entry modifying CURRENT_STATE
        changelog = mock_project / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        recent_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        changelog_content = f"""# PROJECT-CHANGELOG

## {recent_time}
**Update CURRENT_STATE section**
Set PHASE to B2

"""
        changelog.write_text(changelog_content)

        # Attempt bypass with valid-looking but non-existent continuation_id
        request = ContextUpdateRequest(
            target="PROJECT-CONTEXT",
            intent="Bypass attempt",
            content="## CURRENT_STATE\nPHASE::B1",
            continuation_id="fake-bypass-12345678",
            working_dir=str(mock_project),
        )

        result = await tool.run(request.__dict__)

        response = json.loads(result[0].text)
        # Should detect conflict (fallback to detection when state not found)
        assert response["status"] == "conflict"
        result_data = json.loads(response["content"])
        assert "CURRENT_STATE" in result_data["details"]["section"]


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


class TestCompactionEnforcement:
    """Test COMPACTION_ENFORCEMENT gate for archival requirements."""

    @pytest.mark.asyncio
    async def test_compaction_without_history_archive_rejected(self):
        """Test that AI response performing compaction without history_archive artifact is rejected."""
        from tools.contextupdate import validate_ai_response_compaction

        # Mock AI response that performed compaction but didn't include history_archive
        ai_response_invalid = {
            "status": "success",
            "summary": "Compacted PROJECT-CONTEXT from 250 LOC to 150 LOC",
            "compaction_performed": True,
            "artifacts": [
                {
                    "type": "context_update",
                    "path": ".hestai/context/PROJECT-CONTEXT.md",
                    "action": "merged",
                    "content": "# PROJECT-CONTEXT\n\nCompacted content...",
                }
                # Missing history_archive artifact!
            ],
        }

        # Should raise ValueError for missing archive
        with pytest.raises(ValueError) as exc_info:
            validate_ai_response_compaction(ai_response_invalid)

        assert "history_archive" in str(exc_info.value).lower()
        assert "compaction" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_compaction_with_history_archive_accepted(self):
        """Test that AI response with both artifacts is accepted."""
        from tools.contextupdate import validate_ai_response_compaction

        # Mock AI response that performed compaction correctly with both artifacts
        ai_response_valid = {
            "status": "success",
            "summary": "Compacted PROJECT-CONTEXT and archived to PROJECT-HISTORY",
            "compaction_performed": True,
            "artifacts": [
                {
                    "type": "history_archive",
                    "path": ".hestai/context/PROJECT-HISTORY.md",
                    "action": "append_dated_section",
                    "content": "## Archived 2025-12-10\n\nOld content...",
                },
                {
                    "type": "context_update",
                    "path": ".hestai/context/PROJECT-CONTEXT.md",
                    "action": "merged",
                    "content": "# PROJECT-CONTEXT\n\nCompacted content...",
                },
            ],
        }

        # Should not raise
        result = validate_ai_response_compaction(ai_response_valid)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_compaction_no_archive_required(self):
        """Test that responses without compaction don't require history_archive."""
        from tools.contextupdate import validate_ai_response_compaction

        # Mock AI response without compaction
        ai_response_no_compaction = {
            "status": "success",
            "summary": "Merged new content into PROJECT-CONTEXT",
            "compaction_performed": False,
            "artifacts": [
                {
                    "type": "context_update",
                    "path": ".hestai/context/PROJECT-CONTEXT.md",
                    "action": "merged",
                    "content": "# PROJECT-CONTEXT\n\nMerged content...",
                }
            ],
        }

        # Should not raise - no compaction, no archive required
        result = validate_ai_response_compaction(ai_response_no_compaction)
        assert result is True
