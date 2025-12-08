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

from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ClockInRequest(BaseModel):
    """Request model for clock_in tool"""

    role: str = Field(..., description="Agent role name (e.g., 'implementation-lead', 'critical-engineer')")
    focus: str = Field("general", description="Work focus area (e.g., 'b2-implementation', 'validation', 'general')")
    working_dir: str = Field(..., description="Project working directory path")


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
            sessions_dir = hestai_dir / "sessions"
            active_dir = sessions_dir / "active"
            context_dir = hestai_dir / "context"

            active_dir.mkdir(parents=True, exist_ok=True)
            context_dir.mkdir(parents=True, exist_ok=True)

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
                # Store transcript_path if available from context (for clockout JSONL extraction)
                "transcript_path": getattr(session_context, "transcript_path", None) if session_context else None,
            }

            session_file = session_dir / "session.json"
            session_file.write_text(json.dumps(session_data, indent=2))

            logger.info(f"Created session {session_id} for {request.role} (focus: {request.focus})")

            # Build context paths (relative to project root)
            context_paths = {
                "project_context": ".hestai/context/PROJECT-CONTEXT.md",
                "checklist": ".hestai/context/PROJECT-CHECKLIST.md",
            }

            # Create response content
            content = {
                "session_id": session_id,
                "context_paths": context_paths,
                "conflict": conflict,
                "instruction": "Read context_paths. Produce Full RAPH. Submit anchor.",
            }

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

    def get_model_category(self) -> ToolModelCategory:
        """Return the model category for this tool"""
        return ToolModelCategory.FAST_RESPONSE  # Utility tool, no AI needed
