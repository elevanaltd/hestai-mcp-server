"""
Utility functions for Context Steward operations.

Provides filename sanitization and changelog management utilities.

Part of Context Steward v2 Shell layer.
"""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use in filename.

    Converts to lowercase, replaces spaces with hyphens, removes special
    characters, collapses multiple hyphens, and limits to 50 characters.

    Args:
        text: Raw text to sanitize

    Returns:
        Sanitized filename-safe string

    Example:
        >>> sanitize_filename("Add User Authentication")
        'add-user-authentication'
        >>> sanitize_filename("Fix: API/endpoint & validation!")
        'fix-apiendpoint-validation'
    """
    # Convert to lowercase, replace spaces with hyphens
    sanitized = text.lower().replace(" ", "-")
    # Remove any characters that aren't alphanumeric or hyphens
    sanitized = "".join(c for c in sanitized if c.isalnum() or c == "-")
    # Collapse multiple hyphens into single hyphen
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    # Limit length
    return sanitized[:50]


def append_changelog(project_root: Path, entry: str, intent: str) -> None:
    """
    Append entry to PROJECT-CHANGELOG.md.

    Creates the changelog file if it doesn't exist with proper header.
    Appends new entries at the top (most recent first).

    Args:
        project_root: Project root directory
        entry: One-line changelog entry from AI
        intent: Original intent for additional context

    Example:
        >>> append_changelog(Path("/project"), "Added user module", "Add user authentication")
        # Creates/updates .hestai/context/PROJECT-CHANGELOG.md
    """
    changelog_path = project_root / ".hestai" / "context" / "PROJECT-CHANGELOG.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Format the new entry
    new_entry = f"## {timestamp}\n**{intent}**\n{entry}\n\n"

    if changelog_path.exists():
        # Read existing content and prepend new entry after header
        existing = changelog_path.read_text()
        # Find end of header (after first blank line following title)
        header_end = existing.find("\n\n")
        if header_end != -1:
            header = existing[: header_end + 2]
            rest = existing[header_end + 2 :]
            updated = header + new_entry + rest
        else:
            updated = existing + "\n" + new_entry
        changelog_path.write_text(updated)
    else:
        # Create new changelog with header
        header = """# PROJECT-CHANGELOG

*Audit trail of context updates. Most recent first.*

"""
        changelog_path.parent.mkdir(parents=True, exist_ok=True)
        changelog_path.write_text(header + new_entry)

    logger.info(f"Appended changelog entry: {entry[:50]}...")
