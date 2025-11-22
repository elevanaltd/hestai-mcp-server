"""Role manifest loading for auto-injecting supporting documentation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default location for role documentation manifests
ROLE_DOCS_DIR = Path(__file__).parent.parent / "conf" / "role_docs"


class RoleManifest:
    """Represents a role's supporting documentation configuration."""

    def __init__(self, role: str, manifest_data: dict[str, Any]):
        self.role = role
        self.description = manifest_data.get("description", "")
        self.version = manifest_data.get("version", "1.0")

        auto_load = manifest_data.get("auto_load_files", {})
        self.mandatory_files = self._parse_file_list(auto_load.get("mandatory", []))
        self.optional_files = self._parse_file_list(auto_load.get("optional", []))

    @staticmethod
    def _parse_file_list(file_list: list[dict[str, str]]) -> list[dict[str, str]]:
        """Parse file list entries with path and reason."""
        parsed = []
        for entry in file_list:
            if isinstance(entry, dict) and "path" in entry:
                parsed.append(entry)
            else:
                logger.warning("Skipping invalid role manifest file entry: %s", entry)
        return parsed

    def get_mandatory_paths(self) -> list[str]:
        """Return list of mandatory file paths."""
        return [entry["path"] for entry in self.mandatory_files]

    def get_optional_paths(self) -> list[str]:
        """Return list of optional file paths."""
        return [entry["path"] for entry in self.optional_files]

    def get_all_paths(self) -> list[str]:
        """Return all file paths (mandatory + optional)."""
        return self.get_mandatory_paths() + self.get_optional_paths()


def load_role_manifest(role: str, manifest_dir: Path | None = None) -> RoleManifest | None:
    """Load role manifest from YAML file.

    Args:
        role: Role name (e.g., 'implementation-lead')
        manifest_dir: Optional directory override (defaults to conf/role_docs/)

    Returns:
        RoleManifest instance or None if manifest doesn't exist
    """
    if manifest_dir is None:
        manifest_dir = ROLE_DOCS_DIR

    manifest_path = manifest_dir / f"{role}.yaml"

    if not manifest_path.exists():
        logger.debug("No role manifest found for '%s' at %s", role, manifest_path)
        return None

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)

        if not isinstance(manifest_data, dict):
            logger.warning("Invalid role manifest format for '%s': expected dict, got %s", role, type(manifest_data))
            return None

        manifest = RoleManifest(role, manifest_data)
        logger.info(
            "Loaded role manifest for '%s': %d mandatory files, %d optional files",
            role,
            len(manifest.mandatory_files),
            len(manifest.optional_files),
        )
        return manifest

    except yaml.YAMLError as exc:
        logger.warning("Failed to parse role manifest for '%s': %s", role, exc)
        return None
    except Exception as exc:
        logger.warning("Failed to load role manifest for '%s': %s", role, exc)
        return None


def load_role_documentation(
    role: str | None,
    explicit_files: list[str] | None = None,
    include_optional: bool = False,
) -> list[str]:
    """Load auto-injected documentation files for a role.

    Args:
        role: Role name to load manifest for
        explicit_files: Files explicitly requested by caller (always included)
        include_optional: Whether to include optional files from manifest

    Returns:
        List of file paths (auto-loaded + explicit files, deduplicated)
    """
    if not role:
        return explicit_files or []

    manifest = load_role_manifest(role)
    if not manifest:
        logger.debug("No manifest for role '%s', using only explicit files", role)
        return explicit_files or []

    # Start with mandatory files
    auto_files = manifest.get_mandatory_paths()

    # Add optional files if requested
    if include_optional:
        auto_files.extend(manifest.get_optional_paths())

    # Merge with explicit files, deduplicate while preserving order
    all_files = auto_files + (explicit_files or [])
    seen = set()
    deduplicated = []
    for path in all_files:
        if path not in seen:
            seen.add(path)
            deduplicated.append(path)

    if auto_files:
        logger.info(
            "Auto-loaded %d files for role '%s' (mandatory=%d, optional=%d, explicit=%d, total=%d)",
            len(auto_files),
            role,
            len(manifest.mandatory_files),
            len(manifest.optional_files) if include_optional else 0,
            len(explicit_files or []),
            len(deduplicated),
        )

    return deduplicated
