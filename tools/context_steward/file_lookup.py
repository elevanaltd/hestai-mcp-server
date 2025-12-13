"""
File lookup utilities for Context Steward.

Provides multi-location file search across .hestai/context/, .coord/, and
project root with priority ordering.

Part of Context Steward v2 Shell layer.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def find_context_file(project_root: Path, filename: str) -> Path | None:
    """
    Find context file in priority order across multiple locations.

    Searches for the file in:
    1. .hestai/snapshots/ (anchor architecture - READ-ONLY synthesized by Steward)
    2. .hestai/context/ (legacy architecture - direct writes)
    3. .coord/ (legacy coordination directory)
    4. project root

    Anchor architecture takes precedence when both exist (migration in progress).

    Args:
        project_root: Project root directory
        filename: Filename to search for (e.g., "PROJECT-CONTEXT.md")

    Returns:
        Path to found file, or None if not found in any location

    Example:
        >>> find_context_file(Path("/project"), "PROJECT-CONTEXT.md")
        Path("/project/.hestai/snapshots/PROJECT-CONTEXT.md")  # Anchor mode
        Path("/project/.hestai/context/PROJECT-CONTEXT.md")     # Legacy mode
    """
    search_paths = [
        project_root / ".hestai" / "snapshots" / filename,  # Anchor architecture (prioritized)
        project_root / ".hestai" / "context" / filename,  # Legacy architecture
        project_root / ".coord" / filename,  # Legacy coordination
        project_root / filename,  # Project root fallback
    ]

    for path in search_paths:
        if path.exists():
            logger.debug(f"Found {filename} at {path}")
            return path

    logger.debug(f"{filename} not found in any location")
    return None
