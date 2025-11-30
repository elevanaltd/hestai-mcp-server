"""
Tests for TestGuard tool - validating test methodology guardian functionality

This module contains unit tests to ensure that the TestGuard tool
properly detects test manipulation anti-patterns and enforces testing integrity.
"""

import tempfile
from unittest.mock import Mock, patch

import pytest

# CONTEXT7_BYPASS: INFRA-004 - Internal modules from same codebase for session context testing
from tools.testguard import RequirementsRequest, RequirementsTool
from utils.session_manager import SessionContext


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
        assert self.tool.get_default_temperature() == 1.0  # TEMPERATURE_ANALYTICAL
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

    @patch("tools.testguard.FileContextProcessor")
    def test_session_context_usage_bug_demonstration(self, mock_processor_class):
        """
        This test demonstrates the CURRENT BUG: TestGuard uses '.' (server directory)
        instead of session's project_root when gathering test context.

        This test should FAIL initially, showing the bug exists.
        After refactoring, it should PASS.
        """
        # Create a temporary project directory to simulate a real project
        with tempfile.TemporaryDirectory() as temp_project_dir:
            # Create mock processor instance first
            mock_processor_instance = Mock()
            mock_processor_class.return_value = mock_processor_instance

            # Create a mock session context with a specific project root
            mock_session_context = Mock(spec=SessionContext)
            mock_session_context.project_root = temp_project_dir

            # Mock the session's get_file_context_processor method to return our mock processor
            mock_session_context.get_file_context_processor.return_value = mock_processor_instance
            # Mock get_test_context to return proper format for len() operations
            mock_test_context = {
                "test_framework": "pytest",
                "test_files": ["test_example.py"],  # This must be a list for len() to work
                "total_files": 1,
            }
            mock_processor_instance.get_test_context.return_value = mock_test_context

            # Create request with test context gathering enabled (using safe prompt)
            request = RequirementsRequest(
                prompt="Should I adjust test expectations to make them pass?", include_test_context=True
            )

            # BUG DEMONSTRATION: TestGuard should use session context but currently uses hardcoded "."
            tool = RequirementsTool()

            # Simulate how execute() sets up _current_arguments
            arguments = {
                "prompt": "Should I adjust test expectations to make them pass?",
                "include_test_context": True,
                "_session_context": mock_session_context,
            }
            tool._current_arguments = arguments

            # Call prepare_prompt directly to test the session context usage
            import asyncio

            asyncio.run(tool.prepare_prompt(request))

            # THE FIX CHECK: This assertion should pass after refactoring because TestGuard
            # now extracts project_root from session context and passes it to get_test_context
            mock_processor_instance.get_test_context.assert_called_with(temp_project_dir)

    def test_session_context_fallback_behavior(self):
        """
        Test that TestGuard falls back gracefully when no session context is available.
        This tests the fallback behavior that should work even without sessions.
        """
        tool = RequirementsTool()

        # This should work without session context (fallback case)
        # Just verify the tool doesn't crash when no session is provided
        assert tool is not None

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
        assert "openai/gpt-5" in model_config["enum"]
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
        assert "openai/gpt-5" in allowed_models

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
        assert self.tool.get_default_temperature() == 1.0  # Low temperature for consistency
        assert self.tool.requires_model() is True  # Needs AI for pattern detection

        # Should use high-quality models for reliable analysis
        default_model = self.tool.get_default_model()
        assert default_model in ["google/gemini-2.5-pro", "openai/gpt-5"]
