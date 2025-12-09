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
    1. .hestai/context/
    2. .coord/
    3. project root

    Args:
        project_root: Project root directory
        filename: Filename to search for (e.g., "PROJECT-CONTEXT.md")

    Returns:
        Path to found file, or None if not found in any location

    Example:
        >>> find_context_file(Path("/project"), "PROJECT-CONTEXT.md")
        Path("/project/.hestai/context/PROJECT-CONTEXT.md")
    """
    search_paths = [
        project_root / ".hestai" / "context" / filename,
        project_root / ".coord" / filename,
        project_root / filename,
    ]

    for path in search_paths:
        if path.exists():
            logger.debug(f"Found {filename} at {path}")
            return path

    logger.debug(f"{filename} not found in any location")
    return None
