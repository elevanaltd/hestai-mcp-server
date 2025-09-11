"""
Unit tests for SessionManager and SessionContext classes.

Tests project-aware context isolation functionality including:
- Session creation and lifecycle management
- Security boundary validation for project roots
- Thread-safe concurrent access
- Session timeout and cleanup
- FileContextProcessor integration
"""

import tempfile
import threading
import time
import unittest.mock
from pathlib import Path
from unittest import TestCase

import pytest

# CONTEXT7_BYPASS: UTILS-001 - Internal utils module from same codebase
from utils.session_manager import SessionContext, SessionManager, SecurityError


class TestSessionContext(TestCase):
    """Test SessionContext for project-scoped isolation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.allowed_workspaces = [self.temp_dir]
        self.session_id = "test-session-123"

    def test_session_context_creation_valid_project_root(self):
        """Test SessionContext creation with valid project root."""
        # Test creation with valid project directory
        session = SessionContext(
            session_id=self.session_id,
            project_root=self.temp_dir,
            allowed_workspaces=self.allowed_workspaces
        )
        
        self.assertEqual(session.session_id, self.session_id)
        self.assertEqual(str(session.project_root), str(Path(self.temp_dir).resolve()))
        self.assertIsInstance(session.created_at, float)
        self.assertIsInstance(session.last_activity_at, float)

    def test_session_context_creation_nonexistent_project_root(self):
        """Test SessionContext creation fails with nonexistent project root."""
        nonexistent_path = "/nonexistent/path/project"
        
        with self.assertRaises(ValueError) as context:
            SessionContext(
                session_id=self.session_id,
                project_root=nonexistent_path,
                allowed_workspaces=self.allowed_workspaces
            )
        
        self.assertIn("does not exist", str(context.exception))

    def test_session_context_creation_dangerous_path(self):
        """Test SessionContext creation fails with dangerous system paths."""
        dangerous_paths = ["/", "/etc", "/usr", "/bin"]
        
        for dangerous_path in dangerous_paths:
            with self.assertRaises(SecurityError) as context:
                SessionContext(
                    session_id=self.session_id,
                    project_root=dangerous_path,
                    allowed_workspaces=self.allowed_workspaces
                )
            
            self.assertIn("dangerous path", str(context.exception))

    def test_session_context_creation_outside_allowed_workspace(self):
        """Test SessionContext creation fails when project root outside allowed workspaces."""
        # Create temp directory outside allowed workspaces
        outside_workspace = tempfile.mkdtemp()
        
        with self.assertRaises(SecurityError) as context:
            SessionContext(
                session_id=self.session_id,
                project_root=outside_workspace,
                allowed_workspaces=self.allowed_workspaces  # Doesn't include outside_workspace
            )
        
        self.assertIn("outside allowed workspaces", str(context.exception))

    def test_file_context_processor_lazy_loading(self):
        """Test FileContextProcessor is lazy-loaded with correct project_root."""
        session = SessionContext(
            session_id=self.session_id,
            project_root=self.temp_dir,
            allowed_workspaces=self.allowed_workspaces
        )
        
        # Initially no processor loaded
        self.assertIsNone(session._file_context_processor)
        
        # First access creates processor
        processor1 = session.get_file_context_processor()
        self.assertIsNotNone(processor1)
        self.assertEqual(str(processor1.project_root), str(Path(self.temp_dir).resolve()))
        
        # Second access returns same instance
        processor2 = session.get_file_context_processor()
        self.assertIs(processor1, processor2)

    def test_touch_updates_activity_timestamp(self):
        """Test touch() method updates last_activity_at timestamp."""
        session = SessionContext(
            session_id=self.session_id,
            project_root=self.temp_dir,
            allowed_workspaces=self.allowed_workspaces
        )
        
        original_timestamp = session.last_activity_at
        time.sleep(0.01)  # Small delay to ensure timestamp change
        
        session.touch()
        
        self.assertGreater(session.last_activity_at, original_timestamp)


class TestSessionManager(TestCase):
    """Test SessionManager for thread-safe session lifecycle management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.allowed_workspaces = [self.temp_dir]
        self.session_manager = SessionManager(
            allowed_workspaces=self.allowed_workspaces,
            session_timeout=1.0  # 1 second for testing
        )

    def test_session_manager_initialization(self):
        """Test SessionManager initialization with allowed workspaces."""
        manager = SessionManager(allowed_workspaces=self.allowed_workspaces)
        
        self.assertEqual(len(manager.allowed_workspaces), 1)
        self.assertEqual(str(manager.allowed_workspaces[0]), str(Path(self.temp_dir).resolve()))

    def test_session_manager_default_workspaces(self):
        """Test SessionManager uses default workspaces when none provided."""
        manager = SessionManager()  # No allowed_workspaces provided
        
        # Should have at least one default workspace
        self.assertGreater(len(manager.allowed_workspaces), 0)

    def test_get_or_create_session_new_session(self):
        """Test getting or creating new session."""
        session_id = "new-session-456"
        
        session = self.session_manager.get_or_create_session(
            session_id=session_id,
            project_root=self.temp_dir
        )
        
        self.assertEqual(session.session_id, session_id)
        self.assertEqual(str(session.project_root), str(Path(self.temp_dir).resolve()))
        self.assertEqual(self.session_manager.get_session_count(), 1)

    def test_get_or_create_session_existing_session(self):
        """Test getting existing session returns same instance."""
        session_id = "existing-session-789"
        
        # Create session first time
        session1 = self.session_manager.get_or_create_session(
            session_id=session_id,
            project_root=self.temp_dir
        )
        
        # Get same session second time
        session2 = self.session_manager.get_or_create_session(
            session_id=session_id,
            project_root=self.temp_dir
        )
        
        self.assertIs(session1, session2)
        self.assertEqual(self.session_manager.get_session_count(), 1)

    def test_get_session_nonexistent(self):
        """Test getting nonexistent session returns None."""
        result = self.session_manager.get_session("nonexistent-session")
        self.assertIsNone(result)

    def test_end_session(self):
        """Test ending session removes it from manager."""
        session_id = "session-to-end"
        
        # Create session
        self.session_manager.get_or_create_session(
            session_id=session_id,
            project_root=self.temp_dir
        )
        self.assertEqual(self.session_manager.get_session_count(), 1)
        
        # End session
        result = self.session_manager.end_session(session_id)
        self.assertTrue(result)
        self.assertEqual(self.session_manager.get_session_count(), 0)
        
        # Ending nonexistent session returns False
        result = self.session_manager.end_session("nonexistent")
        self.assertFalse(result)

    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions based on timeout."""
        # Create session that will expire
        session_id = "expiring-session"
        session = self.session_manager.get_or_create_session(
            session_id=session_id,
            project_root=self.temp_dir
        )
        
        # Manually set last activity to past timeout
        session.last_activity_at = time.time() - 2.0  # 2 seconds ago, timeout is 1 second
        
        self.assertEqual(self.session_manager.get_session_count(), 1)
        
        # Cleanup expired sessions
        cleaned_count = self.session_manager.cleanup_expired_sessions()
        
        self.assertEqual(cleaned_count, 1)
        self.assertEqual(self.session_manager.get_session_count(), 0)

    def test_thread_safety_concurrent_access(self):
        """Test thread-safe concurrent access to SessionManager."""
        session_ids = [f"concurrent-session-{i}" for i in range(10)]
        sessions_created = []
        errors = []

        def create_session(session_id):
            try:
                session = self.session_manager.get_or_create_session(
                    session_id=session_id,
                    project_root=self.temp_dir
                )
                sessions_created.append(session)
            except Exception as e:
                errors.append(e)

        # Create threads for concurrent session creation
        threads = [
            threading.Thread(target=create_session, args=(session_id,))
            for session_id in session_ids
        ]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all sessions created without errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(sessions_created), 10)
        self.assertEqual(self.session_manager.get_session_count(), 10)

    def test_get_session_info(self):
        """Test getting session manager information."""
        # Create a test session
        session_id = "info-test-session"
        self.session_manager.get_or_create_session(
            session_id=session_id,
            project_root=self.temp_dir
        )
        
        info = self.session_manager.get_session_info()
        
        self.assertEqual(info["active_sessions"], 1)
        self.assertIn("allowed_workspaces", info)
        self.assertIn("session_timeout", info)
        self.assertIn("sessions", info)
        self.assertEqual(len(info["sessions"]), 1)
        self.assertEqual(info["sessions"][0]["session_id"], session_id)