"""
Global Session Registry for HestAI Context Steward.

Provides a persistent, cross-project registry of active sessions to solve
the "lost context" problem where clockout doesn't know the working directory.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GlobalSessionRegistry:
    """
    Manages the global session registry file at ~/.hestai/sessions.registry.json.
    """

    def __init__(self):
        self.registry_dir = Path.home() / ".hestai"
        self.registry_file = self.registry_dir / "sessions.registry.json"
        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        """Ensure the registry directory and file exist."""
        if not self.registry_dir.exists():
            try:
                self.registry_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create global registry dir: {e}")
                return

        if not self.registry_file.exists():
            try:
                self._save_registry({"active_sessions": {}, "version": "1.0"})
            except Exception as e:
                logger.error(f"Failed to initialize global registry file: {e}")

    def _load_registry(self) -> Dict:
        """Load the registry data from disk."""
        if not self.registry_file.exists():
            return {"active_sessions": {}, "version": "1.0"}

        try:
            return json.loads(self.registry_file.read_text())
        except Exception as e:
            logger.error(f"Failed to read registry: {e}")
            return {"active_sessions": {}, "version": "1.0"}

    def _save_registry(self, data: Dict):
        """Save the registry data to disk."""
        try:
            self.registry_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to write registry: {e}")

    def register_session(self, session_id: str, working_dir: str, role: str, focus: str):
        """
        Register a new session.

        Args:
            session_id: The session ID
            working_dir: Absolute path to the project root
            role: Agent role
            focus: Focus area
        """
        data = self._load_registry()

        data["active_sessions"][session_id] = {
            "working_dir": str(working_dir),
            "role": role,
            "focus": focus,
            "started_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }

        self._save_registry(data)
        logger.debug(f"Registered session {session_id} in global registry")

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session details by ID.

        Args:
            session_id: The session ID

        Returns:
            Dict with session info or None
        """
        data = self._load_registry()
        return data["active_sessions"].get(session_id)

    def remove_session(self, session_id: str):
        """
        Remove a session from the registry.

        Args:
            session_id: The session ID to remove
        """
        data = self._load_registry()
        if session_id in data["active_sessions"]:
            del data["active_sessions"][session_id]
            self._save_registry(data)
            logger.debug(f"Removed session {session_id} from global registry")

    def list_active_sessions(self) -> Dict:
        """
        List all active sessions.

        Returns:
            Dict of active sessions
        """
        data = self._load_registry()
        return data.get("active_sessions", {})
