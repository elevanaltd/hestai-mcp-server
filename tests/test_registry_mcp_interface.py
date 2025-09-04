"""Tests for RegistryTool MCP interface compatibility."""

# Context7: consulted for pytest
# Context7: consulted for unittest
# Context7: consulted for tools - internal project module

from unittest.mock import Mock, patch

import pytest

from tools.registry import RegistryTool


class TestRegistryMCPInterface:
    """Test MCP interface compliance for RegistryTool."""

    @pytest.fixture
    def mock_registry_tool(self):
        """Create a mock RegistryTool with database mocked."""
        with patch.object(RegistryTool, '__init__', return_value=None):
            tool = RegistryTool()
            tool.db = Mock()
            tool.db.get_connection.return_value.__enter__ = Mock()
            tool.db.get_connection.return_value.__exit__ = Mock()
            return tool

    @pytest.mark.asyncio
    async def test_execute_with_arguments_dict_new_interface(self, mock_registry_tool):
        """Test that execute works with new arguments dict interface."""
        # Mock the internal methods
        mock_registry_tool.approve_entry = Mock(return_value={"status": "approved", "token": "test-token"})

        # Test new interface - FAILS until we implement backward compatibility
        arguments = {
            "action": "approve",
            "uuid": "test-uuid",
            "specialist": "testguard",
            "reason": "Test approval"
        }

        result = await mock_registry_tool.execute(arguments)

        assert result["status"] == "approved"
        assert result["token"] == "test-token"
        mock_registry_tool.approve_entry.assert_called_once_with(
            uuid="test-uuid",
            specialist="testguard",
            reason="Test approval"
        )

    @pytest.mark.asyncio
    async def test_execute_with_kwargs_legacy_interface(self, mock_registry_tool):
        """Test that execute still works with legacy **kwargs interface."""
        # Mock the internal methods
        mock_registry_tool.approve_entry = Mock(return_value={"status": "approved", "token": "legacy-token"})

        # Test legacy interface (how it's currently called) - FAILS until backward compatibility
        result = await mock_registry_tool.execute(
            action="approve",
            uuid="legacy-uuid",
            specialist="testguard",
            reason="Legacy approval"
        )

        assert result["status"] == "approved"
        assert result["token"] == "legacy-token"
        mock_registry_tool.approve_entry.assert_called_once_with(
            uuid="legacy-uuid",
            specialist="testguard",
            reason="Legacy approval"
        )

    @pytest.mark.asyncio
    async def test_execute_missing_required_arguments_validation(self, mock_registry_tool):
        """Test that execute validates required arguments and fails fast."""
        # Test missing action
        result = await mock_registry_tool.execute({"uuid": "test"})
        assert "error" in result
        assert "Missing required field: action" in result["error"]

        # Test missing required fields for approve action
        result = await mock_registry_tool.execute({
            "action": "approve",
            "uuid": "test-uuid"
            # Missing specialist and reason
        })
        assert "error" in result
        assert "Missing required fields for 'approve' action" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_action_handling(self, mock_registry_tool):
        """Test that execute handles unknown actions gracefully."""
        result = await mock_registry_tool.execute({
            "action": "unknown_action",
            "data": "test"
        })

        assert "error" in result
        assert "Unknown action: unknown_action" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_all_supported_actions(self, mock_registry_tool):
        """Test that execute supports all required actions with proper validation."""
        # Mock all internal methods
        mock_registry_tool.create_blocked_entry = Mock(return_value={"uuid": "blocked-123"})
        mock_registry_tool.approve_entry = Mock(return_value={"token": "approve-123"})
        mock_registry_tool.reject_entry = Mock(return_value={"status": "rejected"})
        mock_registry_tool.validate_token = Mock(return_value={"valid": True})
        mock_registry_tool.list_pending = Mock(return_value={"pending": []})
        mock_registry_tool.db.cleanup_old_entries = Mock(return_value=5)

        # Test create_blocked
        result = await mock_registry_tool.execute({
            "action": "create_blocked",
            "description": "test",
            "file_path": "/test",
            "specialist_type": "testguard",
            "blocked_content": "content"
        })
        assert result["uuid"] == "blocked-123"

        # Test approve
        result = await mock_registry_tool.execute({
            "action": "approve",
            "uuid": "test-uuid",
            "specialist": "testguard",
            "reason": "test"
        })
        assert result["token"] == "approve-123"

        # Test reject
        result = await mock_registry_tool.execute({
            "action": "reject",
            "uuid": "test-uuid",
            "specialist": "testguard",
            "reason": "test",
            "education": "learn this"
        })
        assert result["status"] == "rejected"

        # Test validate
        result = await mock_registry_tool.execute({
            "action": "validate",
            "token": "test-token",
            "uuid": "test-uuid"
        })
        assert result["valid"] is True

        # Test list_pending
        result = await mock_registry_tool.execute({
            "action": "list_pending"
        })
        assert "pending" in result

        # Test cleanup
        result = await mock_registry_tool.execute({
            "action": "cleanup"
        })
        assert result["deleted"] == 5
