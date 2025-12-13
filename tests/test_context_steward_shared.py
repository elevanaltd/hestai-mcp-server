"""
Tests for Context Steward shared modules (visibility_rules, file_lookup, utils).

Part of Context Steward v2 Shell layer - Phase 1 extraction from requestdoc.py
"""

from datetime import datetime

from tools.context_steward.file_lookup import find_context_file
from tools.context_steward.utils import append_changelog, sanitize_filename
from tools.context_steward.visibility_rules import DOCUMENT_TYPES, VISIBILITY_RULES


class TestVisibilityRules:
    """Test visibility rules module."""

    def test_visibility_rules_structure(self):
        """Test VISIBILITY_RULES contains expected document types."""
        assert "adr" in VISIBILITY_RULES
        assert "context_update" in VISIBILITY_RULES
        assert "session_note" in VISIBILITY_RULES
        assert "workflow_update" in VISIBILITY_RULES

    def test_visibility_rules_format(self):
        """Test each rule has required fields.

        Note: context_update uses read_path/write_path/legacy_path for anchor architecture,
        while other rules use the standard 'path' field.
        """
        for doc_type, rule in VISIBILITY_RULES.items():
            if doc_type == "context_update":
                # Anchor architecture: separate read/write/legacy paths
                assert "read_path" in rule, f"{doc_type} missing 'read_path'"
                assert "write_path" in rule, f"{doc_type} missing 'write_path'"
                assert "legacy_path" in rule, f"{doc_type} missing 'legacy_path'"
            else:
                assert "path" in rule, f"{doc_type} missing 'path'"
            assert "format" in rule, f"{doc_type} missing 'format'"

    def test_document_types_structure(self):
        """Test DOCUMENT_TYPES contains expected types."""
        assert "adr" in DOCUMENT_TYPES
        assert "session_note" in DOCUMENT_TYPES
        assert "workflow" in DOCUMENT_TYPES
        assert "config" in DOCUMENT_TYPES

    def test_document_types_fields(self):
        """Test each document type has required fields."""
        for doc_type, config in DOCUMENT_TYPES.items():
            assert "destination" in config, f"{doc_type} missing 'destination'"
            assert "format" in config, f"{doc_type} missing 'format'"
            assert "compress" in config, f"{doc_type} missing 'compress'"

    def test_document_types_config_validation(self):
        """Test config type has requires_validation=True."""
        assert DOCUMENT_TYPES["config"]["requires_validation"] is True


class TestFileLookup:
    """Test file lookup utilities."""

    def test_find_context_file_in_hestai_context(self, tmp_path):
        """Test finding file in .hestai/context/ (priority 1)."""
        # Setup
        hestai_context = tmp_path / ".hestai" / "context"
        hestai_context.mkdir(parents=True)
        target_file = hestai_context / "PROJECT-CONTEXT.md"
        target_file.write_text("# Context")

        # Also create in coord (lower priority)
        coord = tmp_path / ".coord"
        coord.mkdir()
        (coord / "PROJECT-CONTEXT.md").write_text("# Lower priority")

        # Execute
        result = find_context_file(tmp_path, "PROJECT-CONTEXT.md")

        # Verify
        assert result == target_file

    def test_find_context_file_in_coord(self, tmp_path):
        """Test finding file in .coord/ (priority 2)."""
        # Setup
        coord = tmp_path / ".coord"
        coord.mkdir()
        target_file = coord / "PROJECT-CONTEXT.md"
        target_file.write_text("# Context")

        # Execute
        result = find_context_file(tmp_path, "PROJECT-CONTEXT.md")

        # Verify
        assert result == target_file

    def test_find_context_file_in_root(self, tmp_path):
        """Test finding file in project root (priority 3)."""
        # Setup
        target_file = tmp_path / "PROJECT-CONTEXT.md"
        target_file.write_text("# Context")

        # Execute
        result = find_context_file(tmp_path, "PROJECT-CONTEXT.md")

        # Verify
        assert result == target_file

    def test_find_context_file_not_found(self, tmp_path):
        """Test returns None when file not found anywhere."""
        result = find_context_file(tmp_path, "NONEXISTENT.md")
        assert result is None

    def test_find_context_file_priority_order(self, tmp_path):
        """Test priority order is maintained (.hestai > .coord > root)."""
        # Setup - create file in all three locations
        hestai_file = tmp_path / ".hestai" / "context" / "TEST.md"
        hestai_file.parent.mkdir(parents=True)
        hestai_file.write_text("priority 1")

        coord_file = tmp_path / ".coord" / "TEST.md"
        coord_file.parent.mkdir(parents=True)
        coord_file.write_text("priority 2")

        root_file = tmp_path / "TEST.md"
        root_file.write_text("priority 3")

        # Execute
        result = find_context_file(tmp_path, "TEST.md")

        # Verify - should find the .hestai version
        assert result == hestai_file
        assert result.read_text() == "priority 1"


class TestUtils:
    """Test utility functions."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("Add user authentication")
        assert result == "add-user-authentication"

    def test_sanitize_filename_removes_special_chars(self):
        """Test removal of special characters."""
        result = sanitize_filename("Fix: API/endpoint & validation!")
        assert result == "fix-apiendpoint-validation"

    def test_sanitize_filename_length_limit(self):
        """Test filename is limited to 50 characters."""
        long_text = "a" * 100
        result = sanitize_filename(long_text)
        assert len(result) == 50

    def test_sanitize_filename_multiple_spaces(self):
        """Test multiple spaces become single hyphens."""
        result = sanitize_filename("Update   project    context")
        assert result == "update-project-context"

    def test_append_changelog_creates_new(self, tmp_path):
        """Test creating new changelog with header."""
        # Setup
        hestai_context = tmp_path / ".hestai" / "context"
        hestai_context.mkdir(parents=True)

        # Execute
        append_changelog(tmp_path, "Added user module", "Add user authentication")

        # Verify
        changelog_path = hestai_context / "PROJECT-CHANGELOG.md"
        assert changelog_path.exists()

        content = changelog_path.read_text()
        assert "# PROJECT-CHANGELOG" in content
        assert "*Audit trail of context updates. Most recent first.*" in content
        assert "**Add user authentication**" in content
        assert "Added user module" in content

    def test_append_changelog_prepends_to_existing(self, tmp_path):
        """Test prepending to existing changelog."""
        # Setup
        hestai_context = tmp_path / ".hestai" / "context"
        hestai_context.mkdir(parents=True)
        changelog_path = hestai_context / "PROJECT-CHANGELOG.md"

        existing_content = """# PROJECT-CHANGELOG

*Audit trail of context updates. Most recent first.*

## 2025-01-01 10:00
**Previous change**
Old entry

"""
        changelog_path.write_text(existing_content)

        # Execute
        append_changelog(tmp_path, "New entry", "New intent")

        # Verify
        content = changelog_path.read_text()

        # New entry should be after header but before old entry
        assert content.index("**New intent**") < content.index("**Previous change**")
        assert "New entry" in content
        assert "Old entry" in content

    def test_append_changelog_includes_timestamp(self, tmp_path):
        """Test changelog entries include timestamp."""
        # Setup
        hestai_context = tmp_path / ".hestai" / "context"
        hestai_context.mkdir(parents=True)

        # Execute
        append_changelog(tmp_path, "Test entry", "Test intent")

        # Verify
        content = (hestai_context / "PROJECT-CHANGELOG.md").read_text()

        # Should have timestamp in format YYYY-MM-DD HH:MM
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in content

    def test_append_changelog_creates_directory(self, tmp_path):
        """Test changelog creation creates parent directories."""
        # Execute (no .hestai/context yet)
        append_changelog(tmp_path, "Test entry", "Test intent")

        # Verify
        changelog_path = tmp_path / ".hestai" / "context" / "PROJECT-CHANGELOG.md"
        assert changelog_path.exists()
        assert changelog_path.parent.exists()
