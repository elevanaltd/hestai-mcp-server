"""
Test suite for scripts/generate_client_configs.py

Tests YAML-based agent routing configuration generation.
RED phase - these tests will fail until implementation exists.
"""

import json
from pathlib import Path

import pytest


class TestYAMLLoading:
    """Test YAML configuration loading."""

    def test_load_valid_yaml(self):
        """Should load valid agent-routing.yaml file."""
        from scripts.generate_client_configs import load_yaml

        yaml_path = Path(__file__).parent.parent / "conf" / "agent-routing.yaml"
        config = load_yaml(str(yaml_path))

        assert "schema_version" in config
        assert "agents" in config
        assert "defaults" in config

    def test_load_missing_file_raises_error(self):
        """Should raise FileNotFoundError for missing file."""
        from scripts.generate_client_configs import load_yaml

        with pytest.raises(FileNotFoundError):
            load_yaml("/nonexistent/file.yaml")


class TestClaudeGeneration:
    """Test Claude config generation from YAML."""

    @pytest.fixture
    def yaml_config(self):
        """Minimal YAML config for testing."""
        return {
            "schema_version": "2.0.0",
            "defaults": {"claude": "sonnet"},
            "agents": {
                "test-opus": {"claude": "opus", "primary": "claude"},
                "test-sonnet": {"claude": "sonnet", "primary": "claude"},
                "test-haiku": {"claude": "haiku", "primary": "claude"},
                "test-excluded": {"claude": None, "primary": "codex"},
                "test-override": {
                    "claude": "haiku",
                    "primary": "claude",
                    "prompt_override": {"claude": "custom.txt"},
                },
            },
        }

    def test_generate_claude_structure(self, yaml_config):
        """Should generate Claude config with required structure."""
        from scripts.generate_client_configs import generate_claude

        config = generate_claude(yaml_config)

        assert config["name"] == "claude"
        assert config["command"] == "claude"
        assert "roles" in config
        assert isinstance(config["roles"], dict)

    def test_claude_opus_role(self, yaml_config):
        """Should generate role with --model opus."""
        from scripts.generate_client_configs import generate_claude

        config = generate_claude(yaml_config)

        assert "test-opus" in config["roles"]
        role = config["roles"]["test-opus"]
        assert role["prompt_path"] == "systemprompts/clink/test-opus.txt"
        assert role["role_args"] == ["--model", "opus"]

    def test_claude_excludes_null(self, yaml_config):
        """Should exclude agents where claude: null."""
        from scripts.generate_client_configs import generate_claude

        config = generate_claude(yaml_config)

        assert "test-excluded" not in config["roles"]

    def test_claude_prompt_override(self, yaml_config):
        """Should use prompt_override when specified."""
        from scripts.generate_client_configs import generate_claude

        config = generate_claude(yaml_config)

        role = config["roles"]["test-override"]
        assert role["prompt_path"] == "systemprompts/clink/custom.txt"


class TestCodexGeneration:
    """Test Codex config generation from YAML."""

    @pytest.fixture
    def yaml_config(self):
        """Minimal YAML config for testing."""
        return {
            "schema_version": "2.0.0",
            "defaults": {"codex": "gpt-5.1-codex"},
            "agents": {
                "test-basic": {"codex": "gpt-5.1-codex", "primary": "codex"},
                "test-reasoning-high": {
                    "codex": "gpt-5.1-codex",
                    "reasoning_effort": "high",
                    "primary": "codex",
                },
                "test-reasoning-medium": {
                    "codex": "gpt-5.1-codex",
                    "reasoning_effort": "medium",
                    "primary": "codex",
                },
                "test-excluded": {"codex": None, "primary": "claude"},
            },
        }

    def test_generate_codex_structure(self, yaml_config):
        """Should generate Codex config with required structure."""
        from scripts.generate_client_configs import generate_codex

        config = generate_codex(yaml_config)

        assert config["name"] == "codex"
        assert config["command"] == "codex"
        assert "roles" in config

    def test_codex_reasoning_high(self, yaml_config):
        """Should add -c model_reasoning_effort=high."""
        from scripts.generate_client_configs import generate_codex

        config = generate_codex(yaml_config)

        role = config["roles"]["test-reasoning-high"]
        assert role["role_args"] == ["-c", "model_reasoning_effort=high"]

    def test_codex_reasoning_medium(self, yaml_config):
        """Should add -c model_reasoning_effort=medium."""
        from scripts.generate_client_configs import generate_codex

        config = generate_codex(yaml_config)

        role = config["roles"]["test-reasoning-medium"]
        assert role["role_args"] == ["-c", "model_reasoning_effort=medium"]

    def test_codex_no_reasoning(self, yaml_config):
        """Should have empty role_args when no reasoning_effort."""
        from scripts.generate_client_configs import generate_codex

        config = generate_codex(yaml_config)

        role = config["roles"]["test-basic"]
        assert role["role_args"] == []

    def test_codex_excludes_null(self, yaml_config):
        """Should exclude agents where codex: null."""
        from scripts.generate_client_configs import generate_codex

        config = generate_codex(yaml_config)

        assert "test-excluded" not in config["roles"]


class TestGeminiGeneration:
    """Test Gemini config generation from YAML."""

    @pytest.fixture
    def yaml_config(self):
        """Minimal YAML config for testing."""
        return {
            "schema_version": "2.0.0",
            "defaults": {"gemini": "gemini-3-pro-preview"},
            "agents": {
                "test-pro": {"gemini": "gemini-3-pro-preview", "primary": "gemini"},
                "test-flash": {"gemini": "gemini-2.5-flash", "primary": "gemini"},
                "test-excluded": {"gemini": None, "primary": "claude"},
            },
        }

    def test_generate_gemini_structure(self, yaml_config):
        """Should generate Gemini config with required structure."""
        from scripts.generate_client_configs import generate_gemini

        config = generate_gemini(yaml_config)

        assert config["name"] == "gemini"
        assert config["command"] == "gemini"
        assert "roles" in config

    def test_gemini_model_args(self, yaml_config):
        """Should add --model <model> to role_args."""
        from scripts.generate_client_configs import generate_gemini

        config = generate_gemini(yaml_config)

        pro_role = config["roles"]["test-pro"]
        assert pro_role["role_args"] == ["--model", "gemini-3-pro-preview"]

        flash_role = config["roles"]["test-flash"]
        assert flash_role["role_args"] == ["--model", "gemini-2.5-flash"]

    def test_gemini_excludes_null(self, yaml_config):
        """Should exclude agents where gemini: null."""
        from scripts.generate_client_configs import generate_gemini

        config = generate_gemini(yaml_config)

        assert "test-excluded" not in config["roles"]


class TestIntegration:
    """Integration tests with actual agent-routing.yaml."""

    def test_loads_actual_yaml(self):
        """Should successfully load conf/agent-routing.yaml."""
        from scripts.generate_client_configs import load_yaml

        yaml_path = Path(__file__).parent.parent / "conf" / "agent-routing.yaml"
        config = load_yaml(str(yaml_path))

        assert config["schema_version"] == "2.0.0"
        assert "holistic-orchestrator" in config["agents"]

    def test_critical_engineer_all_clis(self):
        """Should generate critical-engineer for all CLIs."""
        from scripts.generate_client_configs import (
            generate_claude,
            generate_codex,
            generate_gemini,
            load_yaml,
        )

        yaml_path = Path(__file__).parent.parent / "conf" / "agent-routing.yaml"
        config = load_yaml(str(yaml_path))

        claude = generate_claude(config)
        codex = generate_codex(config)
        gemini = generate_gemini(config)

        assert "critical-engineer" in claude["roles"]
        assert "critical-engineer" in codex["roles"]
        assert "critical-engineer" in gemini["roles"]

        # Verify model assignments
        assert "opus" in claude["roles"]["critical-engineer"]["role_args"]
        assert "-c" in codex["roles"]["critical-engineer"]["role_args"]

    def test_system_steward_gemini_exclusion(self):
        """Should exclude system-steward from Gemini (null in YAML)."""
        from scripts.generate_client_configs import generate_gemini, load_yaml

        yaml_path = Path(__file__).parent.parent / "conf" / "agent-routing.yaml"
        config = load_yaml(str(yaml_path))

        gemini = generate_gemini(config)

        assert "system-steward" not in gemini["roles"]

    def test_holistic_orchestrator_claude_only(self):
        """Should only generate holistic-orchestrator for Claude."""
        from scripts.generate_client_configs import (
            generate_claude,
            generate_codex,
            generate_gemini,
            load_yaml,
        )

        yaml_path = Path(__file__).parent.parent / "conf" / "agent-routing.yaml"
        config = load_yaml(str(yaml_path))

        claude = generate_claude(config)
        codex = generate_codex(config)
        gemini = generate_gemini(config)

        assert "holistic-orchestrator" in claude["roles"]
        assert "holistic-orchestrator" not in codex["roles"]
        assert "holistic-orchestrator" not in gemini["roles"]

    def test_generated_configs_valid_json(self):
        """Should generate valid JSON for all CLIs."""
        from scripts.generate_client_configs import (
            generate_claude,
            generate_codex,
            generate_gemini,
            load_yaml,
        )

        yaml_path = Path(__file__).parent.parent / "conf" / "agent-routing.yaml"
        config = load_yaml(str(yaml_path))

        claude = generate_claude(config)
        codex = generate_codex(config)
        gemini = generate_gemini(config)

        # Should serialize to JSON without error
        json.dumps(claude)
        json.dumps(codex)
        json.dumps(gemini)

        # Should have roles
        assert len(claude["roles"]) > 0
        assert len(codex["roles"]) > 0
        assert len(gemini["roles"]) > 0
