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
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

import pytest

# CONTEXT7_BYPASS: UTILS-001 - Internal utils module from same codebase
from utils.session_manager import SessionContext, SessionManager


class TestSessionContext(TestCase):
    """Test SessionContext for project-scoped isolation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.allowed_workspaces = [self.temp_dir]
        self.session_id = "test-session-123"

    def test_session_context_creation_valid_project_root(self):
        """Test SessionContext creation with valid project root."""
        # Test creation with valid project directory - SessionContext expects pre-validated Path
        validated_path = Path(self.temp_dir).resolve()
        session = SessionContext(session_id=self.session_id, project_root_validated=validated_path)

        self.assertEqual(session.session_id, self.session_id)
        self.assertEqual(str(session.project_root), str(validated_path))
        self.assertIsInstance(session.created_at, float)
        self.assertIsInstance(session.last_activity_at, float)

    def test_session_context_creation_nonexistent_project_root(self):
        """Test SessionContext creation with nonexistent path - validation should happen in SessionManager."""
        # SessionContext accepts pre-validated paths, so we test with Path object
        # Validation of existence should be done by SessionManager._validate_project_root
        nonexistent_path = Path("/nonexistent/path/project")

        # SessionContext itself doesn't validate existence - it trusts the pre-validated Path
        session = SessionContext(session_id=self.session_id, project_root_validated=nonexistent_path)
        self.assertEqual(str(session.project_root), str(nonexistent_path))

    def test_session_context_creation_dangerous_path(self):
        """Test SessionContext with dangerous paths - validation should happen in SessionManager."""
        # SessionContext accepts pre-validated paths
        # Dangerous path validation should be done by SessionManager._validate_project_root
        dangerous_paths = ["/", "/etc", "/usr", "/bin"]

        for dangerous_path in dangerous_paths:
            # SessionContext itself doesn't validate - it trusts the pre-validated Path
            validated_path = Path(dangerous_path)
            session = SessionContext(session_id=self.session_id, project_root_validated=validated_path)
            self.assertEqual(str(session.project_root), str(validated_path))

    def test_session_context_creation_outside_allowed_workspace(self):
        """Test SessionContext with path outside workspaces - validation should happen in SessionManager."""
        # SessionContext accepts pre-validated paths
        # Workspace validation should be done by SessionManager._validate_project_root
        outside_workspace = tempfile.mkdtemp()
        validated_path = Path(outside_workspace).resolve()

        # SessionContext itself doesn't validate workspaces - it trusts the pre-validated Path
        session = SessionContext(session_id=self.session_id, project_root_validated=validated_path)
        self.assertEqual(str(session.project_root), str(validated_path))

    def test_file_context_processor_lazy_loading(self):
        """Test FileContextProcessor is lazy-loaded with correct project_root."""
        validated_path = Path(self.temp_dir).resolve()
        session = SessionContext(session_id=self.session_id, project_root_validated=validated_path)

        # Initially no processor loaded
        self.assertIsNone(session._file_context_processor)

        # First access creates processor
        processor1 = session.get_file_context_processor()
        self.assertIsNotNone(processor1)
        self.assertEqual(str(processor1.project_root), str(validated_path))

        # Second access returns same instance
        processor2 = session.get_file_context_processor()
        self.assertIs(processor1, processor2)

    def test_touch_updates_activity_timestamp(self):
        """Test touch() method updates last_activity_at timestamp."""
        validated_path = Path(self.temp_dir).resolve()
        session = SessionContext(session_id=self.session_id, project_root_validated=validated_path)

        original_timestamp = session.last_activity_at
        time.sleep(0.01)  # Small delay to ensure timestamp change

        session.touch()

        self.assertGreater(session.last_activity_at, original_timestamp)


class TestSessionManager(IsolatedAsyncioTestCase):
    """Test SessionManager for thread-safe session lifecycle management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.allowed_workspaces = [self.temp_dir]
        self.session_manager = SessionManager(
            allowed_workspaces=self.allowed_workspaces,
            session_timeout=1.0,  # 1 second for testing
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

    async def test_get_or_create_session_new_session(self):
        """Test getting or creating new session."""
        session_id = "new-session-456"

        session = await self.session_manager.get_or_create_session(session_id=session_id, project_root=self.temp_dir)

        self.assertEqual(session.session_id, session_id)
        self.assertEqual(str(session.project_root), str(Path(self.temp_dir).resolve()))
        self.assertEqual(await self.session_manager.get_session_count(), 1)

    async def test_get_or_create_session_existing_session(self):
        """Test getting existing session returns same instance."""
        session_id = "existing-session-789"

        # Create session first time
        session1 = await self.session_manager.get_or_create_session(session_id=session_id, project_root=self.temp_dir)

        # Get same session second time
        session2 = await self.session_manager.get_or_create_session(session_id=session_id, project_root=self.temp_dir)

        self.assertIs(session1, session2)
        self.assertEqual(await self.session_manager.get_session_count(), 1)

    async def test_get_session_nonexistent(self):
        """Test getting nonexistent session raises SessionNotFoundError (SECURITY: fail-fast)."""
        # SECURITY: This was changed from returning None to raising an exception
        # as part of P0 security fix to prevent silent failures
        # CONTEXT7_BYPASS: INFRA-003 - Internal utils module from same codebase
        from utils.session_manager import SessionNotFoundError

        with self.assertRaises(SessionNotFoundError) as context:
            await self.session_manager.get_session("nonexistent-session")

        self.assertIn("Session 'nonexistent-session' not found", str(context.exception))

    async def test_end_session(self):
        """Test ending session removes it from manager."""
        session_id = "session-to-end"

        # Create session
        await self.session_manager.get_or_create_session(session_id=session_id, project_root=self.temp_dir)
        self.assertEqual(await self.session_manager.get_session_count(), 1)

        # End session
        result = await self.session_manager.end_session(session_id)
        self.assertTrue(result)
        self.assertEqual(await self.session_manager.get_session_count(), 0)

        # Ending nonexistent session returns False
        result = await self.session_manager.end_session("nonexistent")
        self.assertFalse(result)

    async def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions based on timeout."""
        # Create session that will expire
        session_id = "expiring-session"
        session = await self.session_manager.get_or_create_session(session_id=session_id, project_root=self.temp_dir)

        # Manually set last activity to past timeout
        session.last_activity_at = time.time() - 2.0  # 2 seconds ago, timeout is 1 second

        self.assertEqual(await self.session_manager.get_session_count(), 1)

        # Cleanup expired sessions
        cleaned_count = await self.session_manager.cleanup_expired_sessions()

        self.assertEqual(cleaned_count, 1)
        self.assertEqual(await self.session_manager.get_session_count(), 0)

    @pytest.mark.skip(reason="Threading tests need async adaptation")
    def test_get_or_create_session_race_condition(self):
        """Test get_or_create_session must be atomic under concurrent access.

        CONTRACT: get_or_create_session MUST handle concurrent calls atomically.
        Both threads should succeed without exceptions, and exactly one session
        should be created. No race conditions or errors should occur.

        This test uses method instrumentation to force the specific thread
        interleaving that currently causes race conditions, proving the bug exists.
        """
        session_id = "atomic-test-session"

        # Track results - BOTH threads should succeed without errors
        sessions_created = []
        errors = []
        create_session_calls = []

        # Store original create_session method
        original_create_session = self.session_manager.create_session
        race_window_hit = threading.Event()
        second_thread_can_proceed = threading.Event()

        def instrumented_create_session(sid, project_root):
            """Instrumented create_session that forces race condition timing"""
            create_session_calls.append(threading.current_thread().name)

            # If this is the first call, pause to let second thread also reach this point
            if len(create_session_calls) == 1:
                race_window_hit.set()  # Signal first thread hit create_session
                second_thread_can_proceed.wait(timeout=2.0)  # Wait for second thread

            # Now call original method - this currently causes race condition
            return original_create_session(sid, project_root)

        # Monkey patch to force race timing
        self.session_manager.create_session = instrumented_create_session

        try:

            def thread1_get_or_create():
                try:
                    session = self.session_manager.get_or_create_session(session_id, self.temp_dir)
                    sessions_created.append(session)
                except Exception as e:
                    errors.append(e)

            def thread2_get_or_create():
                try:
                    # Wait for first thread to hit create_session
                    race_window_hit.wait(timeout=2.0)

                    # Release first thread - both now attempt creation simultaneously
                    second_thread_can_proceed.set()

                    session = self.session_manager.get_or_create_session(session_id, self.temp_dir)
                    sessions_created.append(session)
                except Exception as e:
                    errors.append(e)

            # Start both threads
            t1 = threading.Thread(target=thread1_get_or_create, name="Thread-1")
            t2 = threading.Thread(target=thread2_get_or_create, name="Thread-2")

            t1.start()
            t2.start()

            t1.join(timeout=5.0)
            t2.join(timeout=5.0)

        finally:
            # Restore original method
            self.session_manager.create_session = original_create_session

        # CONTRACT ASSERTIONS: What the code MUST do (currently fails these)

        # NO exceptions should occur - get_or_create_session MUST be atomic
        self.assertEqual(
            len(errors), 0, f"get_or_create_session must handle concurrency atomically. Got errors: {errors}"
        )

        # BOTH threads should succeed in getting a session
        self.assertEqual(
            len(sessions_created),
            2,
            f"Both threads should get session successfully. Got {len(sessions_created)} sessions",
        )

        # All sessions should be the SAME instance (atomic behavior)
        unique_sessions = {id(session) for session in sessions_created}
        self.assertEqual(
            len(unique_sessions),
            1,
            f"Both threads should get same session instance. Got {len(unique_sessions)} different instances",
        )

        # Manager should have exactly ONE session
        self.assertEqual(
            self.session_manager.get_session_count(),
            1,
            "Manager should have exactly one session after concurrent access",
        )

        # This test WILL FAIL until race condition is fixed - that's the point!

    @pytest.mark.skip(reason="Threading tests need async adaptation")
    def test_cleanup_race_condition_with_session_revival(self):
        """Test cleanup handles session revival correctly with atomic operations.

        CONTRACT: cleanup_expired_sessions MUST NOT delete sessions that are revived
        during the cleanup process. Sessions that get activity updates should survive.
        """
        session_id = "revival-safety-test"

        # Create session that will initially be expired
        session = self.session_manager.get_or_create_session(session_id, self.temp_dir)
        session.last_activity_at = time.time() - 2.0  # Expired (timeout is 1 second)

        revival_success = False
        cleanup_completed = threading.Event()
        revival_completed = threading.Event()

        def cleanup_thread_func():
            """Thread that attempts to clean up expired sessions"""
            try:
                # Add small delay to let revival thread have a chance
                time.sleep(0.1)
                self.session_manager.cleanup_expired_sessions()
                cleanup_completed.set()
            except Exception:
                cleanup_completed.set()
                raise

        def revival_thread_func():
            """Thread that revives the session by updating activity"""
            nonlocal revival_success
            try:
                # Small delay, then revive session
                time.sleep(0.05)

                revived_session = self.session_manager.get_session(session_id)
                if revived_session:
                    revived_session.update_activity()  # Make it active again
                    revival_success = True
                revival_completed.set()
            except Exception:
                revival_completed.set()
                raise

        # Start both threads
        cleanup_thread = threading.Thread(target=cleanup_thread_func)
        revival_thread = threading.Thread(target=revival_thread_func)

        cleanup_thread.start()
        revival_thread.start()

        # Wait for both to complete
        cleanup_thread.join(timeout=5.0)
        revival_thread.join(timeout=5.0)

        # Verify operations completed
        self.assertTrue(cleanup_completed.is_set(), "Cleanup should have completed")
        self.assertTrue(revival_completed.is_set(), "Revival should have completed")

        # CONTRACT ASSERTION: If session was successfully revived, it MUST still exist
        if revival_success:
            surviving_session = self.session_manager.get_session(session_id)
            self.assertIsNotNone(surviving_session, "Session was revived but was incorrectly deleted by cleanup")
            self.assertFalse(
                surviving_session.is_expired(self.session_manager.session_timeout),
                "Revived session should not be expired",
            )
            print("✓ ATOMIC CLEANUP: Session revival respected, no TOCTOU bug")
        else:
            # If revival failed, that's also a valid outcome
            print("Revival did not succeed, cleanup behavior is acceptable")

    @pytest.mark.skip(reason="Threading tests need async adaptation")
    def test_max_sessions_resource_limit_with_cleanup(self):
        """Test max_sessions resource limit triggers automatic expired session cleanup.

        CONTRACT: When session limit is reached with expired sessions, creating a new
        session must automatically clean up expired sessions and succeed.
        """
        # Create manager with low limit for testing
        test_manager = SessionManager(allowed_workspaces=[self.temp_dir], session_timeout=1.0, max_sessions=3)

        # Fill to limit with sessions that will expire
        expired_sessions = []
        for i in range(3):
            session = test_manager.get_or_create_session(f"expired-{i}", self.temp_dir)
            # Make them expired
            session.last_activity_at = time.time() - 2.0  # Expired
            expired_sessions.append(session)

        self.assertEqual(test_manager.get_session_count(), 3)

        # Creating new session should trigger cleanup and succeed
        new_session = test_manager.get_or_create_session("new-session", self.temp_dir)

        # New session should exist
        self.assertIsNotNone(new_session)
        self.assertEqual(new_session.session_id, "new-session")

        # Old expired sessions should be cleaned up, only new one remains
        self.assertEqual(test_manager.get_session_count(), 1)

        # Verify new session is the only one left
        remaining = test_manager.get_session("new-session")
        self.assertIsNotNone(remaining)

        test_manager.shutdown()

    @pytest.mark.skip(reason="Threading tests need async adaptation")
    def test_max_sessions_limit_enforcement_with_active_sessions(self):
        """Test max_sessions limit enforcement when no expired sessions to clean.

        CONTRACT: When session limit is reached with all active sessions,
        attempting to create a new session must raise specific ValueError.
        """
        # Create manager with low limit
        test_manager = SessionManager(
            allowed_workspaces=[self.temp_dir],
            session_timeout=60,  # Long timeout so sessions stay active
            max_sessions=2,
        )

        # Fill to limit with active sessions
        session1 = test_manager.get_or_create_session("active-1", self.temp_dir)
        session2 = test_manager.get_or_create_session("active-2", self.temp_dir)

        self.assertEqual(test_manager.get_session_count(), 2)

        # Both sessions are active (not expired)
        self.assertFalse(session1.is_expired(test_manager.session_timeout))
        self.assertFalse(session2.is_expired(test_manager.session_timeout))

        # Attempting to create another session should raise ValueError
        with self.assertRaises(ValueError) as context:
            test_manager.get_or_create_session("should-fail", self.temp_dir)

        # Verify specific error message
        error_msg = str(context.exception)
        self.assertIn("Maximum session limit (2) reached", error_msg)
        self.assertIn("Cleaned up 0 expired sessions", error_msg)

        # Original sessions should still exist
        self.assertEqual(test_manager.get_session_count(), 2)
        self.assertIsNotNone(test_manager.get_session("active-1"))
        self.assertIsNotNone(test_manager.get_session("active-2"))

        test_manager.shutdown()

    @pytest.mark.skip(reason="Threading tests need async adaptation")
    def test_max_sessions_automatic_cleanup_preserves_active_sessions(self):
        """Test automatic cleanup correctly identifies and removes only expired sessions.

        CONTRACT: Automatic cleanup during resource limit enforcement must preserve
        active sessions and only remove genuinely expired sessions.
        """
        # Create manager with limit
        test_manager = SessionManager(allowed_workspaces=[self.temp_dir], session_timeout=1.0, max_sessions=4)

        # Create mix of active and expired sessions
        test_manager.get_or_create_session("active", self.temp_dir)
        expired_session1 = test_manager.get_or_create_session("expired-1", self.temp_dir)
        expired_session2 = test_manager.get_or_create_session("expired-2", self.temp_dir)

        # Make some expired
        expired_session1.last_activity_at = time.time() - 2.0  # Expired
        expired_session2.last_activity_at = time.time() - 2.0  # Expired
        # active_session stays fresh

        self.assertEqual(test_manager.get_session_count(), 3)

        # Fill to limit with one more expired
        final_expired = test_manager.get_or_create_session("expired-3", self.temp_dir)
        final_expired.last_activity_at = time.time() - 2.0  # Expired

        self.assertEqual(test_manager.get_session_count(), 4)

        # Creating new session should clean expired ones but preserve active
        test_manager.get_or_create_session("new-active", self.temp_dir)

        # Should have 2 sessions: the original active + new one
        self.assertEqual(test_manager.get_session_count(), 2)

        # Active session should still exist
        surviving_active = test_manager.get_session("active")
        self.assertIsNotNone(surviving_active)
        self.assertFalse(surviving_active.is_expired(test_manager.session_timeout))

        # New session should exist
        self.assertIsNotNone(test_manager.get_session("new-active"))

        # Expired sessions should be gone (SECURITY: now raises exception instead of None)
        # CONTEXT7_BYPASS: INFRA-003 - Internal utils module from same codebase
        from utils.session_manager import SessionNotFoundError

        with self.assertRaises(SessionNotFoundError):
            test_manager.get_session("expired-1")
        with self.assertRaises(SessionNotFoundError):
            test_manager.get_session("expired-2")
        with self.assertRaises(SessionNotFoundError):
            test_manager.get_session("expired-3")

        test_manager.shutdown()

    async def test_get_session_info(self):
        """Test getting session manager information."""
        # Create a test session
        session_id = "info-test-session"
        await self.session_manager.get_or_create_session(session_id=session_id, project_root=self.temp_dir)

        info = await self.session_manager.get_session_info()

        self.assertEqual(info["active_sessions"], 1)
        self.assertIn("allowed_workspaces", info)
        self.assertIn("session_timeout", info)
        self.assertIn("sessions", info)
        self.assertEqual(len(info["sessions"]), 1)
        self.assertEqual(info["sessions"][0]["session_id"], session_id)
