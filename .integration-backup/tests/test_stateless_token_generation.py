"""Test suite for stateless token generation instructions in specialist tools."""

# TESTGUARD_BYPASS: INFRA-002 - Test infrastructure for stateless token generation
# This tests the stateless prompt instructions for token generation

# Context7: consulted for unittest
# Context7: consulted for os
import os

# Context7: consulted for tempfile
import tempfile
import unittest

# Context7: consulted for pytest
import pytest

from tools.critical_engineer import CriticalEngineerTool

# Context7: consulted for tools - internal modules
from tools.registry import RegistryTool
from tools.testguard import RequirementsTool


class TestStatelessTokenGeneration(unittest.TestCase):
    """Test that specialist tools provide correct stateless instructions for token generation."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_registry.db")
        self.registry = RegistryTool(db_path=self.db_path)

        # Create a blocked entry
        self.blocked_entry = self.registry.create_blocked_entry(
            description="Test without assertion",
            file_path="/path/to/test.py",
            specialist_type="testguard",
            blocked_content="expect(true).toBe(false)",
        )
        self.blocked_uuid = self.blocked_entry["uuid"]

    def tearDown(self):
        """Clean up temporary files."""
        # Context7: consulted for shutil
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_testguard_includes_registry_instructions(self):
        """Test that testguard includes proper registry call instructions."""
        testguard = RequirementsTool()

        # Prepare request with blocked file
        from tools.shared.base_models import ToolRequest

        request = ToolRequest(prompt=f"review /tmp/blocked-test-{self.blocked_uuid}", model="gemini-2.5-flash")

        # Get the prepared prompt
        prompt = await testguard.prepare_prompt(request)

        # Verify it includes registry instructions
        self.assertIn("Call the 'registry' tool", prompt)
        self.assertIn("action: 'approve'", prompt)
        self.assertIn("action: 'reject'", prompt)
        self.assertIn(f"uuid: '{self.blocked_uuid}'", prompt)
        self.assertIn("specialist: 'testguard'", prompt)
        self.assertIn("reason:", prompt)
        self.assertIn("education:", prompt)

    @pytest.mark.asyncio
    async def test_critical_engineer_includes_registry_instructions(self):
        """Test that critical-engineer includes proper registry call instructions."""
        critical = CriticalEngineerTool()

        # Create blocked entry for critical-engineer
        ce_entry = self.registry.create_blocked_entry(
            description="Architecture decision",
            file_path="/path/to/design.py",
            specialist_type="critical-engineer",
            blocked_content="microservices architecture",
        )

        # Prepare request
        from tools.shared.base_models import ToolRequest

        request = ToolRequest(prompt=f"review blocked change {ce_entry['uuid']}", model="gemini-2.5-pro")

        # Get the prepared prompt
        prompt = await critical.prepare_prompt(request)

        # Verify it includes registry instructions
        self.assertIn("Call the 'registry' tool", prompt)
        self.assertIn("action: 'approve'", prompt)
        self.assertIn("action: 'reject'", prompt)
        self.assertIn(f"uuid: '{ce_entry['uuid']}'", prompt)
        self.assertIn("specialist: 'critical-engineer'", prompt)
        self.assertIn("production-ready", prompt)
        self.assertIn("will break in production", prompt)

    @pytest.mark.asyncio
    async def test_registry_execute_approve_action(self):
        """Test that registry execute method handles approve action."""
        result = await self.registry.execute(
            action="approve", uuid=self.blocked_uuid, specialist="testguard", reason="Valid TDD red phase"
        )

        # Verify approval succeeded
        self.assertEqual(result["status"], "approved")
        self.assertIn("token", result)
        self.assertIn("TESTGUARD", result["token"])
        self.assertIn(self.blocked_uuid[:8], result["token"])

    @pytest.mark.asyncio
    async def test_registry_execute_reject_action(self):
        """Test that registry execute method handles reject action."""
        # Create another entry to reject
        rejected_entry = self.registry.create_blocked_entry(
            description="Bad test",
            file_path="/path/to/bad.py",
            specialist_type="testguard",
            blocked_content="meaningless",
        )

        result = await self.registry.execute(
            action="reject",
            uuid=rejected_entry["uuid"],
            specialist="testguard",
            reason="Meaningless placeholder",
            education="Write descriptive tests",
        )

        # Verify rejection succeeded
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "Meaningless placeholder")
        self.assertEqual(result["education"], "Write descriptive tests")

    @pytest.mark.asyncio
    async def test_no_registry_instructions_for_normal_requests(self):
        """Test that normal requests don't include registry instructions."""
        testguard = RequirementsTool()

        # Prepare normal request (no blocked file)
        from tools.shared.base_models import ToolRequest

        request = ToolRequest(prompt="Should I write tests first?", model="gemini-2.5-flash")

        # Get the prepared prompt
        prompt = await testguard.prepare_prompt(request)

        # Verify it does NOT include registry instructions
        self.assertNotIn("Call the 'registry' tool", prompt)
        self.assertNotIn("action: 'approve'", prompt)
        self.assertNotIn("uuid:", prompt)

    @pytest.mark.asyncio
    async def test_registry_token_is_single_use(self):
        """Test that tokens generated via execute are single-use."""
        # Generate token via approve
        approve_result = await self.registry.execute(
            action="approve", uuid=self.blocked_uuid, specialist="testguard", reason="Valid test"
        )

        token = approve_result["token"]

        # First validation should succeed
        validation1 = await self.registry.execute(action="validate", token=token, uuid=self.blocked_uuid)
        self.assertTrue(validation1["valid"])

        # Second validation should fail
        validation2 = await self.registry.execute(action="validate", token=token, uuid=self.blocked_uuid)
        self.assertFalse(validation2["valid"])
        self.assertEqual(validation2["error"], "token_already_used")

    @pytest.mark.asyncio
    async def test_registry_execute_with_unknown_action(self):
        """Test registry execute handles unknown actions gracefully."""
        result = await self.registry.execute(action="unknown_action", some_param="value")

        self.assertIn("error", result)
        self.assertIn("Unknown action", result["error"])

    @pytest.mark.asyncio
    async def test_blocked_uuid_extraction_patterns(self):
        """Test that UUID extraction works for various patterns."""
        testguard = RequirementsTool()

        patterns = [
            f"/tmp/blocked-test-{self.blocked_uuid}",
            f"review {self.blocked_uuid}",
            f"~/.claude/hooks/blocked_changes/{self.blocked_uuid}.json",
            f"blocked change {self.blocked_uuid[:8]}",
        ]

        for pattern in patterns:
            from tools.shared.base_models import ToolRequest

            request = ToolRequest(prompt=pattern, model="gemini-2.5-flash")

            prompt = await testguard.prepare_prompt(request)

            # Should detect as blocked and include instructions
            if "blocked" in pattern.lower() or "/tmp/blocked-" in pattern:
                self.assertIn("BLOCKED CHANGE REVIEW", prompt)


if __name__ == "__main__":
    unittest.main()
