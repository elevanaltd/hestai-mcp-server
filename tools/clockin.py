"""
ClockIn Tool - Register agent session start

This tool enables agents to "clock in" when starting a work session,
creating session metadata and checking for focus conflicts.

Part of the Context Steward session lifecycle management system.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.types import TextContent
from pydantic import BaseModel, Field

from tools.context_steward.context_validator import (
    validate_context_negatives,
    validate_state_vector,
)
from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ClockInRequest(BaseModel):
    """Request model for clock_in tool"""

    role: str = Field(..., description="Agent role name (e.g., 'implementation-lead', 'critical-engineer')")
    focus: str = Field("general", description="Work focus area (e.g., 'b2-implementation', 'validation', 'general')")
    working_dir: str = Field(..., description="Project working directory path")
    model: str | None = Field(None, description="AI model identifier (e.g., 'claude-opus-4-5-20251101')")


class ClockInTool(BaseTool):
    """
    Context Steward tool for registering session start.

    Creates session directory, detects focus conflicts, and returns
    context paths for agent consumption.
    """

    def get_name(self) -> str:
        return "clockin"

    def get_description(self) -> str:
        return (
            "CONTEXT STEWARD - Register agent session start. Creates session directory, "
            "detects focus conflicts, and returns context paths for agent initialization."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Agent role name (e.g., 'implementation-lead', 'critical-engineer')",
                },
                "focus": {
                    "type": "string",
                    "description": "Work focus area (e.g., 'b2-implementation', 'validation', 'general')",
                    "default": "general",
                },
                "working_dir": {"type": "string", "description": "Project working directory path"},
                "model": {
                    "type": ["string", "null"],
                    "description": "AI model identifier (e.g., 'claude-opus-4-5-20251101')",
                    "default": None,
                },
            },
            "required": ["role", "working_dir"],
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """This tool modifies filesystem (creates session directory)"""
        return None  # Not read-only - creates session directories

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool"""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation"""
        return ClockInRequest

    def requires_model(self) -> bool:
        """This is a utility tool that doesn't need an AI model"""
        return False

    async def prepare_prompt(self, request: ClockInRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: ClockInRequest, model_info: dict = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Register agent session start.

        Creates session directory in .hestai/sessions/active/, detects focus
        conflicts with existing sessions, and returns context paths.

        Args:
            arguments: Tool arguments containing role, focus, working_dir

        Returns:
            Session registration response with session_id, context_paths, conflict info
        """
        try:
            # Validate request
            request = ClockInRequest(**arguments)

            # Get project root (from session context or working_dir)
            session_context = arguments.get("_session_context")
            if session_context:
                project_root = Path(session_context.project_root)
            else:
                project_root = Path(request.working_dir)

            # Ensure .hestai directory structure exists
            hestai_dir = project_root / ".hestai"

            # Resolve symlink if .hestai is symlinked to unified location
            if hestai_dir.is_symlink():
                resolved_path = hestai_dir.resolve()
                logger.info(f"Resolved .hestai symlink to: {resolved_path}")
                hestai_dir = resolved_path

            sessions_dir = hestai_dir / "sessions"
            active_dir = sessions_dir / "active"
            context_dir = hestai_dir / "context"

            active_dir.mkdir(parents=True, exist_ok=True)
            context_dir.mkdir(parents=True, exist_ok=True)

            # Trigger daily cleanup if needed (non-blocking)
            try:
                self._check_and_trigger_cleanup(hestai_dir)
            except Exception as e:
                logger.warning(f"Cleanup check failed (non-blocking): {e}")

            # Generate session ID (short UUID)
            session_id = str(uuid.uuid4())[:8]

            # Check for focus conflicts
            conflict = self._check_focus_conflict(active_dir, request.focus, session_id)

            # Create session directory
            session_dir = active_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Create session metadata
            session_data = {
                "session_id": session_id,
                "role": request.role,
                "focus": request.focus,
                "working_dir": str(project_root),
                "started_at": datetime.now().isoformat(),
                "model": request.model,
                # Store transcript_path if available from context (for clockout JSONL extraction)
                "transcript_path": getattr(session_context, "transcript_path", None) if session_context else None,
            }

            session_file = session_dir / "session.json"
            session_file.write_text(json.dumps(session_data, indent=2))

            # GLOBAL REGISTRY: Register session for cross-context discovery
            try:
                from tools.shared.global_registry import GlobalSessionRegistry

                registry = GlobalSessionRegistry()
                registry.register_session(
                    session_id=session_id,
                    working_dir=str(project_root),
                    role=request.role,
                    focus=request.focus,
                )
            except Exception as e:
                logger.warning(f"Failed to register session globally: {e}")

            logger.info(f"Created session {session_id} for {request.role} (focus: {request.focus})")

            # Build context paths (relative to project root)
            context_paths = {
                "project_context": ".hestai/context/PROJECT-CONTEXT.md",
                "checklist": ".hestai/context/PROJECT-CHECKLIST.md",
            }

            # Load and validate state vector if exists
            state_vector_data = self._load_state_vector(context_dir)

            # Load and validate context negatives if exists
            context_negatives_data = self._load_context_negatives(context_dir)

            # Create response content
            content = {
                "session_id": session_id,
                "context_paths": context_paths,
                "conflict": conflict,
                "instruction": "Read context_paths. Produce Full RAPH. Submit anchor.",
            }

            # Add state vector if available and valid
            if state_vector_data:
                content.update(state_vector_data)

            # Add context negatives if available and valid
            if context_negatives_data:
                content.update(context_negatives_data)

            tool_output = ToolOutput(
                status="success",
                content=json.dumps(content, indent=2),
                content_type="json",
                metadata={"tool_name": self.name, "session_id": session_id},
            )

            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            logger.error(f"Error in clock_in: {str(e)}")
            error_output = ToolOutput(
                status="error", content=f"Error registering session: {str(e)}", content_type="text"
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _check_focus_conflict(self, active_dir: Path, focus: str, current_session_id: str) -> Optional[dict]:
        """
        Check if another session is active with the same focus.

        Args:
            active_dir: Path to sessions/active directory
            focus: Focus area to check
            current_session_id: Current session ID to exclude from conflict check

        Returns:
            Conflict info dict if conflict exists, None otherwise
        """
        if not active_dir.exists():
            return None

        for session_dir in active_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Skip current session
            if session_dir.name == current_session_id:
                continue

            session_file = session_dir / "session.json"
            if not session_file.exists():
                continue

            try:
                session_data = json.loads(session_file.read_text())

                # Check if focus matches
                if session_data.get("focus") == focus:
                    return {
                        "focus": focus,
                        "existing_session_id": session_data.get("session_id"),
                        "existing_role": session_data.get("role"),
                        "started_at": session_data.get("started_at"),
                        "message": f"Another session ({session_data.get('role')}) is already active with focus '{focus}'",
                    }

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not parse session file {session_file}: {e}")
                continue

        return None

    def _load_state_vector(self, context_dir: Path) -> Optional[dict]:
        """
        Load and validate state vector if it exists.

        Args:
            context_dir: Path to .hestai/context directory

        Returns:
            Dict with state_vector key if valid, None otherwise
        """
        state_vector_path = context_dir / "current_state.oct"

        if not state_vector_path.exists():
            return None

        try:
            content = state_vector_path.read_text()

            # Validate before including
            validation = validate_state_vector(content)

            if validation.is_valid:
                # Include content directly if < 1KB, otherwise include path
                if len(content) < 1024:
                    logger.info("Including state vector content in clock_in response")
                    return {"state_vector": content}
                else:
                    logger.info("State vector > 1KB, including path instead")
                    return {"state_vector": str(state_vector_path)}
            else:
                logger.warning(f"State vector validation failed: {', '.join(validation.errors)}")
                return {"validation_warning": f"State vector invalid: {', '.join(validation.errors)}"}

        except Exception as e:
            logger.error(f"Error loading state vector: {e}")
            return None

    def _load_context_negatives(self, context_dir: Path) -> Optional[dict]:
        """
        Load and validate context negatives if they exist.

        Args:
            context_dir: Path to .hestai/context directory

        Returns:
            Dict with context_negatives key if valid, None otherwise
        """
        negatives_path = context_dir / "CONTEXT-NEGATIVES.oct"

        if not negatives_path.exists():
            return None

        try:
            content = negatives_path.read_text()

            # Validate before including
            validation = validate_context_negatives(content)

            if validation.is_valid:
                # Include content directly if < 1KB, otherwise include path
                if len(content) < 1024:
                    logger.info("Including context negatives in clock_in response")
                    return {"context_negatives": content}
                else:
                    logger.info("Context negatives > 1KB, including path instead")
                    return {"context_negatives": str(negatives_path)}
            else:
                logger.warning(f"Context negatives validation failed: {', '.join(validation.errors)}")
                return {"validation_warning": f"Context negatives invalid: {', '.join(validation.errors)}"}

        except Exception as e:
            logger.error(f"Error loading context negatives: {e}")
            return None

    def get_model_category(self) -> ToolModelCategory:
        """Return the model category for this tool"""
        return ToolModelCategory.FAST_RESPONSE  # Utility tool, no AI needed

    def _check_and_trigger_cleanup(self, hestai_dir: Path) -> None:
        """
        Check if cleanup should run (> 24h since last run) and trigger if needed.

        This is a non-blocking operation - errors are logged but don't fail clockin.

        Args:
            hestai_dir: Path to .hestai directory
        """
        last_cleanup_file = hestai_dir / "last_cleanup"

        # Check if we need to run cleanup
        should_cleanup = False

        if not last_cleanup_file.exists():
            # First run - create the file and run cleanup
            should_cleanup = True
        else:
            try:
                last_cleanup_str = last_cleanup_file.read_text().strip()
                last_cleanup = datetime.fromisoformat(last_cleanup_str)
                hours_since_cleanup = (datetime.now() - last_cleanup).total_seconds() / 3600

                if hours_since_cleanup > 24:
                    should_cleanup = True
                    logger.info(f"Last cleanup was {hours_since_cleanup:.1f}h ago - triggering cleanup")
            except (ValueError, OSError) as e:
                logger.warning(f"Could not parse last_cleanup timestamp: {e} - will run cleanup")
                should_cleanup = True

        if should_cleanup:
            logger.info("Triggering session cleanup")
            self._run_cleanup(hestai_dir)

            # Update last_cleanup timestamp
            last_cleanup_file.write_text(datetime.now().isoformat())

    def _run_cleanup(self, hestai_dir: Path) -> None:
        """
        Run cleanup of old archived sessions and stale active sessions.

        Retention policy:
        - Archive JSONL files: Delete if > 30 days old
        - Active sessions: Delete if > 24h old (stale)

        Args:
            hestai_dir: Path to .hestai directory
        """

        sessions_dir = hestai_dir / "sessions"
        archive_dir = sessions_dir / "archive"
        active_dir = sessions_dir / "active"

        now = datetime.now()
        archive_retention_days = 30
        stale_session_hours = 24

        # Cleanup old archives
        if archive_dir.exists():
            for archive_file in archive_dir.glob("*.jsonl"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
                    age_days = (now - mtime).days

                    if age_days > archive_retention_days:
                        logger.info(f"Deleting old archive ({age_days}d): {archive_file.name}")
                        archive_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup archive {archive_file.name}: {e}")

        # Cleanup stale active sessions
        if active_dir.exists():
            for session_dir in active_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                session_file = session_dir / "session.json"
                if not session_file.exists():
                    continue

                try:
                    session_data = json.loads(session_file.read_text())
                    started_at_str = session_data.get("started_at")

                    if started_at_str:
                        started_at = datetime.fromisoformat(started_at_str)
                        age_hours = (now - started_at).total_seconds() / 3600

                        if age_hours > stale_session_hours:
                            logger.info(f"Deleting stale session ({age_hours:.1f}h): {session_dir.name}")
                            # Delete entire session directory
                            import shutil

                            shutil.rmtree(session_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup session {session_dir.name}: {e}")
