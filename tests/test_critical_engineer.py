"""
Tests for Critical Engineer tool - validating technical design validation functionality

This module contains unit tests to ensure that the Critical Engineer tool
properly validates technical designs and identifies failure modes.
"""


import pytest

from tools.critical_engineer import CriticalEngineerRequest, CriticalEngineerTool


class TestCriticalEngineerTool:
    """Test suite for Critical Engineer tool"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool = CriticalEngineerTool()

    def test_tool_metadata(self):
        """Test that tool metadata matches requirements"""
        assert self.tool.get_name() == "critical-engineer"
        assert "Critical Engineer" in self.tool.get_description()
        assert "technical designs" in self.tool.get_description()
        assert "implementation decisions" in self.tool.get_description()

    def test_tool_configuration(self):
        """Test tool configuration and requirements"""
        assert self.tool.requires_model() is True
        assert self.tool.get_default_temperature() == 0.2  # TEMPERATURE_ANALYTICAL
        assert self.tool.get_default_model() == "gemini-2.5-pro"

    def test_model_category(self):
        """Test that tool uses analytical model category"""
        from tools.models import ToolModelCategory

        assert self.tool.get_model_category() == ToolModelCategory.ANALYTICAL

    def test_request_model_validation(self):
        """Test that request model accepts valid inputs"""
        # Valid request
        request = CriticalEngineerRequest(prompt="Should I use microservices or monolith?")
        assert request.prompt == "Should I use microservices or monolith?"

        # Empty prompt should raise validation error
        with pytest.raises(Exception):
            CriticalEngineerRequest()

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

    def test_allowed_models_configuration(self):
        """Test that allowed models are properly configured"""
        allowed_models = self.tool.get_allowed_models()

        assert allowed_models is not None
        assert "google/gemini-2.5-pro" in allowed_models
        assert "openai/gpt-5" in allowed_models
        assert len(allowed_models) == 2

    async def test_prepare_prompt_formatting(self):
        """Test that prompt preparation includes validation analysis structure"""
        request = CriticalEngineerRequest(prompt="Is this database architecture scalable?")

        prompt = await self.tool.prepare_prompt(request)

        # Should include the validation framework
        assert "CRITICAL ENGINEERING VALIDATION REQUIRED" in prompt
        assert "UNDERSTAND:" in prompt
        assert "STRESS_TEST:" in prompt
        assert "IDENTIFY_GAPS:" in prompt
        assert "VALIDATE:" in prompt
        assert "RECOMMEND:" in prompt
        assert request.prompt in prompt
        assert "What will break this in production?" in prompt

        # Should include critical lenses
        assert "Scalability:" in prompt
        assert "Reliability:" in prompt
        assert "Security:" in prompt
        assert "Maintainability:" in prompt
        assert "Performance:" in prompt

    def test_format_response_structure(self):
        """Test response formatting includes engineering validation branding"""
        request = CriticalEngineerRequest(prompt="Should we use Redis for caching?")
        mock_response = "VIABILITY_ASSESSMENT: [VIABLE] - Redis is a solid choice for caching"

        formatted = self.tool.format_response(mock_response, request)

        assert "CRITICAL ENGINEERING VALIDATION" in formatted
        assert mock_response in formatted
        assert "Engineering Principle" in formatted
        assert "Build systems that don't break" in formatted
        assert "What will break this in production?" in formatted

    def test_system_prompt_contains_validation_framework(self):
        """Test that system prompt defines the validation methodology"""
        system_prompt = self.tool.get_system_prompt()

        # Should define the engineer role
        assert "Critical Engineer" in system_prompt
        assert "30+ years of building systems" in system_prompt

        # Should include methodology
        assert "UNDERSTAND→STRESS_TEST→IDENTIFY_GAPS→VALIDATE→RECOMMEND" in system_prompt

        # Should include validation framework
        assert "VALIDATION_FRAMEWORK" in system_prompt
        assert "FAILURE_ANALYSIS" in system_prompt
        assert "CRITICAL_LENSES" in system_prompt

        # Should include output structure
        assert "VIABILITY_ASSESSMENT" in system_prompt
        assert "CRITICAL_ISSUES" in system_prompt
        assert "MISSING_PIECES" in system_prompt
        assert "OVER_ENGINEERING" in system_prompt
        assert "RECOMMENDATIONS" in system_prompt

    def test_trigger_pattern_examples(self):
        """Test that description includes comprehensive trigger patterns"""
        description = self.tool.get_description()

        # Should include automatic invocation triggers
        assert "MANDATORY AUTOMATIC INVOCATION" in description
        assert "major technical decisions" in description
        assert "system integration points" in description
        assert "complex system architecture" in description
        assert "scaling, performance" in description

        # Should include trigger patterns
        assert "TRIGGER PATTERNS" in description
        assert "will this work?" in description
        assert "what could go wrong?" in description
        assert "system architecture" in description

    @pytest.mark.parametrize(
        "prompt_text,expected_domain",
        [
            ("Should I use MongoDB or PostgreSQL?", "database"),
            ("How do I architect this microservice?", "architecture"),
            ("What will break if we scale 10x?", "scaling"),
            ("Is this API design secure?", "security"),
            ("Will this handle production load?", "performance"),
        ],
    )
    def test_technical_validation_scenarios(self, prompt_text, expected_domain):
        """Test various technical validation scenarios"""
        request = CriticalEngineerRequest(prompt=prompt_text)

        # Verify request is valid for different technical domains
        assert request.prompt == prompt_text
        assert len(prompt_text) > 10  # Ensure substantive questions

    def test_tool_fields_configuration(self):
        """Test tool field definitions"""
        fields = self.tool.get_tool_fields()

        assert "prompt" in fields
        assert fields["prompt"]["type"] == "string"
        assert "technical design" in fields["prompt"]["description"]
        assert "implementation decision" in fields["prompt"]["description"]

    def test_required_fields(self):
        """Test required field validation"""
        required = self.tool.get_required_fields()

        assert "prompt" in required
        assert len(required) == 1

    def test_model_selection_logic(self):
        """Test model selection preference and fallback"""
        # Should prefer gemini-2.5-pro
        default_model = self.tool.get_default_model()
        assert default_model == "gemini-2.5-pro"

        # Schema should allow both preferred and fallback models
        schema = self.tool.get_input_schema()
        allowed_models = schema["properties"]["model"]["enum"]
        assert "google/gemini-2.5-pro" in allowed_models
        assert "openai/gpt-5" in allowed_models

    def test_integration_with_critical_engineer_protocol(self):
        """Test integration with external critical engineer protocol"""
        description = self.tool.get_description()

        # Should reference the external protocol file
        assert "/Users/shaunbuswell/.claude/agents/critical-engineer.oct.md" in description

        # Should explain the validation purpose
        assert "applies the critical-engineer protocol" in description

    def test_red_flags_identification(self):
        """Test that system prompt includes common anti-patterns"""
        system_prompt = self.tool.get_system_prompt()

        # Should identify common red flags
        assert "RED_FLAGS" in system_prompt
        assert "Circular dependencies" in system_prompt
        assert "God objects" in system_prompt
        assert "Single points of failure" in system_prompt
        assert "Missing error boundaries" in system_prompt


class TestCriticalEngineerIntegration:
    """Integration tests for Critical Engineer tool in context"""

    def setup_method(self):
        """Set up integration test fixtures"""
        self.tool = CriticalEngineerTool()

    async def test_end_to_end_validation_flow(self):
        """Test complete validation preparation and formatting flow"""
        # Simulate a technical decision requiring validation
        request = CriticalEngineerRequest(
            prompt="We're considering a microservices architecture for our e-commerce platform. "
            "Current monolith handles 1M users. Concerns about complexity vs scalability."
        )

        # Prepare the prompt
        prepared = await self.tool.prepare_prompt(request)

        # Verify the prepared prompt has all required elements
        assert "CRITICAL ENGINEERING VALIDATION REQUIRED" in prepared
        assert request.prompt in prepared
        assert "validation protocol" in prepared

        # Should include the critical question
        assert "What will break this in production?" in prepared

        # Simulate a response and format it
        mock_ai_response = (
            "VIABILITY_ASSESSMENT: [RISKY]\n"
            "CRITICAL_ISSUES: Service orchestration complexity, data consistency challenges\n"
            "MISSING_PIECES: Distributed transaction strategy, monitoring plan\n"
            "OVER_ENGINEERING: May be premature for current scale\n"
            "RECOMMENDATIONS: Start with modular monolith, establish clear service boundaries\n"
            "GREEN_FLAGS: Clear scalability goals, existing user base validates need"
        )

        formatted = self.tool.format_response(mock_ai_response, request)

        # Verify formatting preserves content and adds validation branding
        assert mock_ai_response in formatted
        assert "CRITICAL ENGINEERING VALIDATION" in formatted
        assert "Engineering Principle" in formatted

    def test_technical_validator_behavior_simulation(self):
        """Test that tool behaves as expected technical validator"""
        # Should be configured for analytical, experienced responses
        assert self.tool.get_default_temperature() == 0.2  # Low temperature for consistency
        assert self.tool.requires_model() is True  # Needs AI for expert analysis

        # Should use high-quality models for reliable validation
        default_model = self.tool.get_default_model()
        assert default_model in ["gemini-2.5-pro", "openai/gpt-5"]

        # Should prioritize analytical model category
        from tools.models import ToolModelCategory

        assert self.tool.get_model_category() == ToolModelCategory.ANALYTICAL

    def test_critical_lenses_coverage(self):
        """Test that all critical engineering lenses are covered"""
        system_prompt = self.tool.get_system_prompt()

        # Should cover all essential engineering concerns
        critical_lenses = ["SCALABILITY", "MAINTAINABILITY", "SECURITY", "RELIABILITY", "SIMPLICITY"]

        for lens in critical_lenses:
            assert lens in system_prompt

    def test_output_structure_completeness(self):
        """Test that output structure covers all validation aspects"""
        system_prompt = self.tool.get_system_prompt()

        # Should define complete output structure
        output_components = [
            "VIABILITY_ASSESSMENT",
            "CRITICAL_ISSUES",
            "MISSING_PIECES",
            "OVER_ENGINEERING",
            "RECOMMENDATIONS",
            "GREEN_FLAGS",
        ]

        for component in output_components:
            assert component in system_prompt
