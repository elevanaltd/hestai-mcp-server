"""Test suite for RegistryTool - specialist approval registry management."""

# Context7: consulted for json
import json
# Context7: consulted for os
import os
# Context7: consulted for sqlite3
import sqlite3
# Context7: consulted for tempfile
import tempfile
# Context7: consulted for unittest
import unittest
# Context7: consulted for datetime
from datetime import datetime, timedelta
# Context7: consulted for pathlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Context7: consulted for pytest
import pytest

# Context7: consulted for tools - internal module
from tools.registry import RegistryTool


class TestRegistryTool(unittest.TestCase):
    """Test the RegistryTool for managing specialist approvals."""

    def setUp(self):
        """Set up test environment with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_registry.db")
        self.tool = RegistryTool(db_path=self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        # Context7: consulted for shutil
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tool_initialization(self):
        """Test that RegistryTool initializes with database."""
        self.assertTrue(os.path.exists(self.db_path))
        
        # Check database schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check blocked_changes table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='blocked_changes'
        """)
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()

    def test_create_blocked_entry(self):
        """Test creating a blocked change entry."""
        result = self.tool.create_blocked_entry(
            description="Test method without failing test",
            file_path="/path/to/test.py",
            specialist_type="testguard",
            blocked_content="expect(true).toBe(false)"
        )
        
        self.assertIn("uuid", result)
        self.assertIn("created_at", result)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["specialist_type"], "testguard")

    def test_approve_blocked_entry(self):
        """Test approving a blocked entry."""
        # First create an entry
        created = self.tool.create_blocked_entry(
            description="Test without implementation",
            file_path="/path/to/test.py",
            specialist_type="testguard",
            blocked_content="test content"
        )
        
        # Now approve it
        approved = self.tool.approve_entry(
            uuid=created["uuid"],
            specialist="testguard",
            reason="Proper TDD red phase assertion"
        )
        
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["uuid"], created["uuid"])
        self.assertIn("token", approved)
        self.assertIn("approved_at", approved)
        
    def test_reject_blocked_entry(self):
        """Test rejecting a blocked entry."""
        # First create an entry
        created = self.tool.create_blocked_entry(
            description="Meaningless test",
            file_path="/path/to/test.py",
            specialist_type="testguard",
            blocked_content="expect(true).toBe(false)"
        )
        
        # Reject it
        rejected = self.tool.reject_entry(
            uuid=created["uuid"],
            specialist="testguard",
            reason="Meaningless placeholder provides no specification",
            education="Write a test that describes expected behavior"
        )
        
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["uuid"], created["uuid"])
        self.assertIn("education", rejected)

    def test_validate_token(self):
        """Test token validation for approved entries."""
        # Create and approve an entry
        created = self.tool.create_blocked_entry(
            description="Valid test",
            file_path="/path/to/test.py",
            specialist_type="testguard",
            blocked_content="test content"
        )
        
        approved = self.tool.approve_entry(
            uuid=created["uuid"],
            specialist="testguard",
            reason="Valid TDD assertion"
        )
        
        # Validate the token
        validation = self.tool.validate_token(
            token=approved["token"],
            uuid=created["uuid"]
        )
        
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["specialist"], "testguard")
        
        # Second validation should fail (single-use)
        second_validation = self.tool.validate_token(
            token=approved["token"],
            uuid=created["uuid"]
        )
        
        self.assertFalse(second_validation["valid"])
        self.assertEqual(second_validation["error"], "token_already_used")

    def test_list_pending_approvals(self):
        """Test listing pending approvals."""
        # Create multiple entries
        for i in range(3):
            self.tool.create_blocked_entry(
                description=f"Test {i}",
                file_path=f"/path/to/test{i}.py",
                specialist_type="testguard",
                blocked_content=f"content {i}"
            )
        
        # List pending
        pending = self.tool.list_pending()
        
        self.assertEqual(len(pending), 3)
        for entry in pending:
            self.assertEqual(entry["status"], "blocked")

    def test_atomic_token_validation(self):
        """Test that token validation is atomic to prevent race conditions."""
        # Create and approve an entry
        created = self.tool.create_blocked_entry(
            description="Concurrent test",
            file_path="/path/to/test.py",
            specialist_type="testguard", 
            blocked_content="test content"
        )
        
        approved = self.tool.approve_entry(
            uuid=created["uuid"],
            specialist="testguard",
            reason="Valid assertion"
        )
        
        # Simulate concurrent validation attempts
        # Both read token as valid, but only one should succeed
        
        # First validation succeeds
        result1 = self.tool.validate_token(
            token=approved["token"],
            uuid=created["uuid"]
        )
        self.assertTrue(result1["valid"])
        
        # Second attempt with same token fails
        result2 = self.tool.validate_token(
            token=approved["token"],
            uuid=created["uuid"]
        )
        self.assertFalse(result2["valid"])
        self.assertEqual(result2["error"], "token_already_used")

    @pytest.mark.asyncio
    async def test_execute_method(self):
        """Test the execute method for MCP integration."""
        tool = RegistryTool()
        
        # Test create_blocked action
        result = await tool.execute(
            action="create_blocked",
            description="Test without implementation",
            file_path="/path/to/test.py",
            specialist_type="testguard",
            blocked_content="test content"
        )
        
        self.assertIn("uuid", result)
        self.assertEqual(result["status"], "blocked")
        
        # Test approve action
        approve_result = await tool.execute(
            action="approve",
            uuid=result["uuid"],
            specialist="testguard",
            reason="Valid TDD assertion"
        )
        
        self.assertEqual(approve_result["status"], "approved")
        self.assertIn("token", approve_result)


if __name__ == "__main__":
    unittest.main()