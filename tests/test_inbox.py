"""
Tests for Context Steward inbox management.

Part of Context Steward v2 Shell layer - Phase 1 inbox infrastructure.
"""

import json
from datetime import datetime

import pytest

from tools.context_steward.inbox import (
    ensure_inbox_structure,
    get_inbox_status,
    process_inbox_item,
    submit_to_inbox,
    update_index,
)


class TestInboxStructure:
    """Test inbox directory structure creation."""

    def test_ensure_inbox_structure_creates_directories(self, tmp_path):
        """Test inbox structure creation."""
        # Execute
        inbox_path = ensure_inbox_structure(tmp_path)

        # Verify
        assert inbox_path.exists()
        assert (inbox_path / "pending").exists()
        assert (inbox_path / "processed").exists()

    def test_ensure_inbox_structure_creates_gitkeep(self, tmp_path):
        """Test .gitkeep files are created."""
        # Execute
        inbox_path = ensure_inbox_structure(tmp_path)

        # Verify
        assert (inbox_path / "pending" / ".gitkeep").exists()
        assert (inbox_path / "processed" / ".gitkeep").exists()

    def test_ensure_inbox_structure_creates_status_file(self, tmp_path):
        """Test INBOX-STATUS.md is created."""
        # Execute
        inbox_path = ensure_inbox_structure(tmp_path)

        # Verify
        status_file = inbox_path / "INBOX-STATUS.md"
        assert status_file.exists()
        content = status_file.read_text()
        assert "# Inbox Status" in content

    def test_ensure_inbox_structure_creates_index(self, tmp_path):
        """Test processed/index.json is created."""
        # Execute
        inbox_path = ensure_inbox_structure(tmp_path)

        # Verify
        index_file = inbox_path / "processed" / "index.json"
        assert index_file.exists()
        data = json.loads(index_file.read_text())
        assert "processed_items" in data
        assert isinstance(data["processed_items"], list)

    def test_ensure_inbox_structure_idempotent(self, tmp_path):
        """Test calling ensure_inbox_structure multiple times is safe."""
        # Execute twice
        inbox_path1 = ensure_inbox_structure(tmp_path)
        inbox_path2 = ensure_inbox_structure(tmp_path)

        # Verify - should be same path and structure intact
        assert inbox_path1 == inbox_path2
        assert (inbox_path1 / "pending").exists()
        assert (inbox_path1 / "processed").exists()


class TestSubmitToInbox:
    """Test document submission to inbox."""

    def test_submit_to_inbox_creates_file(self, tmp_path):
        """Test submission creates file in pending directory."""
        # Setup
        ensure_inbox_structure(tmp_path)

        # Execute
        uuid = submit_to_inbox(tmp_path, content="Test content", doc_type="adr", session_id="test-session")

        # Verify
        pending_file = tmp_path / ".hestai" / "inbox" / "pending" / f"{uuid}.json"
        assert pending_file.exists()

        data = json.loads(pending_file.read_text())
        assert data["content"] == "Test content"
        assert data["doc_type"] == "adr"
        assert data["session_id"] == "test-session"
        assert "timestamp" in data
        assert data["uuid"] == uuid

    def test_submit_to_inbox_returns_uuid(self, tmp_path):
        """Test submission returns valid UUID."""
        # Setup
        ensure_inbox_structure(tmp_path)

        # Execute
        uuid = submit_to_inbox(tmp_path, content="Test", doc_type="session_note", session_id="sess1")

        # Verify - should be UUID-like (simple check)
        assert len(uuid) > 0
        assert "-" in uuid  # UUIDs have hyphens

    def test_submit_to_inbox_includes_timestamp(self, tmp_path):
        """Test submission includes timestamp."""
        # Setup
        ensure_inbox_structure(tmp_path)

        # Execute
        uuid = submit_to_inbox(tmp_path, content="Test", doc_type="workflow", session_id="s1")

        # Verify
        pending_file = tmp_path / ".hestai" / "inbox" / "pending" / f"{uuid}.json"
        data = json.loads(pending_file.read_text())

        # Should have ISO format timestamp
        assert "timestamp" in data
        # Should be parseable as datetime
        datetime.fromisoformat(data["timestamp"])


class TestProcessInboxItem:
    """Test inbox item processing."""

    def test_process_inbox_item_moves_to_processed(self, tmp_path):
        """Test processing moves item from pending to processed."""
        # Setup
        ensure_inbox_structure(tmp_path)
        uuid = submit_to_inbox(tmp_path, content="Test", doc_type="adr", session_id="s1")

        # Execute
        result = process_inbox_item(tmp_path, uuid)

        # Verify
        pending_file = tmp_path / ".hestai" / "inbox" / "pending" / f"{uuid}.json"
        processed_file = tmp_path / ".hestai" / "inbox" / "processed" / f"{uuid}.json"

        assert not pending_file.exists()
        assert processed_file.exists()
        assert result["status"] == "processed"

    def test_process_inbox_item_updates_index(self, tmp_path):
        """Test processing updates the index."""
        # Setup
        ensure_inbox_structure(tmp_path)
        uuid = submit_to_inbox(tmp_path, content="Test", doc_type="adr", session_id="s1")

        # Execute
        process_inbox_item(tmp_path, uuid)

        # Verify
        index_file = tmp_path / ".hestai" / "inbox" / "processed" / "index.json"
        data = json.loads(index_file.read_text())

        assert len(data["processed_items"]) == 1
        assert data["processed_items"][0]["uuid"] == uuid

    def test_process_inbox_item_returns_metadata(self, tmp_path):
        """Test processing returns item metadata."""
        # Setup
        ensure_inbox_structure(tmp_path)
        uuid = submit_to_inbox(tmp_path, content="Test", doc_type="workflow", session_id="s1")

        # Execute
        result = process_inbox_item(tmp_path, uuid)

        # Verify
        assert result["uuid"] == uuid
        assert result["doc_type"] == "workflow"
        assert result["status"] == "processed"

    def test_process_inbox_item_handles_missing_uuid(self, tmp_path):
        """Test processing non-existent UUID raises error."""
        # Setup
        ensure_inbox_structure(tmp_path)

        # Execute & Verify
        with pytest.raises(FileNotFoundError):
            process_inbox_item(tmp_path, "nonexistent-uuid")


class TestUpdateIndex:
    """Test index update functionality."""

    def test_update_index_adds_entry(self, tmp_path):
        """Test updating index adds entry."""
        # Setup
        ensure_inbox_structure(tmp_path)

        entry = {
            "uuid": "test-uuid",
            "doc_type": "adr",
            "timestamp": datetime.now().isoformat(),
            "status": "processed",
        }

        # Execute
        update_index(tmp_path, entry)

        # Verify
        index_file = tmp_path / ".hestai" / "inbox" / "processed" / "index.json"
        data = json.loads(index_file.read_text())

        assert len(data["processed_items"]) == 1
        assert data["processed_items"][0]["uuid"] == "test-uuid"

    def test_update_index_appends_multiple_entries(self, tmp_path):
        """Test updating index multiple times appends."""
        # Setup
        ensure_inbox_structure(tmp_path)

        entry1 = {"uuid": "uuid1", "doc_type": "adr", "timestamp": datetime.now().isoformat()}
        entry2 = {"uuid": "uuid2", "doc_type": "session_note", "timestamp": datetime.now().isoformat()}

        # Execute
        update_index(tmp_path, entry1)
        update_index(tmp_path, entry2)

        # Verify
        index_file = tmp_path / ".hestai" / "inbox" / "processed" / "index.json"
        data = json.loads(index_file.read_text())

        assert len(data["processed_items"]) == 2
        assert data["processed_items"][0]["uuid"] == "uuid1"
        assert data["processed_items"][1]["uuid"] == "uuid2"


class TestGetInboxStatus:
    """Test inbox status retrieval."""

    def test_get_inbox_status_empty(self, tmp_path):
        """Test status for empty inbox."""
        # Setup
        ensure_inbox_structure(tmp_path)

        # Execute
        status = get_inbox_status(tmp_path)

        # Verify
        assert status["pending_count"] == 0
        assert status["processed_count"] == 0
        assert len(status["recent_processed"]) == 0

    def test_get_inbox_status_with_pending(self, tmp_path):
        """Test status counts pending items."""
        # Setup
        ensure_inbox_structure(tmp_path)
        submit_to_inbox(tmp_path, content="Test1", doc_type="adr", session_id="s1")
        submit_to_inbox(tmp_path, content="Test2", doc_type="workflow", session_id="s2")

        # Execute
        status = get_inbox_status(tmp_path)

        # Verify
        assert status["pending_count"] == 2

    def test_get_inbox_status_with_processed(self, tmp_path):
        """Test status counts processed items."""
        # Setup
        ensure_inbox_structure(tmp_path)
        uuid1 = submit_to_inbox(tmp_path, content="Test1", doc_type="adr", session_id="s1")
        uuid2 = submit_to_inbox(tmp_path, content="Test2", doc_type="workflow", session_id="s2")

        process_inbox_item(tmp_path, uuid1)
        process_inbox_item(tmp_path, uuid2)

        # Execute
        status = get_inbox_status(tmp_path)

        # Verify
        assert status["pending_count"] == 0
        assert status["processed_count"] == 2
        assert len(status["recent_processed"]) == 2

    def test_get_inbox_status_recent_limit(self, tmp_path):
        """Test recent processed is limited to last 5."""
        # Setup
        ensure_inbox_structure(tmp_path)

        # Create and process 7 items
        uuids = []
        for i in range(7):
            uuid = submit_to_inbox(tmp_path, content=f"Test{i}", doc_type="adr", session_id=f"s{i}")
            uuids.append(uuid)

        for uuid in uuids:
            process_inbox_item(tmp_path, uuid)

        # Execute
        status = get_inbox_status(tmp_path)

        # Verify
        assert status["processed_count"] == 7
        assert len(status["recent_processed"]) == 5  # Limited to last 5
