"""
Inbox management for Context Steward document processing.

Provides inbox-based document submission and processing workflow:
- Submit documents to pending queue
- Process items from pending to processed
- Maintain audit trail with index
- Track inbox status

Part of Context Steward v2 Shell layer.
"""

import json
import logging
import uuid as uuid_module
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_inbox_structure(project_root: Path) -> Path:
    """
    Ensure inbox directory structure exists.

    Creates:
    - .hestai/inbox/pending/
    - .hestai/inbox/processed/
    - .hestai/inbox/INBOX-STATUS.md
    - .hestai/inbox/processed/index.json

    Args:
        project_root: Project root directory

    Returns:
        Path to inbox directory

    Example:
        >>> inbox = ensure_inbox_structure(Path("/project"))
        >>> assert (inbox / "pending").exists()
    """
    inbox_path = project_root / ".hestai" / "inbox"
    pending_path = inbox_path / "pending"
    processed_path = inbox_path / "processed"

    # Create directories
    pending_path.mkdir(parents=True, exist_ok=True)
    processed_path.mkdir(parents=True, exist_ok=True)

    # Create .gitkeep files
    (pending_path / ".gitkeep").touch()
    (processed_path / ".gitkeep").touch()

    # Create INBOX-STATUS.md if it doesn't exist
    status_file = inbox_path / "INBOX-STATUS.md"
    if not status_file.exists():
        status_content = """# Inbox Status

Current state of document processing inbox.

## Overview
- **Pending**: Documents awaiting processing
- **Processed**: Audit trail (30-day retention, git tracked)

## Usage
Submit documents via `document_submit` tool. Items are processed and moved
to appropriate locations based on visibility rules.
"""
        status_file.write_text(status_content)
        logger.info("Created INBOX-STATUS.md")

    # Create index.json if it doesn't exist
    index_file = processed_path / "index.json"
    if not index_file.exists():
        initial_index = {"processed_items": [], "last_updated": datetime.now().isoformat()}
        index_file.write_text(json.dumps(initial_index, indent=2))
        logger.info("Created processed/index.json")

    return inbox_path


def submit_to_inbox(project_root: Path, content: str, doc_type: str, session_id: str) -> str:
    """
    Submit document to inbox, return UUID.

    Creates JSON file in pending/ with document metadata and content.

    Args:
        project_root: Project root directory
        content: Document content or file reference
        doc_type: Type of document (adr, session_note, workflow, config)
        session_id: Session ID for tracking

    Returns:
        UUID string for the submitted item

    Example:
        >>> uuid = submit_to_inbox(Path("/project"), "content", "adr", "sess1")
        >>> assert len(uuid) > 0
    """
    # Ensure inbox structure exists
    inbox_path = ensure_inbox_structure(project_root)

    # Generate UUID for this submission
    item_uuid = str(uuid_module.uuid4())

    # Create submission metadata
    submission = {
        "uuid": item_uuid,
        "doc_type": doc_type,
        "session_id": session_id,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    }

    # Write to pending directory
    pending_file = inbox_path / "pending" / f"{item_uuid}.json"
    pending_file.write_text(json.dumps(submission, indent=2))

    logger.info(f"Submitted {doc_type} to inbox: {item_uuid}")
    return item_uuid


def process_inbox_item(project_root: Path, uuid: str) -> dict:
    """
    Process item from inbox, move to processed.

    Moves item from pending/ to processed/ and updates index.

    Args:
        project_root: Project root directory
        uuid: UUID of item to process

    Returns:
        Processing result with metadata

    Raises:
        FileNotFoundError: If UUID not found in pending

    Example:
        >>> result = process_inbox_item(Path("/project"), "uuid123")
        >>> assert result["status"] == "processed"
    """
    inbox_path = project_root / ".hestai" / "inbox"
    pending_file = inbox_path / "pending" / f"{uuid}.json"
    processed_file = inbox_path / "processed" / f"{uuid}.json"

    # Check if pending file exists
    if not pending_file.exists():
        raise FileNotFoundError(f"Inbox item not found: {uuid}")

    # Read item data
    item_data = json.loads(pending_file.read_text())

    # Update status and processing timestamp
    item_data["status"] = "processed"
    item_data["processed_at"] = datetime.now().isoformat()

    # Move to processed
    processed_file.write_text(json.dumps(item_data, indent=2))
    pending_file.unlink()

    # Update index
    index_entry = {
        "uuid": uuid,
        "doc_type": item_data["doc_type"],
        "session_id": item_data["session_id"],
        "timestamp": item_data["timestamp"],
        "processed_at": item_data["processed_at"],
    }
    update_index(project_root, index_entry)

    logger.info(f"Processed inbox item: {uuid}")

    return item_data


def update_index(project_root: Path, entry: dict) -> None:
    """
    Update processed/index.json with entry.

    Appends new entry to the processed items list and updates last_updated.

    Args:
        project_root: Project root directory
        entry: Index entry to append

    Example:
        >>> update_index(Path("/project"), {"uuid": "123", "doc_type": "adr"})
    """
    index_file = project_root / ".hestai" / "inbox" / "processed" / "index.json"

    # Read current index
    if index_file.exists():
        index_data = json.loads(index_file.read_text())
    else:
        index_data = {"processed_items": []}

    # Append new entry
    index_data["processed_items"].append(entry)
    index_data["last_updated"] = datetime.now().isoformat()

    # Write back
    index_file.write_text(json.dumps(index_data, indent=2))


def get_inbox_status(project_root: Path) -> dict:
    """
    Get current inbox status (pending count, recent processed).

    Returns summary of inbox state for status reporting.

    Args:
        project_root: Project root directory

    Returns:
        Status dict with pending_count, processed_count, recent_processed

    Example:
        >>> status = get_inbox_status(Path("/project"))
        >>> print(status["pending_count"])
        2
    """
    inbox_path = project_root / ".hestai" / "inbox"

    # Count pending items
    pending_path = inbox_path / "pending"
    pending_count = 0
    if pending_path.exists():
        pending_count = len(list(pending_path.glob("*.json")))

    # Read processed index
    index_file = inbox_path / "processed" / "index.json"
    processed_count = 0
    recent_processed = []

    if index_file.exists():
        index_data = json.loads(index_file.read_text())
        processed_items = index_data.get("processed_items", [])
        processed_count = len(processed_items)
        # Get last 5 processed items
        recent_processed = processed_items[-5:]

    return {
        "pending_count": pending_count,
        "processed_count": processed_count,
        "recent_processed": recent_processed,
    }
