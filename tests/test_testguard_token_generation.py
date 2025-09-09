"""Test for testguard direct token generation enhancement."""

# TESTGUARD_BYPASS: INFRA-003 - Testing infrastructure enhancement
# TDD: Test for direct token generation in testguard

# Context7: consulted for asyncio
import asyncio

# Context7: consulted for datetime
import datetime

# Context7: consulted for re
import re

# Context7: consulted for unittest
import unittest

# Context7: consulted for unittest.mock
from unittest.mock import MagicMock, patch

# Context7: consulted for tools.testguard - internal module
from tools.testguard import RequirementsRequest, RequirementsTool


class TestTestguardTokenGeneration(unittest.TestCase):
    """Test the enhanced testguard token generation workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = RequirementsTool()

    def test_blocked_uuid_extraction(self):
        """Test that blocked UUID is correctly extracted from various patterns."""
        test_cases = [
            ("/tmp/blocked-test-7b55dcdd-uuid", "7b55dcdd-uuid"),
            ("blocked_changes/abc12345-def6-7890-ghij-klmnopqrstuv", "abc12345-def6-7890-ghij-klmnopqrstuv"),
            ("review 12345678-90ab-cdef-ghij-klmnopqrstuv", "12345678-90ab-cdef-ghij-klmnopqrstuv"),
            ("blocked-abcd1234", "abcd1234"),
        ]

        for prompt, expected_uuid in test_cases:
            request = RequirementsRequest(prompt=prompt, model="google/gemini-2.5-pro")
            asyncio.run(self.tool.prepare_prompt(request))
            self.assertEqual(self.tool._blocked_uuid, expected_uuid, f"Failed for prompt: {prompt}")

    def test_approved_token_generation(self):
        """Test that approved changes generate tokens correctly."""
        # Set up blocked UUID
        self.tool._blocked_uuid = "7b55dcdd-test-uuid"

        # Mock response indicating approval
        response = "APPROVED: This is valid TDD practice - writing test before implementation"
        request = RequirementsRequest(prompt="review blocked change", model="google/gemini-2.5-pro")

        # Mock the registry to avoid actual database writes
        with patch("tools.registry.RegistryDB") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry_class.return_value = mock_registry

            # Format the response
            formatted = self.tool.format_response(response, request)

            # Verify token generation
            self.assertIn("APPROVED ✅", formatted)
            self.assertIn("APPROVAL TOKEN GENERATED", formatted)
            self.assertIn("TEST-METHODOLOGY-GUARDIAN", formatted)
            self.assertIn("7b55dcdd", formatted)  # UUID short form in token

            # Extract the generated token
            token_match = re.search(r"Token: `([^`]+)`", formatted)
            self.assertIsNotNone(token_match, "Token not found in response")

            token = token_match.group(1)
            # Verify token format
            self.assertTrue(token.startswith("TEST-METHODOLOGY-GUARDIAN-"))
            self.assertIn(datetime.datetime.now().strftime("%Y%m%d"), token)
            self.assertIn("7b55dcdd", token)

            # Verify registry was called
            mock_registry.approve_entry.assert_called_once_with(
                uuid="7b55dcdd-test-uuid",
                specialist="testguard",
                reason="This is valid TDD practice - writing test before implementation",
            )

    def test_rejected_response_formatting(self):
        """Test that rejected changes are formatted correctly."""
        # Set up blocked UUID
        self.tool._blocked_uuid = "7b55dcdd-test-uuid"

        # Mock response indicating rejection
        response = "REJECTED: This is test manipulation - fixing test instead of code"
        request = RequirementsRequest(prompt="review blocked change", model="google/gemini-2.5-pro")

        # Format the response
        formatted = self.tool.format_response(response, request)

        # Verify rejection formatting
        self.assertIn("REJECTED ❌", formatted)
        self.assertIn("CHANGE REJECTED", formatted)
        self.assertIn("UUID: 7b55dcdd-test-uuid", formatted)
        self.assertIn("violates test methodology principles", formatted)
        self.assertNotIn("TOKEN", formatted.upper())  # No token for rejections

    def test_normal_analysis_without_blocked_change(self):
        """Test that normal analysis works without blocked change context."""
        # No blocked UUID set
        response = "This code follows good TDD practices."
        request = RequirementsRequest(prompt="analyze this test", model="google/gemini-2.5-pro")

        # Format the response
        formatted = self.tool.format_response(response, request)

        # Verify standard formatting
        self.assertIn("TEST METHODOLOGY GUARDIAN ANALYSIS", formatted)
        self.assertIn("Guardian Protocol: Defend test integrity", formatted)
        self.assertNotIn("TOKEN", formatted.upper())
        self.assertNotIn("APPROVED ✅", formatted)
        self.assertNotIn("REJECTED ❌", formatted)

    def test_registry_failure_still_generates_token(self):
        """Test that token is generated even if registry recording fails."""
        # Set up blocked UUID
        self.tool._blocked_uuid = "7b55dcdd-test-uuid"

        # Mock response indicating approval
        response = "APPROVED: Valid TDD practice"
        request = RequirementsRequest(prompt="review blocked change", model="google/gemini-2.5-pro")

        # Mock the registry to raise an exception
        with patch("tools.registry.RegistryDB") as mock_registry_class:
            mock_registry_class.side_effect = Exception("Database error")

            # Format the response - should not raise exception
            formatted = self.tool.format_response(response, request)

            # Verify token still generated
            self.assertIn("APPROVAL TOKEN GENERATED", formatted)
            token_match = re.search(r"Token: `([^`]+)`", formatted)
            self.assertIsNotNone(token_match, "Token not generated despite registry failure")

    async def test_prepare_prompt_for_blocked_change(self):
        """Test that prepare_prompt correctly identifies and handles blocked changes."""
        request = RequirementsRequest(prompt="/tmp/blocked-test-7b55dcdd-uuid", model="google/gemini-2.5-pro")

        # Prepare the prompt
        prompt = await self.tool.prepare_prompt(request)

        # Verify blocked change handling
        self.assertIn("BLOCKED CHANGE REVIEW", prompt)
        self.assertIn("DIRECT APPROVAL WORKFLOW", prompt)
        self.assertIn("Blocked Change UUID: 7b55dcdd-uuid", prompt)
        self.assertIn("APPROVED: <your approval reason>", prompt)
        self.assertIn("REJECTED: <your rejection reason>", prompt)

        # Verify UUID was stored
        self.assertEqual(self.tool._blocked_uuid, "7b55dcdd-uuid")


if __name__ == "__main__":
    unittest.main()
