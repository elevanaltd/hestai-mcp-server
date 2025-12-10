"""Tests for clink fallback hints error messages."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.clink import CLinkTool


class TestClinkFallbackHints:
    """Test clink tool's fallback hints in error messages."""

    @pytest.fixture
    def mock_registry(self):
        """Mock clink registry with test configuration."""
        registry = MagicMock()
        registry.list_clients.return_value = ["gemini", "claude", "codex"]
        registry.list_roles.return_value = ["default", "codereviewer", "validator"]
        return registry

    @pytest.fixture
    def fallback_hints_json(self):
        """Create a test fallback_hints.json file in the expected location."""
        hints_path = Path("conf/cli_clients/fallback_hints.json")

        # Backup existing file if it exists
        backup_path = None
        if hints_path.exists():
            backup_path = hints_path.with_suffix(".json.backup")
            shutil.copy(hints_path, backup_path)

        # Ensure directory exists
        hints_path.parent.mkdir(parents=True, exist_ok=True)

        # Create test hints
        hints_data = {
            "system-steward": {
                "primary_cli": "claude",
                "primary_model": "haiku",
                "fallback_cli": "codex",
                "fallback_model": "gpt-5.1-codex-mini",
                "reason": "Requires file system access - avoids Gemini sandbox",
            },
            "holistic-orchestrator": {
                "primary_cli": "claude",
                "primary_model": "opus",
                "fallback_cli": None,
                "fallback_model": None,
                "reason": "Constitutional authority requires Claude Opus - no fallback",
            },
        }
        hints_path.write_text(json.dumps(hints_data, indent=2))

        yield hints_path

        # Cleanup: restore original or delete test file
        if backup_path and backup_path.exists():
            shutil.move(backup_path, hints_path)
        elif hints_path.exists():
            hints_path.unlink()

    @patch("tools.clink.get_registry")
    def test_error_message_with_fallback_hints(self, mock_get_registry, mock_registry, fallback_hints_json):
        """Test error message shows fallback hints when agent is unavailable."""
        mock_get_registry.return_value = mock_registry

        # Mock client config to simulate missing role on gemini
        mock_client = MagicMock()
        mock_client.name = "gemini"
        mock_client.get_role.side_effect = KeyError(
            "Role 'system-steward' not configured for CLI 'gemini'. Available roles: codereviewer, default, validator"
        )
        mock_registry.get_client.return_value = mock_client

        tool = CLinkTool()

        # Execute with unavailable agent
        import asyncio

        result = asyncio.run(
            tool.execute(
                {
                    "prompt": "Test prompt",
                    "cli_name": "gemini",
                    "role": "system-steward",
                }
            )
        )

        # Extract error message from result
        assert len(result) == 1
        result_json = json.loads(result[0].text)
        error_message = result_json["content"]

        # Verify error message contains fallback hints
        assert "Agent 'system-steward' unavailable on gemini" in error_message
        assert "→ Primary: claude (haiku)" in error_message
        assert "→ Fallback: codex (gpt-5.1-codex-mini)" in error_message
        assert "→ Reason: Requires file system access - avoids Gemini sandbox" in error_message
        assert "Available agents:" in error_message

    @patch("tools.clink.get_registry")
    def test_error_message_without_fallback(self, mock_get_registry, mock_registry, fallback_hints_json):
        """Test error message when agent has no fallback option."""
        mock_get_registry.return_value = mock_registry

        mock_client = MagicMock()
        mock_client.name = "gemini"
        mock_client.get_role.side_effect = KeyError(
            "Role 'holistic-orchestrator' not configured for CLI 'gemini'. Available roles: codereviewer, default, validator"
        )
        mock_registry.get_client.return_value = mock_client

        tool = CLinkTool()

        import asyncio

        result = asyncio.run(
            tool.execute(
                {
                    "prompt": "Test prompt",
                    "cli_name": "gemini",
                    "role": "holistic-orchestrator",
                }
            )
        )

        assert len(result) == 1
        result_json = json.loads(result[0].text)
        error_message = result_json["content"]

        # Verify shows primary but indicates no fallback
        assert "Agent 'holistic-orchestrator' unavailable on gemini" in error_message
        assert "→ Primary: claude (opus)" in error_message
        assert "→ Reason: Constitutional authority requires Claude Opus - no fallback" in error_message
        # Should NOT show fallback line when fallback_cli is null
        assert "→ Fallback: None" not in error_message or "no fallback" in error_message.lower()

    @patch("tools.clink.get_registry")
    def test_error_message_without_hints_file(self, mock_get_registry, mock_registry):
        """Test graceful degradation when fallback_hints.json doesn't exist."""
        mock_get_registry.return_value = mock_registry

        mock_client = MagicMock()
        mock_client.name = "gemini"
        mock_client.get_role.side_effect = KeyError(
            "Role 'unknown-agent' not configured for CLI 'gemini'. Available roles: codereviewer, default, validator"
        )
        mock_registry.get_client.return_value = mock_client

        # Don't use fallback_hints_json fixture - let it fail naturally
        tool = CLinkTool()

        import asyncio

        result = asyncio.run(
            tool.execute(
                {
                    "prompt": "Test prompt",
                    "cli_name": "gemini",
                    "role": "unknown-agent",
                }
            )
        )

        assert len(result) == 1
        result_json = json.loads(result[0].text)
        error_message = result_json["content"]

        # Should show basic error without hints
        assert "Agent 'unknown-agent'" in error_message
        assert "Available agents:" in error_message
        # Should NOT crash or show hint details
        assert "→ Primary:" not in error_message

    @patch("tools.clink.get_registry")
    def test_error_message_agent_not_in_hints(self, mock_get_registry, mock_registry, fallback_hints_json):
        """Test error message when agent exists but is not in hints file."""
        mock_get_registry.return_value = mock_registry

        mock_client = MagicMock()
        mock_client.name = "gemini"
        mock_client.get_role.side_effect = KeyError(
            "Role 'codereviewer' not configured for CLI 'gemini'. Available roles: default, validator"
        )
        mock_registry.get_client.return_value = mock_client

        tool = CLinkTool()

        import asyncio

        result = asyncio.run(
            tool.execute(
                {
                    "prompt": "Test prompt",
                    "cli_name": "gemini",
                    "role": "codereviewer",
                }
            )
        )

        assert len(result) == 1
        result_json = json.loads(result[0].text)
        error_message = result_json["content"]

        # Should show basic error without hints
        assert "Agent 'codereviewer'" in error_message
        assert "Available agents:" in error_message
        # Should NOT show hint details for agents not in hints
        assert "→ Primary:" not in error_message
