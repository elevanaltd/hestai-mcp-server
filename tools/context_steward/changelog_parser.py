"""
CHANGELOG Parser - Section-aware conflict detection.

Part of Context Steward v2 Phase 2 (Issue #91).

Parses PROJECT-CHANGELOG.md to detect section-level conflicts
when multiple agents submit concurrent context updates.
"""

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ChangelogEntry:
    """Represents a parsed changelog entry."""

    timestamp: datetime
    intent: str
    description: str
    target: str

    def extract_sections(self) -> list[str]:
        """
        Extract section names from intent and description.

        Looks for patterns like:
        - "Update ARCHITECTURE section"
        - "Modified CURRENT_STATE and DEPENDENCIES"
        - References to ## SECTION_NAME

        Returns:
            List of section names (e.g., ["ARCHITECTURE", "DEPENDENCIES"])
        """
        text = f"{self.intent} {self.description}"

        # Pattern 1: ## SECTION_NAME (markdown headers)
        sections = re.findall(r"##\s+([A-Z_]+)", text)

        # Pattern 2: Uppercase words that look like section names (3+ chars)
        # Common sections: ARCHITECTURE, DEPENDENCIES, CURRENT_STATE, etc.
        uppercase_words = re.findall(r"\b([A-Z_]{3,})\b", text)
        sections.extend(uppercase_words)

        # Deduplicate and return
        return list(set(sections))


def parse_recent_changes(changelog_path: Path, minutes: int = 30) -> list[ChangelogEntry]:
    """
    Parse PROJECT-CHANGELOG.md for recent changes within time window.

    Args:
        changelog_path: Path to PROJECT-CHANGELOG.md
        minutes: Time window for recent changes (default: 30 minutes)

    Returns:
        List of ChangelogEntry objects within time window
    """
    if not changelog_path.exists():
        return []

    entries = []
    content = changelog_path.read_text()

    # Parse entries - format: ## YYYY-MM-DD HH:MM\n**Intent**\nDescription
    entry_pattern = r"##\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\n\*\*(.+?)\*\*\s*\n(.+?)(?=\n##|\Z)"
    matches = re.finditer(entry_pattern, content, re.MULTILINE | re.DOTALL)

    cutoff_time = datetime.now() - timedelta(minutes=minutes)

    for match in matches:
        timestamp_str, intent, description = match.groups()
        try:
            entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
            if entry_time >= cutoff_time:
                # Extract target from intent or description (e.g., "Updated PROJECT-CONTEXT")
                target_match = re.search(r"PROJECT-(?:CONTEXT|CHECKLIST|ROADMAP)", f"{intent} {description}")
                target = target_match.group(0) if target_match else "PROJECT-CONTEXT"

                entries.append(
                    ChangelogEntry(
                        timestamp=entry_time,
                        intent=intent.strip(),
                        description=description.strip()[:200],  # Limit description length
                        target=target,
                    )
                )
        except ValueError as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            continue

    return entries


def detect_section_conflicts(
    recent_entries: list[ChangelogEntry],
    new_content: str,
    target: str,
) -> dict | None:
    """
    Detect section-level conflicts between recent changes and new content.

    Args:
        recent_entries: Recent changelog entries from parse_recent_changes()
        new_content: New content being submitted
        target: Target file (e.g., "PROJECT-CONTEXT")

    Returns:
        Conflict dict with continuation_id if conflict detected, None otherwise
    """
    if not recent_entries:
        return None

    # Extract sections from new content
    new_sections = set(re.findall(r"##\s+([A-Z_]+)", new_content))

    # Check each recent entry for same target + overlapping sections
    for entry in recent_entries:
        # Skip if different target
        if entry.target != target:
            continue

        # Extract sections from recent entry
        recent_sections = set(entry.extract_sections())

        # Check for overlap
        overlapping = new_sections.intersection(recent_sections)
        if overlapping:
            conflict_id = f"conflict-{uuid.uuid4().hex[:8]}"
            return {
                "status": "conflict",
                "conflict_type": "same_section_modified",
                "details": {
                    "section": ", ".join(sorted(overlapping)),
                    "your_sections": sorted(new_sections),
                    "recent_sections": sorted(recent_sections),
                    "modified_by": f"Recent change: {entry.intent}",
                    "modified_at": entry.timestamp.strftime("%Y-%m-%d %H:%M"),
                },
                "suggestion": f"Section(s) {', '.join(sorted(overlapping))} were recently modified. Review before merging.",
                "continuation_id": conflict_id,
            }

    return None


def store_conflict_state(
    project_root: Path,
    conflict_id: str,
    conflict_data: dict,
    request_data: dict,
) -> Path:
    """
    Store conflict state to inbox for resolution via continuation_id.

    Args:
        project_root: Project root directory
        conflict_id: Unique conflict identifier
        conflict_data: Conflict details from detect_section_conflicts()
        request_data: Original request data for context

    Returns:
        Path to stored conflict file
    """
    pending_dir = project_root / ".hestai" / "inbox" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    conflict_file = pending_dir / f"{conflict_id}.json"

    import json

    state = {
        "conflict_id": conflict_id,
        "created_at": datetime.now().isoformat(),
        "conflict": conflict_data,
        "original_request": {
            "target": request_data.get("target"),
            "intent": request_data.get("intent"),
            "content": request_data.get("content", "")[:500],  # Truncate for storage
            "file_ref": request_data.get("file_ref", ""),
        },
    }

    conflict_file.write_text(json.dumps(state, indent=2))
    logger.info(f"Stored conflict state to {conflict_file}")

    return conflict_file


def _validate_continuation_id(continuation_id: str) -> bool:
    """
    Validate continuation_id format to prevent path traversal.

    Only allows lowercase alphanumeric, hyphens, and length 8-64.

    Args:
        continuation_id: ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not continuation_id or len(continuation_id) < 8 or len(continuation_id) > 64:
        return False

    # Only allow: lowercase letters, digits, hyphens
    return re.match(r"^[a-z0-9-]+$", continuation_id) is not None


def load_conflict_state(project_root: Path, continuation_id: str) -> dict | None:
    """
    Load conflict state from inbox for resolution.

    Args:
        project_root: Project root directory
        continuation_id: Unique conflict identifier from previous request

    Returns:
        Conflict state dict, or None if not found

    Raises:
        ValueError: If continuation_id is invalid (security: prevent path traversal)
    """
    # Security: validate ID format
    if not _validate_continuation_id(continuation_id):
        raise ValueError(f"Invalid continuation_id format: {continuation_id}")

    pending_dir = project_root / ".hestai" / "inbox" / "pending"
    conflict_file = pending_dir / f"{continuation_id}.json"

    # Security: ensure resolved path is within pending directory
    try:
        conflict_file_resolved = conflict_file.resolve()
        pending_dir_resolved = pending_dir.resolve()
        if not str(conflict_file_resolved).startswith(str(pending_dir_resolved)):
            raise ValueError(f"Path traversal attempt detected: {continuation_id}")
    except Exception as e:
        logger.error(f"Path validation failed for {continuation_id}: {e}")
        return None

    if not conflict_file.exists():
        logger.warning(f"Conflict state not found: {continuation_id}")
        return None

    try:
        import json

        state = json.loads(conflict_file.read_text())
        return state
    except Exception as e:
        logger.error(f"Failed to load conflict state {continuation_id}: {e}")
        return None


def clear_conflict_state(project_root: Path, continuation_id: str) -> bool:
    """
    Clear conflict state after resolution.

    Args:
        project_root: Project root directory
        continuation_id: Unique conflict identifier

    Returns:
        True if cleared successfully, False otherwise

    Raises:
        ValueError: If continuation_id is invalid (security: prevent path traversal)
    """
    # Security: validate ID format
    if not _validate_continuation_id(continuation_id):
        raise ValueError(f"Invalid continuation_id format: {continuation_id}")

    pending_dir = project_root / ".hestai" / "inbox" / "pending"
    conflict_file = pending_dir / f"{continuation_id}.json"

    # Security: ensure resolved path is within pending directory
    try:
        conflict_file_resolved = conflict_file.resolve()
        pending_dir_resolved = pending_dir.resolve()
        if not str(conflict_file_resolved).startswith(str(pending_dir_resolved)):
            raise ValueError(f"Path traversal attempt detected: {continuation_id}")
    except Exception as e:
        logger.error(f"Path validation failed for {continuation_id}: {e}")
        return False

    if conflict_file.exists():
        conflict_file.unlink()
        logger.info(f"Cleared conflict state: {continuation_id}")
        return True

    return False
