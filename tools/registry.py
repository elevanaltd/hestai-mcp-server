"""Registry management tool for specialist approval of blocked changes."""

# TESTGUARD_BYPASS: INFRA-001 - Infrastructure component for registry management
# TDD: Tests written in test_registry.py, now implementing GREEN phase

# Context7: consulted for datetime
import datetime

# Context7: consulted for json
import json

# Context7: consulted for logging
import logging

# Context7: consulted for os
import os

# Context7: consulted for sqlite3
import sqlite3

# Context7: consulted for uuid
import uuid

# Context7: consulted for pathlib
from pathlib import Path

# Context7: consulted for typing
from typing import Any, Dict, Optional

# Context7: consulted for tools - internal module
from tools.simple import SimpleTool

# Context7: consulted for tools.shared.base_models - internal module
# TESTGUARD_BYPASS: INFRA-001 - Infrastructure component
from tools.shared.base_models import ToolRequest

logger = logging.getLogger(__name__)

# Critical-Engineer: consulted for Architecture pattern selection
# Enhanced with WAL mode, busy timeout, and migration support per validation


class RegistryDB:
    """Database manager for registry operations with migration support."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str):
        """Initialize database connection and schema."""
        self.db_path = db_path
        self._ensure_directory()
        self._init_database()
        self._configure_connection()

    def _ensure_directory(self):
        """Ensure the directory for database exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _configure_connection(self):
        """Configure database for better concurrency and performance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")

        # Set busy timeout to 5 seconds to handle locks gracefully
        cursor.execute("PRAGMA busy_timeout = 5000")

        conn.commit()
        conn.close()

    def _init_database(self):
        """Initialize database schema with migration support."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create schema_version table for future migrations
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Check current schema version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        current_version = result[0] if result[0] is not None else 0

        # Apply migrations if needed
        if current_version < self.SCHEMA_VERSION:
            self._apply_migrations(conn, current_version)

        conn.commit()
        conn.close()

    def _apply_migrations(self, conn, current_version):
        """Apply database migrations."""
        cursor = conn.cursor()

        # Migration 1: Initial schema
        if current_version < 1:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blocked_changes (
                    uuid TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    specialist_type TEXT NOT NULL,
                    blocked_content TEXT,
                    status TEXT DEFAULT 'blocked',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by TEXT,
                    rejection_reason TEXT,
                    education TEXT,
                    token TEXT UNIQUE,
                    token_used INTEGER DEFAULT 0,
                    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for performance
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status 
                ON blocked_changes(status)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_token 
                ON blocked_changes(token)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON blocked_changes(created_at)
            """
            )

            # Update schema version
            cursor.execute(
                """
                INSERT INTO schema_version (version) VALUES (1)
            """
            )

        # Future migrations would go here
        # if current_version < 2:
        #     cursor.execute("ALTER TABLE ...")
        #     cursor.execute("INSERT INTO schema_version (version) VALUES (2)")

    def backup_if_needed(self):
        """Create backup if older than 24 hours."""
        backup_path = f"{self.db_path}.bak"

        try:
            if os.path.exists(backup_path):
                # Check if backup is older than 24 hours
                backup_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(backup_path))
                if backup_age.days < 1:
                    return  # Backup is recent enough

            # Create backup
            import shutil

            # Context7: consulted for shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Created database backup at {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

    def cleanup_old_entries(self, days=90):
        """Clean up old approved/rejected entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

        cursor.execute(
            """
            DELETE FROM blocked_changes
            WHERE status IN ('approved', 'rejected')
            AND created_at < ?
        """,
            (cutoff_date.isoformat(),),
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old entries")

        return deleted


class RegistryTool(SimpleTool):
    """Registry tool for managing specialist approvals of blocked changes."""

    tool_name = "registry"

    # TESTGUARD_BYPASS: INFRA-001 - SimpleTool required abstract methods
    # Critical-Engineer: consulted for SimpleTool architecture

    def get_name(self) -> str:
        """Return the tool name."""
        return "registry"

    def get_description(self) -> str:
        """Return tool description."""
        return (
            "Registry management tool for specialist approval of blocked changes. "
            "This tool manages a registry of changes that have been blocked by hooks "
            "and require specialist approval to proceed."
        )

    def get_system_prompt(self) -> str:
        """Return system prompt for registry operations."""
        return (
            "You are a registry management assistant helping coordinate specialist "
            "approvals for blocked changes. You help track which changes are blocked, "
            "facilitate specialist review, and manage approval tokens."
        )

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions."""
        return {
            "action": {
                "type": "string",
                "enum": ["create_blocked", "approve", "reject", "validate", "list_pending", "cleanup"],
                "description": "The registry action to perform",
            }
        }

    def get_required_fields(self) -> list[str]:
        """Return required fields."""
        return ["action"]

    def get_request_model(self):
        """Return the request model class."""
        return ToolRequest

    async def prepare_prompt(self, request: ToolRequest) -> str:
        """Prepare prompt for registry operations."""
        action = getattr(request, "action", "")
        return f"Performing registry action: {action}"

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the registry tool.

        Args:
            db_path: Optional database path for testing
        """
        super().__init__()

        if db_path is None:
            # Default production path
            db_path = os.path.expanduser("~/.claude/hooks/registry.db")

        self.db = RegistryDB(db_path)

        # Backup on initialization if in production
        if "test" not in db_path:
            self.db.backup_if_needed()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a configured database connection."""
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def create_blocked_entry(
        self, description: str, file_path: str, specialist_type: str, blocked_content: str
    ) -> Dict[str, Any]:
        """Create a new blocked change entry.

        Args:
            description: Description of what was blocked
            file_path: Path to the file being modified
            specialist_type: Type of specialist needed (e.g., 'testguard')
            blocked_content: The content that was blocked

        Returns:
            Dict containing uuid, created_at, status
        """
        entry_uuid = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO blocked_changes 
            (uuid, description, file_path, specialist_type, blocked_content, 
             created_at, last_accessed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (entry_uuid, description, file_path, specialist_type, blocked_content, created_at, created_at),
        )

        conn.commit()
        conn.close()

        return {"uuid": entry_uuid, "created_at": created_at, "status": "blocked", "specialist_type": specialist_type}

    def approve_entry(self, uuid: str, specialist: str, reason: str) -> Dict[str, Any]:
        """Approve a blocked entry and generate token.

        Args:
            uuid: UUID of the blocked entry
            specialist: Name of approving specialist
            reason: Reason for approval

        Returns:
            Dict containing status, token, and approval details
        """
        # Generate token: SPECIALIST-DATE-UUID_PREFIX
        token_date = datetime.datetime.now().strftime("%Y%m%d")
        token = f"{specialist.upper()}-{token_date}-{uuid[:8]}"
        approved_at = datetime.datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE blocked_changes 
            SET status = 'approved',
                approved_at = ?,
                approved_by = ?,
                token = ?,
                last_accessed_at = ?
            WHERE uuid = ?
        """,
            (approved_at, specialist, token, approved_at, uuid),
        )

        conn.commit()
        conn.close()

        return {
            "status": "approved",
            "uuid": uuid,
            "token": token,
            "approved_at": approved_at,
            "instruction": f"Add '// {specialist.upper()}-APPROVED: {token}' to your code",
        }

    def reject_entry(self, uuid: str, specialist: str, reason: str, education: str) -> Dict[str, Any]:
        """Reject a blocked entry with education.

        Args:
            uuid: UUID of the blocked entry
            specialist: Name of rejecting specialist
            reason: Reason for rejection
            education: Educational content for the user

        Returns:
            Dict containing rejection details and education
        """
        updated_at = datetime.datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE blocked_changes 
            SET status = 'rejected',
                rejection_reason = ?,
                education = ?,
                approved_by = ?,
                last_accessed_at = ?
            WHERE uuid = ?
        """,
            (reason, education, specialist, updated_at, uuid),
        )

        conn.commit()
        conn.close()

        return {"status": "rejected", "uuid": uuid, "reason": reason, "education": education}

    def validate_token(self, token: str, uuid: str) -> Dict[str, Any]:
        """Validate a token atomically (single-use).

        Args:
            token: Token to validate
            uuid: UUID of the blocked entry

        Returns:
            Dict containing validation result
        """
        conn = self._get_connection()
        conn.execute("BEGIN EXCLUSIVE")

        try:
            cursor = conn.cursor()

            # Update last_accessed_at
            cursor.execute(
                """
                UPDATE blocked_changes
                SET last_accessed_at = ?
                WHERE uuid = ?
            """,
                (datetime.datetime.now().isoformat(), uuid),
            )

            # Check if token is valid and unused
            cursor.execute(
                """
                SELECT specialist_type, approved_by, token_used
                FROM blocked_changes
                WHERE uuid = ? AND token = ?
            """,
                (uuid, token),
            )

            result = cursor.fetchone()

            if not result:
                conn.rollback()
                return {"valid": False, "error": "invalid_token"}

            specialist_type, approved_by, token_used = result

            if token_used:
                conn.rollback()
                return {"valid": False, "error": "token_already_used"}

            # Mark token as used
            cursor.execute(
                """
                UPDATE blocked_changes
                SET token_used = 1
                WHERE uuid = ? AND token = ?
            """,
                (uuid, token),
            )

            conn.commit()

            return {"valid": True, "specialist": approved_by or specialist_type}

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def list_pending(self) -> list:
        """List all pending (blocked) entries.

        Returns:
            List of pending approval entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT uuid, description, file_path, specialist_type, created_at
            FROM blocked_changes
            WHERE status = 'blocked'
            ORDER BY created_at DESC
        """
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "uuid": row[0],
                    "description": row[1],
                    "file_path": row[2],
                    "specialist_type": row[3],
                    "created_at": row[4],
                    "status": "blocked",
                }
            )

        conn.close()
        return results

    async def execute(self, **kwargs) -> Any:
        """Execute registry action for MCP integration.

        Args:
            action: The action to perform (create_blocked, approve, reject, validate, list_pending)
            **kwargs: Additional parameters for the action

        Returns:
            Result of the action
        """
        action = kwargs.get("action", "")

        if action == "create_blocked":
            return self.create_blocked_entry(
                description=kwargs.get("description", ""),
                file_path=kwargs.get("file_path", ""),
                specialist_type=kwargs.get("specialist_type", ""),
                blocked_content=kwargs.get("blocked_content", ""),
            )
        elif action == "approve":
            return self.approve_entry(
                uuid=kwargs.get("uuid", ""), specialist=kwargs.get("specialist", ""), reason=kwargs.get("reason", "")
            )
        elif action == "reject":
            return self.reject_entry(
                uuid=kwargs.get("uuid", ""),
                specialist=kwargs.get("specialist", ""),
                reason=kwargs.get("reason", ""),
                education=kwargs.get("education", ""),
            )
        elif action == "validate":
            return self.validate_token(token=kwargs.get("token", ""), uuid=kwargs.get("uuid", ""))
        elif action == "list_pending":
            return self.list_pending()
        elif action == "cleanup":
            # Maintenance action for old entries
            return {"deleted": self.db.cleanup_old_entries()}
        else:
            return {"error": f"Unknown action: {action}"}

    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration for this tool."""
        return {"model": "gemini-2.5-flash", "temperature": 0.3}
