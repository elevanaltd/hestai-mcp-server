"""
Session management for project-aware context isolation in MCP server.

This module provides thread-safe session management with secure project root
validation and lifecycle management for MCP tool instances.
"""

import threading
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import logging

from .file_context_processor import FileContextProcessor

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security boundaries are violated."""
    pass


class SessionNotFoundError(Exception):
    """Raised when a session is not found."""
    pass


class SessionContext:
    """
    Encapsulates session-specific context including project root and tool instances.
    
    Provides secure project root validation and lazy-loaded tool instances
    with proper lifecycle management.
    """
    
    def __init__(self, session_id: str, project_root: str, allowed_workspaces: List[str]):
        """
        Initialize a new session context.
        
        Args:
            session_id: Unique identifier for this session
            project_root: Path to the project root directory
            allowed_workspaces: List of allowed workspace paths for security validation
            
        Raises:
            SecurityError: If project_root is outside allowed workspaces
            ValueError: If project_root is invalid or doesn't exist
        """
        self.session_id = session_id
        self.project_root = self._validate_project_root(project_root, allowed_workspaces)
        self.created_at = time.time()
        self.last_activity_at = time.time()
        
        # Lazy-loaded tool instances
        self._file_context_processor = None
        self._tools_cache = {}
        
        # Session metadata
        self.metadata = {
            'created': datetime.fromtimestamp(self.created_at).isoformat(),
            'project_root': str(self.project_root)
        }
    
    def _validate_project_root(self, project_root: str, allowed_workspaces: List[str]) -> Path:
        """
        Validate that project root is within allowed workspaces.
        
        Args:
            project_root: Path to validate
            allowed_workspaces: List of allowed workspace paths
            
        Returns:
            Resolved Path object for the validated project root
            
        Raises:
            SecurityError: If project root is outside allowed workspaces
            ValueError: If project root doesn't exist or is not a directory
        """
        if not project_root:
            raise ValueError("Project root cannot be empty")
            
        resolved = Path(project_root).resolve()
        
        # Check for dangerous paths first (before existence check)
        dangerous_paths = ["/", "/etc", "/bin", "/sbin", "/usr", "/usr/bin", "/usr/sbin", "/sys", "/proc"]
        # Check both the original path and resolved path
        if (str(project_root) in dangerous_paths or 
            str(resolved) in dangerous_paths or 
            any(str(resolved).startswith(dp + "/") for dp in dangerous_paths if dp != "/")):
            raise SecurityError(f"dangerous path: {project_root}")
        
        # Check if path exists and is a directory
        if not resolved.exists():
            raise ValueError(f"Project root does not exist: {project_root}")
        if not resolved.is_dir():
            raise ValueError(f"Project root is not a directory: {project_root}")
        
        # Security boundary: must be within allowed workspaces
        for workspace in allowed_workspaces:
            workspace_path = Path(workspace).resolve()
            try:
                # Check if resolved path is relative to workspace
                resolved.relative_to(workspace_path)
                return resolved
            except ValueError:
                # Not relative to this workspace, try next
                continue
        
        # Path is outside all allowed workspaces
        raise SecurityError(f"Project root outside allowed workspaces: {project_root}")
    
    def get_file_context_processor(self) -> FileContextProcessor:
        """
        Get or create the FileContextProcessor for this session.
        
        Returns:
            FileContextProcessor instance configured for this session's project root
        """
        if self._file_context_processor is None:
            self._file_context_processor = FileContextProcessor(
                project_root=str(self.project_root)
            )
        self.update_activity()
        return self._file_context_processor
    
    def update_activity(self):
        """Update the last activity timestamp for this session."""
        self.last_activity_at = time.time()
    
    def touch(self):
        """Alias for update_activity() to match test expectations."""
        self.update_activity()
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """
        Check if this session has expired due to inactivity.
        
        Args:
            timeout_seconds: Inactivity timeout in seconds (default: 1 hour)
            
        Returns:
            True if session has been inactive longer than timeout
        """
        return (time.time() - self.last_activity_at) > timeout_seconds
    
    def cleanup(self):
        """Clean up resources associated with this session."""
        # Clear tool instances
        self._file_context_processor = None
        self._tools_cache.clear()
        logger.info(f"Session {self.session_id} cleaned up")


class SessionManager:
    """
    Thread-safe manager for multiple concurrent sessions.
    
    Provides session creation, retrieval, and lifecycle management with
    automatic cleanup of expired sessions.
    """
    
    def __init__(self, allowed_workspaces: Optional[List[str]] = None, session_timeout: int = 3600):
        """
        Initialize the SessionManager.
        
        Args:
            allowed_workspaces: List of allowed workspace paths for security validation.
                               If None, defaults to common workspace locations.
            session_timeout: Session timeout in seconds (default: 3600 = 1 hour)
        """
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = threading.Lock()
        self.session_timeout = session_timeout
        
        # Default allowed workspaces if none provided
        if allowed_workspaces is None:
            self.allowed_workspaces = [
                "/Users",
                "/home",
                "/tmp",
                "/var/tmp",
                "/Volumes"
            ]
        else:
            # Resolve workspace paths to handle symlinks
            self.allowed_workspaces = [str(Path(ws).resolve()) for ws in allowed_workspaces]
        
        # Start background cleanup thread
        self._shutdown = False
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"SessionManager initialized with workspaces: {self.allowed_workspaces}")
    
    def create_session(self, session_id: str, project_root: str) -> SessionContext:
        """
        Create a new session with validated project root.
        
        Args:
            session_id: Unique identifier for the session
            project_root: Path to the project root directory
            
        Returns:
            Created SessionContext instance
            
        Raises:
            ValueError: If session_id already exists
            SecurityError: If project_root is outside allowed workspaces
        """
        with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session {session_id} already exists")
            
            session = SessionContext(session_id, project_root, self.allowed_workspaces)
            self._sessions[session_id] = session
            logger.info(f"Created session {session_id} for project {project_root}")
            return session
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Retrieve an existing session by ID.
        
        Args:
            session_id: Session identifier to retrieve
            
        Returns:
            SessionContext instance or None if not found
            
        Raises:
            SessionNotFoundError: If session doesn't exist (only when strict mode)
        """
        with self._lock:
            if session_id not in self._sessions:
                return None  # Test expects None rather than exception for nonexistent
            
            session = self._sessions[session_id]
            session.update_activity()
            return session
    
    def get_or_create_session(self, session_id: str, project_root: str) -> SessionContext:
        """
        Get existing session or create new one if it doesn't exist.
        
        Args:
            session_id: Session identifier
            project_root: Path to project root (used only if creating new session)
            
        Returns:
            SessionContext instance
        """
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.update_activity()
                return session
            else:
                # Create new session without lock (create_session will acquire it)
                pass
        
        # Create outside lock to avoid deadlock
        return self.create_session(session_id, project_root)
    
    def end_session(self, session_id: str) -> bool:
        """Alias for remove_session() to match test expectations.
        
        Returns:
            True if session was removed, False if it didn't exist
        """
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.cleanup()
                del self._sessions[session_id]
                logger.info(f"Ended session {session_id}")
                return True
            return False
    
    def remove_session(self, session_id: str):
        """
        Remove a session and clean up its resources.
        
        Args:
            session_id: Session identifier to remove
        """
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.cleanup()
                del self._sessions[session_id]
                logger.info(f"Removed session {session_id}")
    
    def get_session_count(self) -> int:
        """Get the number of active sessions.
        
        Returns:
            Number of active sessions
        """
        with self._lock:
            return len(self._sessions)
    
    def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a specific session or all sessions.
        
        Args:
            session_id: Session identifier (if None, returns info for all sessions)
            
        Returns:
            Dictionary with session metadata or manager info
            
        Raises:
            SessionNotFoundError: If specific session doesn't exist
        """
        if session_id is None:
            # Return overall manager info
            with self._lock:
                sessions_list = [
                    {
                        'session_id': session.session_id,
                        'project_root': str(session.project_root),
                        'created_at': session.created_at,
                        'last_activity_at': session.last_activity_at,
                        'is_expired': session.is_expired(self.session_timeout)
                    }
                    for session in self._sessions.values()
                ]
                return {
                    "active_sessions": len(self._sessions),
                    "allowed_workspaces": self.allowed_workspaces,
                    "session_timeout": self.session_timeout,
                    "sessions": sessions_list
                }
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(f"Session {session_id} not found")
            
            session = self._sessions[session_id]
            return {
                'session_id': session.session_id,
                'project_root': str(session.project_root),
                'created_at': session.created_at,
                'last_activity_at': session.last_activity_at,
                'is_expired': session.is_expired(self.session_timeout)
            }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions with metadata.
        
        Returns:
            List of session metadata dictionaries
        """
        with self._lock:
            return [
                {
                    'session_id': session.session_id,
                    'project_root': str(session.project_root),
                    'created_at': session.created_at,
                    'last_activity_at': session.last_activity_at,
                    'is_expired': session.is_expired()
                }
                for session in self._sessions.values()
            ]
    
    def cleanup_expired_sessions(self, timeout_seconds: Optional[int] = None) -> int:
        """
        Remove all expired sessions.
        
        Args:
            timeout_seconds: Inactivity timeout in seconds (default: uses session_timeout)
        """
        if timeout_seconds is None:
            timeout_seconds = self.session_timeout
        with self._lock:
            expired_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if session.is_expired(timeout_seconds)
            ]
        
        # Remove outside lock iteration to avoid modification during iteration
        for session_id in expired_ids:
            self.remove_session(session_id)
            logger.info(f"Cleaned up expired session {session_id}")
        
        return len(expired_ids)
    
    def _cleanup_expired_sessions(self):
        """Background thread to periodically clean up expired sessions."""
        while not self._shutdown:
            time.sleep(300)  # Check every 5 minutes
            if not self._shutdown:
                self.cleanup_expired_sessions(self.session_timeout)
    
    def shutdown(self):
        """Shutdown the session manager and clean up all sessions."""
        self._shutdown = True
        with self._lock:
            for session in self._sessions.values():
                session.cleanup()
            self._sessions.clear()
        logger.info("SessionManager shutdown complete")
