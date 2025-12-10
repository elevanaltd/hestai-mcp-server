"""
ClockOut Tool - Extract and archive session transcript

This tool enables agents to "clock out" when ending a work session,
extracting the Claude session JSONL transcript and archiving it.

Part of the Context Steward session lifecycle management system.
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.types import TextContent
from pydantic import BaseModel, Field, field_validator

from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Security and performance constants
MAX_PROJECTS_SCAN = 50  # DoS prevention for metadata inversion
MAX_SCAN_TIME = 2.0  # Timeout in seconds
TEMPORAL_BEACON_MAX_AGE_HOURS = 24  # Only scan files modified in last 24h


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

            # Find Claude session JSONL using dual-path resolution
            jsonl_path = self._resolve_transcript_path(session_data, project_root)

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

            # AI compression (optional - graceful degradation)
            # Controlled by conf/context_steward.json enabled flag
            from tools.context_steward.ai import ContextStewardAI

            try:
                ai = ContextStewardAI()
                if ai.is_task_enabled("session_compression"):
                    result = await ai.run_task(
                        "session_compression",
                        session_id=request.session_id,
                        role=session_data.get("role", "unknown"),
                        duration=session_data.get("duration", "unknown"),
                        branch=session_data.get("branch", "main"),
                        working_dir=str(project_root),  # For signal gathering
                        transcript_path=str(archive_path),
                    )
                    if result.get("status") == "success":
                        # Save octave summary
                        octave_path = archive_path.with_suffix(".oct.md")
                        artifacts = result.get("artifacts", [])
                        if artifacts:
                            octave_content = artifacts[0].get("content", "")

                            # Defensive check: AI must return substantial OCTAVE content
                            MIN_OCTAVE_LENGTH = 300  # Minimum for meaningful compression
                            if len(octave_content) < MIN_OCTAVE_LENGTH:
                                logger.warning(
                                    f"AI returned truncated OCTAVE content ({len(octave_content)} chars), "
                                    f"expected at least {MIN_OCTAVE_LENGTH}. Skipping OCTAVE file creation."
                                )
                            else:
                                octave_path.write_text(octave_content)
                                logger.info(f"AI compression saved to {octave_path}")
            except Exception as e:
                logger.warning(f"AI compression skipped: {e}")
                # Graceful degradation - continue without AI

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

    def _validate_path_containment(self, input_path: Path, allowed_root: Optional[Path] = None) -> Path:
        """
        Validate path is within allowed Claude projects directory.

        Args:
            input_path: Path to validate
            allowed_root: Optional custom allowed root (defaults to ~/.claude/projects)

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path traversal attempt detected
        """
        if allowed_root is None:
            allowed_root = Path("~/.claude/projects").expanduser().resolve()
        else:
            allowed_root = allowed_root.expanduser().resolve()

        target_path = input_path.expanduser().resolve()

        if not target_path.is_relative_to(allowed_root):
            raise ValueError(f"Path traversal attempt: {target_path} not within {allowed_root}")

        return target_path

    def _find_by_temporal_beacon(self, session_id: str, claude_projects: Optional[Path] = None) -> Path:
        """
        Layer 1: Find JSONL by scanning recently modified files for session_id content.

        The clockout command writes to the JSONL log, so the session_id is guaranteed
        to be present in the file. Temporal filter (24h) provides I/O efficiency.

        Args:
            session_id: Unique session identifier to search for
            claude_projects: Optional path to Claude projects directory

        Returns:
            Path to JSONL file containing session_id

        Raises:
            FileNotFoundError: If no matching file found in last 24h
        """
        if claude_projects is None:
            claude_projects = Path("~/.claude/projects").expanduser()

        # Validate path containment
        claude_projects = self._validate_path_containment(claude_projects)

        if not claude_projects.exists():
            raise FileNotFoundError(f"Claude projects directory not found: {claude_projects}")

        # Calculate cutoff time (24h ago)
        cutoff_time = time.time() - (TEMPORAL_BEACON_MAX_AGE_HOURS * 60 * 60)

        # Scan all JSONL files modified in last 24h
        for project_dir in claude_projects.iterdir():
            if not project_dir.is_dir():
                continue

            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    # Check modification time first (I/O efficiency)
                    if jsonl_file.stat().st_mtime < cutoff_time:
                        continue

                    # Scan file content for session_id
                    with open(jsonl_file) as f:
                        for line in f:
                            if session_id in line:
                                logger.debug(f"Found session_id via temporal beacon: {jsonl_file}")
                                return jsonl_file

                except OSError as e:
                    logger.warning(f"Error reading {jsonl_file}: {e}")
                    continue

        raise FileNotFoundError(
            f"No JSONL file found containing session_id {session_id} in last {TEMPORAL_BEACON_MAX_AGE_HOURS}h"
        )

    def _find_by_metadata_inversion(self, project_root: Path, claude_projects: Optional[Path] = None) -> Path:
        """
        Layer 2: Find JSONL by scanning project_config.json files to match project root.

        Args:
            project_root: Project root directory to match
            claude_projects: Optional path to Claude projects directory

        Returns:
            Path to most recent JSONL file in matched project directory

        Raises:
            FileNotFoundError: If no matching project or JSONL found, or MAX_PROJECTS_SCAN exceeded
        """
        if claude_projects is None:
            claude_projects = Path("~/.claude/projects").expanduser()

        # Validate path containment
        claude_projects = self._validate_path_containment(claude_projects)

        if not claude_projects.exists():
            raise FileNotFoundError(f"Claude projects directory not found: {claude_projects}")

        project_root = project_root.resolve()
        scanned_count = 0
        start_time = time.time()

        # Scan project directories
        for project_dir in claude_projects.iterdir():
            if not project_dir.is_dir():
                continue

            scanned_count += 1

            # DoS prevention: enforce MAX_PROJECTS_SCAN limit
            if scanned_count > MAX_PROJECTS_SCAN:
                raise FileNotFoundError(
                    f"MAX_PROJECTS_SCAN ({MAX_PROJECTS_SCAN}) exceeded - "
                    f"use explicit config or temporal beacon instead"
                )

            # Timeout protection
            if time.time() - start_time > MAX_SCAN_TIME:
                raise FileNotFoundError(f"Metadata inversion timeout ({MAX_SCAN_TIME}s) exceeded")

            # Check for project_config.json
            config_file = project_dir / "project_config.json"
            if not config_file.exists():
                continue

            try:
                config = json.loads(config_file.read_text())
                config_root = Path(config.get("rootPath", "")).resolve()

                if config_root == project_root:
                    # Found matching project - find most recent JSONL
                    jsonl_files = list(project_dir.glob("*.jsonl"))
                    if not jsonl_files:
                        raise FileNotFoundError(f"No JSONL files in matched project: {project_dir}")

                    most_recent = max(jsonl_files, key=lambda p: p.stat().st_mtime)
                    logger.debug(f"Found JSONL via metadata inversion: {most_recent}")
                    return most_recent

            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error reading {config_file}: {e}")
                continue

        raise FileNotFoundError(f"No project_config.json found matching project root: {project_root}")

    def _find_by_explicit_config(self, session_id: str) -> Path:
        """
        Layer 3: Find JSONL via explicit configuration (CLAUDE_TRANSCRIPT_DIR env var).

        Args:
            session_id: Session identifier to locate file

        Returns:
            Path to JSONL file in configured directory

        Raises:
            FileNotFoundError: If env var not set or no matching file found
        """
        transcript_dir = os.environ.get("CLAUDE_TRANSCRIPT_DIR")

        if not transcript_dir:
            raise FileNotFoundError("CLAUDE_TRANSCRIPT_DIR environment variable not set")

        # The env var IS the allowed root (escape hatch for custom locations)
        custom_root = Path(transcript_dir).expanduser().resolve()

        if not custom_root.exists():
            raise FileNotFoundError(f"CLAUDE_TRANSCRIPT_DIR does not exist: {custom_root}")

        # Find JSONL file containing session_id
        for jsonl_file in custom_root.rglob("*.jsonl"):
            try:
                # Validate that found file is within the custom root (not outside via symlink)
                if not jsonl_file.resolve().is_relative_to(custom_root):
                    logger.warning(f"Skipping {jsonl_file} - outside custom root")
                    continue

                with open(jsonl_file) as f:
                    for line in f:
                        if session_id in line:
                            logger.debug(f"Found session_id via explicit config: {jsonl_file}")
                            return jsonl_file
            except OSError as e:
                logger.warning(f"Error reading {jsonl_file}: {e}")
                continue

        raise FileNotFoundError(f"No JSONL file containing session_id {session_id} in {custom_root}")

    def _resolve_transcript_path(self, session_data: dict, project_root: Path) -> Path:
        """
        Layered transcript resolution with security validation.

        Resolution order:
        1. Hook-provided path (deterministic, from clockin)
        2. Temporal beacon (scan recent files for session_id)
        3. Metadata inversion (match project_root via project_config.json)
        4. Explicit config (CLAUDE_TRANSCRIPT_DIR env var)
        5. Legacy fallback (Claude path encoding - kept for compatibility)

        Args:
            session_data: Session metadata dict
            project_root: Project root directory

        Returns:
            Path to session JSONL file

        Raises:
            FileNotFoundError: If no transcript found via any method
        """
        session_id = session_data.get("session_id", "")

        # Layer 0: Hook-provided path (existing behavior - highest priority)
        if session_data.get("transcript_path"):
            provided = Path(session_data["transcript_path"])
            if provided.exists():
                try:
                    # Security: validate hook-provided path is within allowed sandbox
                    # Respect CLAUDE_TRANSCRIPT_DIR if set as custom allowed root
                    custom_root = os.environ.get("CLAUDE_TRANSCRIPT_DIR")
                    allowed_root = Path(custom_root) if custom_root else None
                    validated = self._validate_path_containment(provided, allowed_root)
                    logger.debug("Using hook-provided transcript path")
                    return validated
                except ValueError as e:
                    logger.warning(f"Hook path failed containment check ({e}), falling back to discovery")
            else:
                logger.warning("Hook path missing, falling back to discovery")

        # Layer 1: Temporal beacon (efficient for recent sessions)
        if session_id:
            try:
                return self._find_by_temporal_beacon(session_id)
            except FileNotFoundError as e:
                logger.debug(f"Temporal beacon failed: {e}")

        # Layer 2: Metadata inversion (robust cross-project discovery)
        try:
            return self._find_by_metadata_inversion(project_root)
        except FileNotFoundError as e:
            logger.debug(f"Metadata inversion failed: {e}")

        # Layer 3: Explicit config (escape hatch for custom setups)
        if session_id:
            try:
                return self._find_by_explicit_config(session_id)
            except FileNotFoundError as e:
                logger.debug(f"Explicit config failed: {e}")

        # Layer 4: Legacy fallback (existing _find_session_jsonl for compatibility)
        logger.debug("Falling back to legacy path encoding method")
        return self._find_session_jsonl(project_root)

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

                        # Handle both string and list formats
                        if isinstance(content_parts, str):
                            text = content_parts
                        elif isinstance(content_parts, list):
                            text = "\n".join(
                                part.get("text") or ""
                                for part in content_parts
                                if isinstance(part, dict) and part.get("type") == "text"
                            )
                        else:
                            text = ""

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
