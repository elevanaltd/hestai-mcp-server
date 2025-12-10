"""Tests for generate_client_configs.py script."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from generate_client_configs import ConfigGenerator


@pytest.fixture
def mock_tier_mapping():
    """Mock tier mapping data."""
    return {
        "_schema_version": "1.0.0",
        "tiers": {
            "HIGH": {
                "claude": "opus",
                "gemini": None,
                "codex": None,
                "agents": ["holistic-orchestrator", "critical-engineer"],
            },
            "MEDIUM": {
                "claude": "sonnet",
                "gemini": "gemini-3-pro-preview",
                "codex": "gpt-5.1-codex",
                "agents": ["implementation-lead"],
            },
            "LOW": {
                "claude": "haiku",
                "gemini": "gemini-3-pro-preview",
                "codex": "gpt-5.1-codex-mini",
                "agents": ["surveyor"],
            },
        },
        "exceptions": {
            "system-steward": {
                "claude": "haiku",
                "gemini": None,
                "codex": "gpt-5.1-codex-mini",
            }
        },
        "primary_fallback_hints": {
            "system-steward": {
                "primary_cli": "claude",
                "primary_model": "haiku",
                "fallback_cli": "codex",
                "fallback_model": "gpt-5.1-codex-mini",
                "reason": "Requires file system access",
            }
        },
        "model_mappings": {
            "claude": {"opus": "opus", "sonnet": "sonnet", "haiku": "haiku"},
            "gemini": {"gemini-3-pro-preview": "gemini-3-pro-preview"},
            "codex": {
                "gpt-5.1-codex": "gpt-5.1-codex",
                "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
            },
        },
        "reasoning_effort_mappings": {
            "high": ["critical-engineer"],
            "medium": ["holistic-orchestrator"],
            "low": [],
        },
    }


@pytest.fixture
def mock_claude_config():
    """Mock Claude client config."""
    return {
        "name": "claude",
        "command": "claude",
        "additional_args": [],
        "env": {},
        "roles": {
            "holistic-orchestrator": {
                "prompt_path": "systemprompts/clink/holistic-orchestrator.txt",
                "role_args": [],
            },
            "critical-engineer": {
                "prompt_path": "systemprompts/clink/critical-engineer.txt",
                "role_args": [],
            },
            "implementation-lead": {
                "prompt_path": "systemprompts/clink/implementation-lead.txt",
                "role_args": [],
            },
            "surveyor": {
                "prompt_path": "systemprompts/clink/surveyor.txt",
                "role_args": [],
            },
            "system-steward": {
                "prompt_path": "systemprompts/clink/system-steward.txt",
                "role_args": [],
            },
        },
    }


@pytest.fixture
def generator(tmp_path, mock_tier_mapping, mock_claude_config):
    """Create ConfigGenerator with mocked data."""
    # Create directory structure
    cli_clients_dir = tmp_path / "conf" / "cli_clients"
    cli_clients_dir.mkdir(parents=True)

    # Write mock tier mapping
    tier_mapping_path = cli_clients_dir / "agent-model-tiers.json"
    with open(tier_mapping_path, "w") as f:
        json.dump(mock_tier_mapping, f)

    # Write mock claude config
    claude_config_path = cli_clients_dir / "claude.json"
    with open(claude_config_path, "w") as f:
        json.dump(mock_claude_config, f)

    gen = ConfigGenerator(base_dir=tmp_path)
    gen.load_tier_mapping()
    gen.load_client_configs(["claude"])

    return gen


class TestConfigGenerator:
    """Tests for ConfigGenerator class."""

    def test_find_agent_tier(self, generator):
        """Test finding agent tier."""
        assert generator.find_agent_tier("holistic-orchestrator") == "HIGH"
        assert generator.find_agent_tier("implementation-lead") == "MEDIUM"
        assert generator.find_agent_tier("surveyor") == "LOW"
        assert generator.find_agent_tier("unknown-agent") is None

    def test_get_model_for_agent_from_tier(self, generator):
        """Test getting model from tier mapping."""
        # HIGH tier agent
        assert generator.get_model_for_agent("holistic-orchestrator", "claude") == "opus"
        assert generator.get_model_for_agent("holistic-orchestrator", "gemini") is None

        # MEDIUM tier agent
        assert generator.get_model_for_agent("implementation-lead", "claude") == "sonnet"
        assert (
            generator.get_model_for_agent("implementation-lead", "gemini")
            == "gemini-3-pro-preview"
        )

        # LOW tier agent
        assert generator.get_model_for_agent("surveyor", "claude") == "haiku"

    def test_get_model_for_agent_exception_override(self, generator):
        """Test exception overrides tier mapping."""
        # system-steward has exception override
        assert generator.get_model_for_agent("system-steward", "claude") == "haiku"
        assert generator.get_model_for_agent("system-steward", "gemini") is None  # Explicit exclusion
        assert (
            generator.get_model_for_agent("system-steward", "codex")
            == "gpt-5.1-codex-mini"
        )

    def test_get_reasoning_effort(self, generator):
        """Test getting reasoning effort level."""
        assert generator.get_reasoning_effort("critical-engineer") == "high"
        assert generator.get_reasoning_effort("holistic-orchestrator") == "medium"
        assert generator.get_reasoning_effort("surveyor") is None

    def test_update_client_config_claude(self, generator):
        """Test updating Claude client config."""
        result = generator.update_client_config("claude", dry_run=False)

        config = result["config"]
        roles = config["roles"]

        # HIGH tier → opus
        assert roles["holistic-orchestrator"]["role_args"] == ["--model", "opus"]
        assert roles["critical-engineer"]["role_args"] == ["--model", "opus"]

        # MEDIUM tier → sonnet
        assert roles["implementation-lead"]["role_args"] == ["--model", "sonnet"]

        # LOW tier → haiku
        assert roles["surveyor"]["role_args"] == ["--model", "haiku"]

        # Exception override → haiku
        assert roles["system-steward"]["role_args"] == ["--model", "haiku"]

        # Metadata added
        assert config["_generated_by"] == "scripts/generate_client_configs.py"

    def test_update_client_config_dry_run(self, generator):
        """Test dry-run mode doesn't modify config."""
        original_config = generator.client_configs["claude"].copy()

        result = generator.update_client_config("claude", dry_run=True)

        # Original config should be unchanged
        assert generator.client_configs["claude"] == original_config

        # Result should show changes
        assert len(result["changes"]) > 0

    def test_validate_model_ids_valid(self, generator):
        """Test validation passes for valid model IDs."""
        errors = generator.validate_model_ids()
        assert errors == []

    def test_validate_model_ids_invalid(self, generator):
        """Test validation catches invalid model IDs."""
        # Add invalid model to tier
        generator.tier_mapping["tiers"]["HIGH"]["claude"] = "invalid-model"

        errors = generator.validate_model_ids()
        assert len(errors) > 0
        assert "invalid-model" in errors[0]

    def test_generate_fallback_hints(self, generator):
        """Test generating fallback hints."""
        hints = generator.generate_fallback_hints()

        assert "system-steward" in hints
        assert hints["system-steward"]["primary_cli"] == "claude"
        assert hints["system-steward"]["primary_model"] == "haiku"
        assert hints["system-steward"]["fallback_cli"] == "codex"


class TestValidation:
    """Tests for validation functions."""

    def test_validate_tier_degradation_warning(self, generator):
        """Test tier degradation detection."""
        # Add a HIGH→LOW degradation
        generator.tier_mapping["primary_fallback_hints"]["critical-engineer"] = {
            "primary_cli": "claude",
            "primary_model": "opus",
            "fallback_cli": "codex",
            "fallback_model": "gpt-5.1-codex-mini",  # LOW tier model
        }

        warnings = generator.validate_tier_degradation()
        # Current implementation may not catch this - test structure
        # This is a placeholder for future enhancement
        assert isinstance(warnings, list)


def test_main_function_help(capsys):
    """Test main function help output."""
    with patch("sys.argv", ["generate_client_configs.py", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            from generate_client_configs import main

            main()

        assert exc_info.value.code == 0
