"""
Tests for CHANGELOG Parser - Section-aware conflict detection.

Test Coverage:
1. Parse recent changes from CHANGELOG with timestamp filtering
2. Extract section modifications from changelog entries
3. Detect same-section conflicts (true positive)
4. Ignore unrelated-section changes (false positive prevention)
5. Handle malformed changelog entries gracefully
"""

from datetime import datetime, timedelta

import pytest

from tools.context_steward.changelog_parser import (
    ChangelogEntry,
    detect_section_conflicts,
    parse_recent_changes,
)


class TestParseRecentChanges:
    """Test parsing recent changes from CHANGELOG."""

    def test_parse_recent_changes_finds_entries(self, tmp_path):
        """Test parsing finds entries within time window."""
        changelog = tmp_path / "PROJECT-CHANGELOG.md"
        recent_time = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
        old_time = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")

        changelog.write_text(
            f"""# PROJECT-CHANGELOG

## {recent_time}
**Updated CURRENT_STATE section**
Changed phase from B1 to B2

## {old_time}
**Old update**
Should not appear in results

"""
        )

        entries = parse_recent_changes(changelog, minutes=30)

        assert len(entries) == 1
        assert entries[0].intent == "Updated CURRENT_STATE section"
        assert "B1 to B2" in entries[0].description

    def test_parse_recent_changes_extracts_sections(self, tmp_path):
        """Test parser extracts section names from intent and description."""
        changelog = tmp_path / "PROJECT-CHANGELOG.md"
        recent_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")

        changelog.write_text(
            f"""# PROJECT-CHANGELOG

## {recent_time}
**Modified ARCHITECTURE and DEPENDENCIES sections**
Updated Python version in ARCHITECTURE, added new dependency

"""
        )

        entries = parse_recent_changes(changelog, minutes=30)

        assert len(entries) == 1
        # Should detect both ARCHITECTURE and DEPENDENCIES
        assert "ARCHITECTURE" in entries[0].intent or "ARCHITECTURE" in entries[0].description
        assert "DEPENDENCIES" in entries[0].intent or "DEPENDENCIES" in entries[0].description

    def test_parse_recent_changes_empty_changelog(self, tmp_path):
        """Test parsing empty changelog returns empty list."""
        changelog = tmp_path / "PROJECT-CHANGELOG.md"
        changelog.write_text("# PROJECT-CHANGELOG\n\n")

        entries = parse_recent_changes(changelog, minutes=30)

        assert len(entries) == 0

    def test_parse_recent_changes_nonexistent_file(self, tmp_path):
        """Test parsing nonexistent file returns empty list."""
        changelog = tmp_path / "NONEXISTENT.md"

        entries = parse_recent_changes(changelog, minutes=30)

        assert len(entries) == 0

    def test_parse_recent_changes_malformed_timestamp(self, tmp_path):
        """Test parser skips entries with malformed timestamps."""
        changelog = tmp_path / "PROJECT-CHANGELOG.md"

        changelog.write_text(
            """# PROJECT-CHANGELOG

## INVALID-TIMESTAMP
**Some update**
Should be skipped

"""
        )

        entries = parse_recent_changes(changelog, minutes=30)

        assert len(entries) == 0


class TestDetectSectionConflicts:
    """Test section-level conflict detection."""

    def test_same_section_conflict_detected(self, tmp_path):
        """Test conflict when same section modified recently."""
        # Recent change to CURRENT_STATE
        recent_entry = ChangelogEntry(
            timestamp=datetime.now() - timedelta(minutes=5),
            intent="Update CURRENT_STATE",
            description="Set phase to B2",
            target="PROJECT-CONTEXT",
        )

        # New change also to CURRENT_STATE
        new_content = """## CURRENT_STATE
PHASE::B1
"""

        conflict = detect_section_conflicts(
            recent_entries=[recent_entry],
            new_content=new_content,
            target="PROJECT-CONTEXT",
        )

        assert conflict is not None
        assert conflict["status"] == "conflict"
        assert conflict["conflict_type"] == "same_section_modified"
        assert "CURRENT_STATE" in conflict["details"]["section"]
        assert "continuation_id" in conflict

    def test_unrelated_sections_no_conflict(self, tmp_path):
        """Test no conflict when different sections modified."""
        # Recent change to ARCHITECTURE
        recent_entry = ChangelogEntry(
            timestamp=datetime.now() - timedelta(minutes=5),
            intent="Update ARCHITECTURE",
            description="Added new service",
            target="PROJECT-CONTEXT",
        )

        # New change to RECENT_ACHIEVEMENTS (unrelated)
        new_content = """## RECENT_ACHIEVEMENTS
- Completed feature X
"""

        conflict = detect_section_conflicts(
            recent_entries=[recent_entry],
            new_content=new_content,
            target="PROJECT-CONTEXT",
        )

        assert conflict is None

    def test_multiple_sections_partial_conflict(self, tmp_path):
        """Test conflict when one of multiple sections overlaps."""
        # Recent change to ARCHITECTURE
        recent_entry = ChangelogEntry(
            timestamp=datetime.now() - timedelta(minutes=5),
            intent="Update ARCHITECTURE section",
            description="Changed stack",
            target="PROJECT-CONTEXT",
        )

        # New change to ARCHITECTURE and IDENTITY
        new_content = """## IDENTITY
NAME::TestProject

## ARCHITECTURE
STACK::Updated
"""

        conflict = detect_section_conflicts(
            recent_entries=[recent_entry],
            new_content=new_content,
            target="PROJECT-CONTEXT",
        )

        assert conflict is not None
        assert "ARCHITECTURE" in conflict["details"]["section"]

    def test_no_recent_entries_no_conflict(self, tmp_path):
        """Test no conflict when no recent entries exist."""
        new_content = """## CURRENT_STATE
PHASE::B1
"""

        conflict = detect_section_conflicts(
            recent_entries=[],
            new_content=new_content,
            target="PROJECT-CONTEXT",
        )

        assert conflict is None

    def test_different_target_no_conflict(self, tmp_path):
        """Test no conflict when recent changes to different target."""
        # Recent change to PROJECT-ROADMAP
        recent_entry = ChangelogEntry(
            timestamp=datetime.now() - timedelta(minutes=5),
            intent="Update roadmap",
            description="Added milestone",
            target="PROJECT-ROADMAP",
        )

        # New change to PROJECT-CONTEXT
        new_content = """## CURRENT_STATE
PHASE::B1
"""

        conflict = detect_section_conflicts(
            recent_entries=[recent_entry],
            new_content=new_content,
            target="PROJECT-CONTEXT",
        )

        assert conflict is None


class TestChangelogEntryModel:
    """Test ChangelogEntry data model."""

    def test_changelog_entry_creation(self):
        """Test creating ChangelogEntry with all fields."""
        entry = ChangelogEntry(
            timestamp=datetime.now(),
            intent="Test update",
            description="Test description",
            target="PROJECT-CONTEXT",
        )

        assert entry.intent == "Test update"
        assert entry.description == "Test description"
        assert entry.target == "PROJECT-CONTEXT"
        assert isinstance(entry.timestamp, datetime)

    def test_changelog_entry_extracts_sections(self):
        """Test ChangelogEntry can identify mentioned sections."""
        entry = ChangelogEntry(
            timestamp=datetime.now(),
            intent="Update ARCHITECTURE and DEPENDENCIES",
            description="Modified sections",
            target="PROJECT-CONTEXT",
        )

        sections = entry.extract_sections()

        assert "ARCHITECTURE" in sections
        assert "DEPENDENCIES" in sections


class TestSecurityValidation:
    """Test security validation for continuation_id (Issue #91 security fixes)."""

    def test_path_traversal_prevention_in_load(self, tmp_path):
        """Test that path traversal attempts are blocked in load_conflict_state."""
        from tools.context_steward.changelog_parser import load_conflict_state

        # Attempt path traversal with ../
        with pytest.raises(ValueError, match="Invalid continuation_id format"):
            load_conflict_state(tmp_path, "../../../etc/passwd")

        # Attempt absolute path
        with pytest.raises(ValueError, match="Invalid continuation_id format"):
            load_conflict_state(tmp_path, "/etc/passwd")

        # Attempt with uppercase (should fail validation)
        with pytest.raises(ValueError, match="Invalid continuation_id format"):
            load_conflict_state(tmp_path, "INVALID-ID")

    def test_path_traversal_prevention_in_clear(self, tmp_path):
        """Test that path traversal attempts are blocked in clear_conflict_state."""
        from tools.context_steward.changelog_parser import clear_conflict_state

        # Attempt path traversal
        with pytest.raises(ValueError, match="Invalid continuation_id format"):
            clear_conflict_state(tmp_path, "../../../etc/passwd")

    def test_valid_continuation_id_formats(self, tmp_path):
        """Test that valid continuation_id formats are accepted."""
        from tools.context_steward.changelog_parser import load_conflict_state

        # Create valid conflict file
        pending_dir = tmp_path / ".hestai" / "inbox" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        # Valid formats
        valid_ids = [
            "conflict-abc12345",
            "conflict-12345678",
            "abc-def-ghi-123",
        ]

        for valid_id in valid_ids:
            conflict_file = pending_dir / f"{valid_id}.json"
            conflict_file.write_text('{"test": "data"}')

            # Should not raise ValueError
            result = load_conflict_state(tmp_path, valid_id)
            assert result == {"test": "data"}

    def test_invalid_continuation_id_formats_rejected(self, tmp_path):
        """Test that invalid continuation_id formats are rejected."""
        from tools.context_steward.changelog_parser import load_conflict_state

        invalid_ids = [
            "",  # Empty
            "abc",  # Too short (< 8 chars)
            "a" * 65,  # Too long (> 64 chars)
            "conflict-ABC",  # Uppercase
            "conflict@123",  # Special chars
            "conflict 123",  # Spaces
            "../conflict",  # Path traversal
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid continuation_id format"):
                load_conflict_state(tmp_path, invalid_id)
