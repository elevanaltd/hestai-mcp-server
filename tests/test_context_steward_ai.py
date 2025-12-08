"""Tests for Context Steward AI integration module.

Tests AI-driven task execution via clink delegation with configuration-driven
prompt templates and graceful degradation.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Module to test - this will fail until we implement it
from tools.context_steward.ai import ContextStewardAI


class TestContextStewardAIConfig:
    """Test configuration loading and caching."""

    def test_load_config_success(self, tmp_path):
        """FAILING TEST: Should load valid configuration from conf/context_steward.json"""
        # Arrange: Create valid config
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {
            "version": "1.0.0",
            "enabled": True,
            "default_cli": "gemini",
            "tasks": {
                "session_compression": {
                    "enabled": True,
                    "cli": "gemini",
                    "role": "system-steward",
                }
            },
        }
        config_file.write_text(json.dumps(config_data))

        # Act: Load config
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            config = ai.load_config()

        # Assert: Config loaded correctly
        assert config["version"] == "1.0.0"
        assert config["enabled"] is True
        assert config["default_cli"] == "gemini"
        assert "session_compression" in config["tasks"]

    def test_load_config_missing_file(self, tmp_path):
        """FAILING TEST: Should raise FileNotFoundError for missing config"""
        # Arrange: Point to non-existent config
        config_file = tmp_path / "missing_config.json"

        # Act & Assert: Should raise
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            with pytest.raises(FileNotFoundError):
                ai = ContextStewardAI()
                ai.load_config()

    def test_load_config_invalid_json(self, tmp_path):
        """FAILING TEST: Should raise ValueError for malformed JSON"""
        # Arrange: Create malformed config
        config_file = tmp_path / "bad_config.json"
        config_file.write_text("{ invalid json }")

        # Act & Assert: Should raise
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            with pytest.raises(ValueError):
                ai = ContextStewardAI()
                ai.load_config()

    def test_load_config_caching(self, tmp_path):
        """FAILING TEST: Should cache config and not reload on subsequent calls"""
        # Arrange: Create config
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {"version": "1.0.0", "enabled": True, "tasks": {}}
        config_file.write_text(json.dumps(config_data))

        # Act: Load config twice
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            config1 = ai.load_config()
            config2 = ai.load_config()

        # Assert: Same object (cached)
        assert config1 is config2


class TestContextStewardAITaskEnabled:
    """Test task enabled checks."""

    def test_is_task_enabled_true(self, tmp_path):
        """FAILING TEST: Should return True for enabled task"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {
            "enabled": True,
            "tasks": {"session_compression": {"enabled": True}},
        }
        config_file.write_text(json.dumps(config_data))

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            result = ai.is_task_enabled("session_compression")

        # Assert
        assert result is True

    def test_is_task_enabled_false_task_disabled(self, tmp_path):
        """FAILING TEST: Should return False when task.enabled = false"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {
            "enabled": True,
            "tasks": {"session_compression": {"enabled": False}},
        }
        config_file.write_text(json.dumps(config_data))

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            result = ai.is_task_enabled("session_compression")

        # Assert
        assert result is False

    def test_is_task_enabled_false_global_disabled(self, tmp_path):
        """FAILING TEST: Should return False when global enabled = false"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {
            "enabled": False,  # Global disable
            "tasks": {"session_compression": {"enabled": True}},
        }
        config_file.write_text(json.dumps(config_data))

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            result = ai.is_task_enabled("session_compression")

        # Assert
        assert result is False

    def test_is_task_enabled_missing_task(self, tmp_path):
        """FAILING TEST: Should return False for non-existent task"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {"enabled": True, "tasks": {}}
        config_file.write_text(json.dumps(config_data))

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            result = ai.is_task_enabled("nonexistent_task")

        # Assert
        assert result is False


class TestContextStewardAIBuildPrompt:
    """Test prompt template loading and variable substitution."""

    def test_build_prompt_success(self, tmp_path):
        """FAILING TEST: Should build prompt from template with variables"""
        # Arrange: Create config and template
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        template_dir = tmp_path / "systemprompts" / "context_steward"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "test_task.txt"
        template_file.write_text("Session: {{session_id}}\nRole: {{role}}")

        config_data = {
            "enabled": True,
            "tasks": {
                "test_task": {
                    "enabled": True,
                    "prompt_template": str(template_file),
                }
            },
        }
        config_file.write_text(json.dumps(config_data))

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            prompt = ai.build_prompt("test_task", session_id="abc123", role="implementation-lead")

        # Assert
        assert "Session: abc123" in prompt
        assert "Role: implementation-lead" in prompt

    def test_build_prompt_missing_template(self, tmp_path):
        """FAILING TEST: Should raise FileNotFoundError for missing template"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {
            "enabled": True,
            "tasks": {"test_task": {"enabled": True, "prompt_template": "/nonexistent/template.txt"}},
        }
        config_file.write_text(json.dumps(config_data))

        # Act & Assert
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            with pytest.raises(FileNotFoundError):
                ai.build_prompt("test_task", session_id="abc123")

    def test_build_prompt_missing_variable(self, tmp_path):
        """FAILING TEST: Should handle missing variables gracefully"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        template_dir = tmp_path / "systemprompts" / "context_steward"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "test_task.txt"
        template_file.write_text("Session: {{session_id}}\nRole: {{role}}")

        config_data = {
            "enabled": True,
            "tasks": {"test_task": {"enabled": True, "prompt_template": str(template_file)}},
        }
        config_file.write_text(json.dumps(config_data))

        # Act: Missing 'role' variable
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            prompt = ai.build_prompt("test_task", session_id="abc123")

        # Assert: Should leave placeholder or raise
        # Implementation decision: leave {{role}} or raise KeyError
        assert "{{role}}" in prompt or "role" not in prompt


class TestContextStewardAIRunTask:
    """Test end-to-end task execution via clink."""

    @pytest.mark.asyncio
    async def test_run_task_success(self, tmp_path):
        """FAILING TEST: Should execute task via clink and parse XML response"""
        # Arrange: Mock clink response
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        template_dir = tmp_path / "systemprompts" / "context_steward"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "session_compression.txt"
        template_file.write_text("Compress session: {{session_id}}")

        config_data = {
            "enabled": True,
            "default_cli": "gemini",
            "tasks": {
                "session_compression": {
                    "enabled": True,
                    "cli": "gemini",
                    "role": "system-steward",
                    "prompt_template": str(template_file),
                }
            },
        }
        config_file.write_text(json.dumps(config_data))

        # Mock clink execution with OCTAVE response
        mock_octave_response = """RESPONSE::[
  STATUS::success,
  SUMMARY::"Session compressed successfully",
  FILES_ANALYZED::["transcript.jsonl"],
  CHANGES::[
    "Compressed session into OCTAVE format",
    "Extracted 1 decision"
  ],
  ARTIFACTS::[
    {type::session_compression, path::".hestai/sessions/archive/abc123-octave.oct.md", action::created}
  ]
]"""

        mock_clink = AsyncMock()
        mock_clink.execute.return_value = [
            Mock(text=json.dumps({"status": "success", "content": mock_octave_response}))
        ]

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            with patch("tools.context_steward.ai.CLinkTool", return_value=mock_clink):
                ai = ContextStewardAI()
                result = await ai.run_task("session_compression", session_id="abc123")

        # Assert
        assert result["status"] == "success"
        assert result["summary"] == "Session compressed successfully"
        assert len(result["artifacts"]) > 0
        assert result["artifacts"][0]["type"] == "session_compression"

    @pytest.mark.asyncio
    async def test_run_task_disabled(self, tmp_path):
        """FAILING TEST: Should skip execution if task disabled"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        config_data = {
            "enabled": True,
            "tasks": {"session_compression": {"enabled": False}},
        }
        config_file.write_text(json.dumps(config_data))

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            ai = ContextStewardAI()
            result = await ai.run_task("session_compression", session_id="abc123")

        # Assert
        assert result["status"] == "skipped"
        assert "disabled" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_run_task_clink_error(self, tmp_path):
        """FAILING TEST: Should handle clink errors gracefully"""
        # Arrange
        config_dir = tmp_path / "conf"
        config_dir.mkdir()
        config_file = config_dir / "context_steward.json"
        template_dir = tmp_path / "systemprompts" / "context_steward"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "session_compression.txt"
        template_file.write_text("Compress session")

        config_data = {
            "enabled": True,
            "default_cli": "gemini",
            "tasks": {
                "session_compression": {
                    "enabled": True,
                    "cli": "gemini",
                    "role": "system-steward",
                    "prompt_template": str(template_file),
                }
            },
        }
        config_file.write_text(json.dumps(config_data))

        # Mock clink failure
        mock_clink = AsyncMock()
        mock_clink.execute.side_effect = Exception("Clink execution failed")

        # Act
        with patch("tools.context_steward.ai.CONFIG_FILE", config_file):
            with patch("tools.context_steward.ai.CLinkTool", return_value=mock_clink):
                ai = ContextStewardAI()
                result = await ai.run_task("session_compression", session_id="abc123")

        # Assert: Graceful degradation
        assert result["status"] == "error"
        assert "error" in result or "exception" in result
