"""
Tests for TestGuard tool - validating test methodology guardian functionality

This module contains unit tests to ensure that the TestGuard tool
properly detects test manipulation anti-patterns and enforces testing integrity.
"""

import pytest

from tools.testguard import RequirementsRequest, RequirementsTool


class TestTestGuardTool:
    """Test suite for TestGuard tool"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool = RequirementsTool()

    def test_tool_metadata(self):
        """Test that tool metadata matches requirements"""
        assert self.tool.get_name() == "testguard"
        assert "Test Methodology Guardian" in self.tool.get_description()
        assert "test manipulation anti-patterns" in self.tool.get_description()
        assert "Quality gate" in self.tool.get_description()

    def test_tool_configuration(self):
        """Test tool configuration and requirements"""
        assert self.tool.requires_model() is True
        assert self.tool.get_default_temperature() == 0.2  # TEMPERATURE_ANALYTICAL
        assert self.tool.get_default_model() == "google/gemini-2.5-pro"

    def test_model_category(self):
        """Test that tool uses balanced model category"""
        from tools.models import ToolModelCategory

        assert self.tool.get_model_category() == ToolModelCategory.BALANCED

    def test_request_model_validation(self):
        """Test that request model accepts valid inputs"""
        # Valid request
        request = RequirementsRequest(prompt="Let's skip this failing test")
        assert request.prompt == "Let's skip this failing test"

        # Empty prompt should raise validation error
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RequirementsRequest()

    def test_input_schema_model_restrictions(self):
        """Test that input schema restricts to high-quality models only"""
        schema = self.tool.get_input_schema()

        # Should have model property with restricted enum
        assert "properties" in schema
        assert "model" in schema["properties"]

        model_config = schema["properties"]["model"]
        assert model_config["type"] == "string"
        assert "enum" in model_config
        assert "google/gemini-2.5-pro" in model_config["enum"]
        assert "gpt-4.1-2025-04-14" in model_config["enum"]
        # Should only have these two high-quality models
        assert len(model_config["enum"]) == 2

    async def test_prepare_prompt_formatting(self):
        """Test that prompt preparation includes test guard analysis structure"""
        request = RequirementsRequest(prompt="Maybe we should lower the coverage threshold")

        prompt = await self.tool.prepare_prompt(request)

        # Should include the analysis framework
        assert "TEST METHODOLOGY ANALYSIS REQUIRED" in prompt
        assert "DETECT:" in prompt
        assert "ANALYZE:" in prompt
        assert "EDUCATE:" in prompt
        assert "REDIRECT:" in prompt
        assert "ENFORCE:" in prompt
        assert request.prompt in prompt
        assert "Are we fixing the code or hiding the problem?" in prompt

    def test_format_response_structure(self):
        """Test response formatting includes guardian branding"""
        request = RequirementsRequest(prompt="Let's comment out this test")
        mock_response = "INTERVENTION: [IMMEDIATE_HALT] - Test manipulation detected"

        formatted = self.tool.format_response(mock_response, request)

        assert "TEST METHODOLOGY GUARDIAN ANALYSIS" in formatted
        assert mock_response in formatted
        assert "Guardian Protocol" in formatted
        assert "Truth over convenience" in formatted

    def test_system_prompt_contains_anti_patterns(self):
        """Test that system prompt defines key anti-patterns to detect"""
        system_prompt = self.tool.get_system_prompt()

        # Should define the guardian role
        assert "Test Methodology Guardian" in system_prompt
        assert "quality gate" in system_prompt

        # Should list anti-patterns to detect
        assert "Modifying assertions to match broken code" in system_prompt
        assert "Reducing coverage to avoid failures" in system_prompt
        assert "Adding workarounds instead of fixes" in system_prompt
        assert "Commenting out failing tests" in system_prompt

        # Should include core principles
        assert "TRUTH OVER CONVENIENCE" in system_prompt
        assert "Tests reveal reality, not confirm wishes" in system_prompt

    def test_trigger_pattern_examples(self):
        """Test that description includes comprehensive trigger patterns"""
        description = self.tool.get_description()

        # Should include automatic invocation triggers
        assert "MANDATORY AUTOMATIC INVOCATION" in description
        assert "fixing the test" in description
        assert "adjusting expectations" in description
        assert "simpler test" in description
        assert "workaround" in description

        # Should include trigger patterns
        assert "TRIGGER PATTERNS" in description
        assert "skip this test" in description
        assert "comment out" in description
        assert "lower the bar" in description

    @pytest.mark.parametrize(
        "prompt_text,expected_concern",
        [
            ("Let's skip this failing test", "skip"),
            ("Maybe we should adjust our expectations", "adjust"),
            ("I'll comment out this test for now", "comment"),
            ("Let's try a simpler test approach", "simpler"),
            ("We need to lower the coverage threshold", "lower"),
        ],
    )
    def test_anti_pattern_detection_scenarios(self, prompt_text, expected_concern):
        """Test various anti-pattern scenarios that should trigger intervention"""
        request = RequirementsRequest(prompt=prompt_text)

        # Verify request is valid for different anti-pattern phrases
        assert request.prompt == prompt_text
        assert expected_concern.lower() in prompt_text.lower()

    def test_tool_fields_configuration(self):
        """Test tool field definitions"""
        fields = self.tool.get_tool_fields()

        assert "prompt" in fields
        assert fields["prompt"]["type"] == "string"
        assert "complete context" in fields["prompt"]["description"]

    def test_required_fields(self):
        """Test required field validation"""
        required = self.tool.get_required_fields()

        assert "prompt" in required
        assert len(required) == 1

    def test_model_selection_fallback(self):
        """Test model selection logic with fallback"""
        # Should prefer gemini-2.5-pro but allow gpt-4.1 fallback
        default_model = self.tool.get_default_model()
        assert default_model == "google/gemini-2.5-pro"

        # Schema should allow both models
        schema = self.tool.get_input_schema()
        allowed_models = schema["properties"]["model"]["enum"]
        assert "google/gemini-2.5-pro" in allowed_models
        assert "gpt-4.1-2025-04-14" in allowed_models

    def test_integration_with_test_methodology_protocol(self):
        """Test integration with external test methodology guardian protocol"""
        description = self.tool.get_description()

        # Should reference the external protocol file
        assert "/Users/shaunbuswell/.claude/agents/test-methodology-guardian.oct.md" in description

        # Should explain the role relationship
        assert "enforces the test-methodology-guardian protocol" in description


class TestTestGuardIntegration:
    """Integration tests for TestGuard tool in context"""

    def setup_method(self):
        """Set up integration test fixtures"""
        self.tool = RequirementsTool()

    async def test_end_to_end_prompt_flow(self):
        """Test complete prompt preparation and formatting flow"""
        # Simulate a concerning test manipulation request
        request = RequirementsRequest(prompt="This test is failing, let's just adjust the assertion to make it pass")

        # Prepare the prompt
        prepared = await self.tool.prepare_prompt(request)

        # Verify the prepared prompt has all required elements
        assert "TEST METHODOLOGY ANALYSIS REQUIRED" in prepared
        assert request.prompt in prepared
        assert "test manipulation anti-patterns" in prepared

        # Simulate a response and format it
        mock_ai_response = (
            "INTERVENTION: [IMMEDIATE_HALT]\n"
            "ANALYSIS: Detected assertion modification anti-pattern\n"
            "EDUCATION: This violates test integrity principles\n"
            "REDIRECT: Fix the underlying code issue instead\n"
            "ENFORCEMENT: Acknowledge before proceeding"
        )

        formatted = self.tool.format_response(mock_ai_response, request)

        # Verify formatting preserves content and adds guardian branding
        assert mock_ai_response in formatted
        assert "TEST METHODOLOGY GUARDIAN ANALYSIS" in formatted
        assert "Guardian Protocol" in formatted

    def test_quality_gate_behavior_simulation(self):
        """Test that tool behaves as expected quality gate"""
        # Should be configured for immediate, authoritative responses
        assert self.tool.get_default_temperature() == 0.2  # Low temperature for consistency
        assert self.tool.requires_model() is True  # Needs AI for pattern detection

        # Should use high-quality models for reliable analysis
        default_model = self.tool.get_default_model()
        assert default_model in ["google/gemini-2.5-pro", "gpt-4.1-2025-04-14"]
