"""
ClockOut Tool - Extract and archive session transcript

This tool enables agents to "clock out" when ending a work session,
extracting the Claude session JSONL transcript and archiving it.

Part of the Context Steward session lifecycle management system.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.types import TextContent
from pydantic import BaseModel, Field, field_validator

from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ClockOutRequest(BaseModel):
    """Request model for clock_out tool"""

    session_id: str = Field(..., description="Session ID from clock_in")
    description: str = Field("", description="Optional session summary/description")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session_id to prevent path traversal attacks"""
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        # Path traversal prevention
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid session_id format - path separators not allowed")
        return v.strip()


class ClockOutTool(BaseTool):
    """
    Context Steward tool for extracting and archiving session transcripts.

    Extracts JSONL from Claude session, formats as readable transcript,
    and archives to .hestai/sessions/archive/.
    """

    def get_name(self) -> str:
        return "clockout"

    def get_description(self) -> str:
        return (
            "CONTEXT STEWARD - Extract and archive session transcript. "
            "Parses Claude session JSONL, creates readable archive, and cleans up active session."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID from clock_in"},
                "description": {
                    "type": "string",
                    "description": "Optional session summary/description",
                    "default": "",
                },
            },
            "required": ["session_id"],
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """This tool modifies filesystem (creates archive, removes session)"""
        return None  # Not read-only - modifies session directories

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool"""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation"""
        return ClockOutRequest

    def requires_model(self) -> bool:
        """This is a utility tool that doesn't need an AI model"""
        return False

    async def prepare_prompt(self, request: ClockOutRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: ClockOutRequest, model_info: dict = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Extract and archive session transcript.

        Finds Claude session JSONL, parses messages, creates readable archive,
        and removes active session directory.

        Args:
            arguments: Tool arguments containing session_id, description

        Returns:
            Session archive response with summary, archive_path, message_count
        """
        try:
            # Validate request
            request = ClockOutRequest(**arguments)

            # Get project root (from session context or cwd)
            session_context = arguments.get("_session_context")
            if session_context:
                project_root = Path(session_context.project_root)
            else:
                project_root = Path.cwd()

            # Verify .hestai directory exists
            hestai_dir = project_root / ".hestai"
            sessions_dir = hestai_dir / "sessions"
            active_dir = sessions_dir / "active"
            archive_dir = sessions_dir / "archive"

            if not active_dir.exists():
                raise FileNotFoundError(f"Active sessions directory not found: {active_dir}")

            # Verify session exists
            session_dir = active_dir / request.session_id
            if not session_dir.exists():
                raise FileNotFoundError(f"Session {request.session_id} not found in active sessions")

            # Load session metadata
            session_file = session_dir / "session.json"
            if not session_file.exists():
                raise FileNotFoundError(f"Session metadata not found: {session_file}")

            session_data = json.loads(session_file.read_text())

            # Find Claude session JSONL
            jsonl_path = self._find_session_jsonl(project_root)

            # Parse session transcript
            messages = self._parse_session_transcript(jsonl_path)

            # Generate summary
            summary = self._generate_summary(messages, session_data, request.description)

            # Create archive
            archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            focus = session_data.get("focus", "general")
            archive_filename = f"{timestamp}-{focus}-{request.session_id}.txt"
            archive_path = archive_dir / archive_filename

            # Format and write archive
            formatted_transcript = self._format_transcript(messages, session_data, request.description)
            archive_path.write_text(formatted_transcript)

            logger.info(f"Archived session {request.session_id} to {archive_path}")

            # Remove active session directory
            shutil.rmtree(session_dir)
            logger.info(f"Removed active session directory: {session_dir}")

            # Create response content
            content = {
                "summary": summary,
                "archive_path": str(archive_path),
                "message_count": len(messages),
                "session_id": request.session_id,
            }

            tool_output = ToolOutput(
                status="success",
                content=json.dumps(content, indent=2),
                content_type="json",
                metadata={"tool_name": self.name, "session_id": request.session_id},
            )

            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            logger.error(f"Error in clock_out: {str(e)}")
            error_output = ToolOutput(status="error", content=f"Error archiving session: {str(e)}", content_type="text")
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _find_session_jsonl(self, project_root: Path) -> Path:
        """
        Find the most recent Claude session JSONL for this project.

        Args:
            project_root: Project root directory

        Returns:
            Path to session JSONL file

        Raises:
            FileNotFoundError: If no session files found
        """
        # Encode project path using Claude's encoding scheme
        encoded_path = str(project_root).replace("/", "-").lstrip("-")

        # Find session directory
        session_dir = Path.home() / ".claude" / "projects" / encoded_path

        if not session_dir.exists():
            raise FileNotFoundError(f"No Claude session directory found for project: {project_root}")

        # Find most recent JSONL file
        jsonl_files = list(session_dir.glob("*.jsonl"))
        if not jsonl_files:
            raise FileNotFoundError(f"No session JSONL files found in: {session_dir}")

        # Return most recently modified
        return max(jsonl_files, key=lambda p: p.stat().st_mtime)

    def _parse_session_transcript(self, jsonl_path: Path) -> list[dict]:
        """
        Extract user/assistant messages from session JSONL.

        Args:
            jsonl_path: Path to session JSONL file

        Returns:
            List of message dicts with role and content
        """
        messages = []

        with open(jsonl_path) as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type")

                    if entry_type in ("user", "assistant"):
                        role = entry.get("message", {}).get("role", entry_type)
                        content_parts = entry.get("message", {}).get("content", [])
                        text = "\n".join(part.get("text", "") for part in content_parts if part.get("type") == "text")
                        if text:
                            messages.append({"role": role, "content": text})

                    # Note: thinking messages excluded by default as per spec
                    # They can be included in future enhancement with include_thinking flag

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSONL line: {e}")
                    continue

        return messages

    def _generate_summary(self, messages: list[dict], session_data: dict, description: str) -> str:
        """
        Generate a summary of the session.

        Args:
            messages: List of message dicts
            session_data: Session metadata
            description: User-provided description

        Returns:
            Summary string
        """
        role = session_data.get("role", "unknown")
        focus = session_data.get("focus", "general")
        message_count = len(messages)

        summary_parts = [
            f"Session: {role} focused on {focus}",
            f"Messages: {message_count}",
        ]

        if description:
            summary_parts.append(f"Description: {description}")

        return " | ".join(summary_parts)

    def _format_transcript(self, messages: list[dict], session_data: dict, description: str) -> str:
        """
        Format messages as readable transcript.

        Args:
            messages: List of message dicts
            session_data: Session metadata
            description: User-provided description

        Returns:
            Formatted transcript string
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("Claude Code Session Export")
        lines.append(f"Session ID: {session_data.get('session_id', 'unknown')}")
        lines.append(f"Role: {session_data.get('role', 'unknown')}")
        lines.append(f"Focus: {session_data.get('focus', 'general')}")
        lines.append(f"Started: {session_data.get('started_at', 'unknown')}")
        lines.append(f"Exported: {datetime.now().isoformat()}")
        if description:
            lines.append(f"Description: {description}")
        lines.append(f"Working Directory: {session_data.get('working_dir', 'unknown')}")
        lines.append("=" * 80)
        lines.append("")

        # Messages
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            lines.append(f"[{role}]")
            lines.append(content)
            lines.append("")

        # Footer
        lines.append("=" * 80)
        lines.append(f"End of session ({len(messages)} messages)")
        lines.append("=" * 80)

        return "\n".join(lines)

    def get_model_category(self) -> ToolModelCategory:
        """Return the model category for this tool"""
        return ToolModelCategory.FAST_RESPONSE  # Utility tool, no AI needed
