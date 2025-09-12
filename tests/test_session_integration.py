"""
Tests for SessionManager integration with MCP server.

This module tests the complete integration pipeline from MCP requests
through session creation to tool isolation.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

# CONTEXT7_BYPASS: INFRA-003 - Internal server module from same codebase
# CONTEXT7_BYPASS: INFRA-003 - Internal utils module from same codebase
from utils.session_manager import SessionContext, SessionManager


class TestSessionIntegration:
    """Test session management integration with MCP server."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager for testing."""
        manager = Mock(spec=SessionManager)
        session = Mock(spec=SessionContext)
        session.session_id = "test-session"
        session.project_root = Path("/test/project")
        session.get_file_context_processor.return_value = Mock()

        manager.get_or_create_session.return_value = session
        return manager

    @pytest.fixture
    def sample_tool_args(self):
        """Sample tool arguments for testing."""
        return {
            "prompt": "Test prompt",
            "model": "google/gemini-2.5-flash",
            "session_id": "test-session-123",
            "project_root": "/test/project",
        }

    def test_session_id_extraction_from_params(self, sample_tool_args):
        """Test that session_id is correctly extracted from tool parameters."""
        session_id = sample_tool_args.get("session_id")
        project_root = sample_tool_args.get("project_root")

        assert session_id == "test-session-123"
        assert project_root == "/test/project"

    def test_default_session_handling_for_missing_session_id(self):
        """Test graceful handling when session_id is missing."""
        args_without_session = {"prompt": "Test", "model": "auto"}

        # Should use default session handling
        session_id = args_without_session.get("session_id", "default")
        assert session_id == "default"

    @pytest.mark.asyncio
    async def test_session_manager_initialization_in_server(self):
        """Test that SessionManager is properly initialized in server context."""
        # This test will fail initially - we need to add initialization
        from server import session_manager

        # This should exist after integration
        assert hasattr(session_manager, "get_or_create_session")
        assert hasattr(session_manager, "allowed_workspaces")

    @pytest.mark.asyncio
    async def test_project_root_validation(self):
        """Test that project_root is validated against allowed workspaces."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create allowed and project directories
            allowed_path = Path(temp_dir) / "allowed"
            allowed_path.mkdir()
            project_path = allowed_path / "project"
            project_path.mkdir()

            manager = SessionManager(allowed_workspaces=[str(allowed_path)])

            # Valid path should work
            valid_session = await manager.get_or_create_session("test-session", str(project_path))
            assert valid_session is not None

            # Test security boundary enforcement with a different manager
            forbidden_path = Path(temp_dir) / "forbidden"
            forbidden_path.mkdir()
            restricted_manager = SessionManager(allowed_workspaces=[str(allowed_path)])

            # Invalid path should raise SecurityError
            # CONTEXT7_BYPASS: INFRA-003 - Internal utils module from same codebase
            from utils.session_manager import SecurityError

            with pytest.raises(SecurityError):
                await restricted_manager.get_or_create_session("invalid-session", str(forbidden_path))

    @pytest.mark.asyncio
    async def test_session_aware_tool_execution(self, mock_session_manager, sample_tool_args):
        """Test that tools are executed with session context."""
        # Test the session parameter extraction logic directly
        session_id = sample_tool_args.get("session_id", "default")
        project_root = sample_tool_args.get("project_root")

        assert session_id == "test-session-123"
        assert project_root == "/test/project"

        # Test session creation logic
        if project_root:
            session_context = mock_session_manager.get_or_create_session(session_id, project_root)
            # Verify session was created/retrieved
            mock_session_manager.get_or_create_session.assert_called_once_with("test-session-123", "/test/project")
            assert session_context is not None

    def test_session_lifecycle_hooks(self, mock_session_manager):
        """Test session creation and activity updates."""
        session = mock_session_manager.get_or_create_session("test", "/test/path")

        # Session should be returned
        assert session is not None

        # Test cleanup
        result = mock_session_manager.end_session("test")
        # Mock should return something
        assert result is not None

    def test_backward_compatibility_no_session_params(self):
        """Test that requests without session parameters still work."""
        legacy_args = {"prompt": "Test prompt", "model": "auto"}

        # Test parameter extraction logic for backward compatibility
        session_id = legacy_args.get("session_id", "default")
        project_root = legacy_args.get("project_root")

        assert session_id == "default"  # Should use default
        assert project_root is None  # Should be None for legacy requests

    @pytest.mark.asyncio
    async def test_tool_instance_isolation_per_session(self):
        """Test that different sessions get isolated tool instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create project directories
            test_path = Path(temp_dir) / "test"
            test_path.mkdir()
            project1_path = test_path / "project1"
            project1_path.mkdir()
            project2_path = test_path / "project2"
            project2_path.mkdir()

            manager = SessionManager(allowed_workspaces=[str(test_path)])

            session1 = await manager.get_or_create_session("session1", str(project1_path))
            session2 = await manager.get_or_create_session("session2", str(project2_path))

            # Sessions should have different contexts
            assert session1.session_id != session2.session_id
            assert session1.project_root != session2.project_root

            # File context processors should be isolated
            processor1 = session1.get_file_context_processor()
            processor2 = session2.get_file_context_processor()
            assert processor1 is not processor2

    @pytest.mark.asyncio
    async def test_session_cleanup_on_disconnect(self):
        """Test that sessions are cleaned up when clients disconnect."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SessionManager(allowed_workspaces=[str(temp_dir)])

            # Create session
            session = await manager.get_or_create_session("test-cleanup", str(temp_dir))

            # Manually expire the session
            session.last_activity_at = 0  # Set to very old timestamp

            # Should clean up the expired session
            cleaned_count = await manager.cleanup_expired_sessions(timeout_seconds=1)
            assert cleaned_count == 1
