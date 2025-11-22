"""Tests for role manifest loading and auto-file injection."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from utils.role_manifest import RoleManifest, load_role_documentation, load_role_manifest


class TestRoleManifest:
    """Test RoleManifest class."""

    def test_parse_valid_manifest(self):
        """Test parsing a valid manifest with mandatory and optional files."""
        manifest_data = {
            "role": "test-role",
            "description": "Test role",
            "version": "1.0",
            "auto_load_files": {
                "mandatory": [
                    {"path": "/path/to/file1.md", "reason": "Core functionality"},
                    {"path": "/path/to/file2.md", "reason": "Essential patterns"},
                ],
                "optional": [
                    {"path": "/path/to/file3.md", "reason": "Advanced topics"},
                ],
            },
        }

        manifest = RoleManifest("test-role", manifest_data)

        assert manifest.role == "test-role"
        assert manifest.description == "Test role"
        assert manifest.version == "1.0"
        assert len(manifest.mandatory_files) == 2
        assert len(manifest.optional_files) == 1
        assert manifest.get_mandatory_paths() == ["/path/to/file1.md", "/path/to/file2.md"]
        assert manifest.get_optional_paths() == ["/path/to/file3.md"]
        assert manifest.get_all_paths() == ["/path/to/file1.md", "/path/to/file2.md", "/path/to/file3.md"]

    def test_parse_manifest_with_missing_fields(self):
        """Test parsing manifest with missing optional fields."""
        manifest_data = {
            "auto_load_files": {
                "mandatory": [
                    {"path": "/path/to/file1.md", "reason": "Core"},
                ],
            },
        }

        manifest = RoleManifest("test-role", manifest_data)

        assert manifest.role == "test-role"
        assert manifest.description == ""
        assert manifest.version == "1.0"
        assert len(manifest.mandatory_files) == 1
        assert len(manifest.optional_files) == 0

    def test_parse_manifest_with_no_files(self):
        """Test parsing manifest with no auto_load_files section."""
        manifest_data = {}

        manifest = RoleManifest("test-role", manifest_data)

        assert len(manifest.mandatory_files) == 0
        assert len(manifest.optional_files) == 0
        assert manifest.get_all_paths() == []


class TestLoadRoleManifest:
    """Test load_role_manifest function."""

    def test_load_existing_manifest(self):
        """Test loading an existing manifest file."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "test-role.yaml"

            manifest_data = {
                "role": "test-role",
                "description": "Test role",
                "auto_load_files": {
                    "mandatory": [
                        {"path": "/path/to/file1.md", "reason": "Core"},
                    ],
                },
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f)

            manifest = load_role_manifest("test-role", manifest_dir)

            assert manifest is not None
            assert manifest.role == "test-role"
            assert len(manifest.mandatory_files) == 1

    def test_load_nonexistent_manifest(self):
        """Test loading a manifest that doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest = load_role_manifest("nonexistent-role", manifest_dir)

            assert manifest is None

    def test_load_invalid_yaml(self):
        """Test loading a manifest with invalid YAML."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "bad-role.yaml"

            with open(manifest_file, "w", encoding="utf-8") as f:
                f.write("invalid: yaml: content: [unclosed")

            manifest = load_role_manifest("bad-role", manifest_dir)

            assert manifest is None

    def test_load_non_dict_manifest(self):
        """Test loading a manifest that's not a dictionary."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "list-role.yaml"

            with open(manifest_file, "w", encoding="utf-8") as f:
                yaml.dump(["not", "a", "dict"], f)

            manifest = load_role_manifest("list-role", manifest_dir)

            assert manifest is None


class TestLoadRoleDocumentation:
    """Test load_role_documentation function."""

    def test_load_with_no_role(self):
        """Test loading with no role specified."""
        result = load_role_documentation(role=None, explicit_files=["/explicit/file.md"])

        assert result == ["/explicit/file.md"]

    def test_load_with_nonexistent_role(self):
        """Test loading with a role that has no manifest."""
        # When manifest doesn't exist, should return only explicit files
        result = load_role_documentation(
            role="nonexistent-role",
            explicit_files=["/explicit/file.md"],
        )

        assert result == ["/explicit/file.md"]

    def test_load_mandatory_only(self):
        """Test loading only mandatory files from manifest."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "test-role.yaml"

            manifest_data = {
                "auto_load_files": {
                    "mandatory": [
                        {"path": "/mandatory/file1.md", "reason": "Core"},
                        {"path": "/mandatory/file2.md", "reason": "Essential"},
                    ],
                    "optional": [
                        {"path": "/optional/file1.md", "reason": "Advanced"},
                    ],
                },
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f)

            # Temporarily override the default manifest directory
            import utils.role_manifest

            original_dir = utils.role_manifest.ROLE_DOCS_DIR
            utils.role_manifest.ROLE_DOCS_DIR = manifest_dir

            try:
                result = load_role_documentation(
                    role="test-role",
                    explicit_files=["/explicit/file.md"],
                    include_optional=False,
                )

                assert len(result) == 3
                assert "/mandatory/file1.md" in result
                assert "/mandatory/file2.md" in result
                assert "/explicit/file.md" in result
                assert "/optional/file1.md" not in result
            finally:
                utils.role_manifest.ROLE_DOCS_DIR = original_dir

    def test_load_with_optional(self):
        """Test loading mandatory + optional files from manifest."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "test-role.yaml"

            manifest_data = {
                "auto_load_files": {
                    "mandatory": [
                        {"path": "/mandatory/file1.md", "reason": "Core"},
                    ],
                    "optional": [
                        {"path": "/optional/file1.md", "reason": "Advanced"},
                    ],
                },
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f)

            import utils.role_manifest

            original_dir = utils.role_manifest.ROLE_DOCS_DIR
            utils.role_manifest.ROLE_DOCS_DIR = manifest_dir

            try:
                result = load_role_documentation(
                    role="test-role",
                    explicit_files=["/explicit/file.md"],
                    include_optional=True,
                )

                assert len(result) == 3
                assert "/mandatory/file1.md" in result
                assert "/optional/file1.md" in result
                assert "/explicit/file.md" in result
            finally:
                utils.role_manifest.ROLE_DOCS_DIR = original_dir

    def test_deduplication(self):
        """Test that duplicate files are removed."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "test-role.yaml"

            manifest_data = {
                "auto_load_files": {
                    "mandatory": [
                        {"path": "/shared/file.md", "reason": "Core"},
                        {"path": "/mandatory/file.md", "reason": "Essential"},
                    ],
                },
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f)

            import utils.role_manifest

            original_dir = utils.role_manifest.ROLE_DOCS_DIR
            utils.role_manifest.ROLE_DOCS_DIR = manifest_dir

            try:
                # Include the same file in explicit files
                result = load_role_documentation(
                    role="test-role",
                    explicit_files=["/shared/file.md", "/explicit/file.md"],
                    include_optional=False,
                )

                # Should deduplicate /shared/file.md
                assert len(result) == 3
                assert result.count("/shared/file.md") == 1
                assert "/mandatory/file.md" in result
                assert "/explicit/file.md" in result
            finally:
                utils.role_manifest.ROLE_DOCS_DIR = original_dir

    def test_order_preservation(self):
        """Test that file order is preserved (auto-loaded first, then explicit)."""
        with TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest_file = manifest_dir / "test-role.yaml"

            manifest_data = {
                "auto_load_files": {
                    "mandatory": [
                        {"path": "/auto/file1.md", "reason": "Core"},
                        {"path": "/auto/file2.md", "reason": "Essential"},
                    ],
                },
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f)

            import utils.role_manifest

            original_dir = utils.role_manifest.ROLE_DOCS_DIR
            utils.role_manifest.ROLE_DOCS_DIR = manifest_dir

            try:
                result = load_role_documentation(
                    role="test-role",
                    explicit_files=["/explicit/file1.md", "/explicit/file2.md"],
                    include_optional=False,
                )

                # Auto-loaded files should come before explicit files
                assert result[0] == "/auto/file1.md"
                assert result[1] == "/auto/file2.md"
                assert result[2] == "/explicit/file1.md"
                assert result[3] == "/explicit/file2.md"
            finally:
                utils.role_manifest.ROLE_DOCS_DIR = original_dir


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
