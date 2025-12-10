"""
Context Update Tool - AI-driven merge into context files.
Part of Context Steward v2 Phase 2.

Flow: ACCEPT → ARCHIVE → CROSS_REFERENCE → DETECT_CONFLICTS → MERGE → COMPRESS → WRITE → LOG → RETURN
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from tools.context_steward.ai import ContextStewardAI
from tools.context_steward.changelog_parser import (
    detect_section_conflicts,
    load_conflict_state,
    parse_recent_changes,
    store_conflict_state,
)
from tools.context_steward.file_lookup import find_context_file
from tools.context_steward.inbox import process_inbox_item, submit_to_inbox
from tools.context_steward.schemas import PROJECT_CONTEXT_SCHEMA
from tools.context_steward.utils import append_changelog
from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ContextUpdateRequest(BaseModel):
    """Request model for context_update tool."""

    target: Literal["PROJECT-CONTEXT", "PROJECT-CHECKLIST", "PROJECT-ROADMAP"] = Field(
        ..., description="Target context file to update"
    )
    intent: str = Field(..., description="What change is being made")
    content: str = Field("", description="Update content (if <1KB)")
    file_ref: str = Field("", description="Path to file in inbox (if >1KB)")
    continuation_id: str = Field("", description="For dialogue/conflict resolution")
    working_dir: str = Field(..., description="Project root path")


def detect_recent_conflicts(changelog_path: Path, target: str, minutes: int = 30) -> list[dict]:
    """
    Check CHANGELOG for recent changes to same target.

    Args:
        changelog_path: Path to PROJECT-CHANGELOG.md
        target: Target file name (e.g., "PROJECT-CONTEXT")
        minutes: Time window for conflict detection (default: 30 minutes)

    Returns:
        List of potential conflicts with metadata
    """
    if not changelog_path.exists():
        return []

    conflicts = []
    content = changelog_path.read_text()

    # Parse entries - format: ## YYYY-MM-DD HH:MM\n**Intent**\nEntry
    entry_pattern = r"##\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\n\*\*(.+?)\*\*\s*\n(.+?)(?=\n##|\Z)"
    matches = re.finditer(entry_pattern, content, re.MULTILINE | re.DOTALL)

    cutoff_time = datetime.now() - timedelta(minutes=minutes)

    for match in matches:
        timestamp_str, intent, entry = match.groups()
        try:
            entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
            if entry_time >= cutoff_time:
                # Check if entry mentions target
                if target in intent or target in entry:
                    conflicts.append(
                        {
                            "target": target,
                            "timestamp": timestamp_str,
                            "intent": intent.strip(),
                            "entry": entry.strip()[:100],  # First 100 chars
                        }
                    )
        except ValueError as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            continue

    return conflicts


def validate_ai_response_compaction(ai_response: dict) -> bool:
    """
    Validate AI response complies with COMPACTION_ENFORCEMENT gate.

    BLOCKING GATE: If compaction was performed (COMPACTION_PERFORMED::true),
    AI response MUST include both artifacts:
    1. history_archive - archived content to PROJECT-HISTORY.md
    2. context_update - compacted content for PROJECT-CONTEXT.md

    Args:
        ai_response: AI response dict with status, artifacts, compaction_performed

    Returns:
        True if validation passes

    Raises:
        ValueError: If compaction performed without history_archive artifact
    """
    compaction_performed = ai_response.get("compaction_performed", False)

    if not compaction_performed:
        # No compaction, no archive required
        return True

    # COMPACTION_ENFORCEMENT gate active
    artifacts = ai_response.get("artifacts", [])

    # Check for required artifacts
    has_history_archive = any(artifact.get("type") == "history_archive" for artifact in artifacts)
    has_context_update = any(artifact.get("type") == "context_update" for artifact in artifacts)

    if not has_history_archive:
        raise ValueError(
            "COMPACTION_ENFORCEMENT gate failure: compaction_performed=true but "
            "history_archive artifact missing. AI must provide both artifacts when "
            "compacting PROJECT-CONTEXT."
        )

    if not has_context_update:
        raise ValueError(
            "COMPACTION_ENFORCEMENT gate failure: compaction_performed=true but "
            "context_update artifact missing. AI must provide both artifacts when "
            "compacting PROJECT-CONTEXT."
        )

    logger.info("COMPACTION_ENFORCEMENT gate passed: both artifacts present")
    return True


def compact_if_needed(content: str, target: str, project_root: Path, max_loc: int = 200) -> str:
    """
    If content exceeds max_loc, move old sections to PROJECT-HISTORY.md

    Strategy:
    1. Count lines
    2. If under limit, return as-is
    3. If over limit:
       - Preserve required sections (IDENTITY, ARCHITECTURE, CURRENT_STATE, etc.)
       - Move older achievement/history sections to PROJECT-HISTORY.md
       - Return compacted content

    Args:
        content: Current content to check
        target: Target file name (for logging)
        project_root: Project root directory
        max_loc: Maximum lines of code (default: 200)

    Returns:
        Compacted content if needed, otherwise original content
    """
    lines = content.split("\n")
    if len(lines) <= max_loc:
        return content

    logger.info(f"{target} exceeds {max_loc} LOC ({len(lines)} lines), triggering compaction")

    # Required sections that must be preserved
    required_sections = PROJECT_CONTEXT_SCHEMA.get("required_sections", [])

    # Parse sections
    sections = {}
    current_section = None
    section_lines = []

    for line in lines:
        if line.startswith("## "):
            # Save previous section
            if current_section:
                sections[current_section] = section_lines
            # Start new section
            current_section = line[3:].strip()
            section_lines = [line]
        elif current_section is not None:
            section_lines.append(line)

    # Save last section
    if current_section:
        sections[current_section] = section_lines

    # Identify sections to archive (not in required sections)
    # Prioritize archiving sections with "ACHIEVEMENT", "HISTORY", "COMPLETED" in name
    archive_priority = []
    keep_sections = []

    for section_name, section_content in sections.items():
        section_upper = section_name.upper()
        if any(req.upper() in section_upper for req in required_sections):
            keep_sections.append((section_name, section_content))
        else:
            # Lower priority = archive first
            priority = 0
            if any(keyword in section_upper for keyword in ["ACHIEVEMENT", "HISTORY", "COMPLETED", "OLD"]):
                priority = -1  # Archive these first
            archive_priority.append((priority, section_name, section_content))

    # Sort by priority (lowest first = archive first)
    archive_priority.sort(key=lambda x: x[0])

    # Build compacted content with required sections
    compacted_lines = []
    if lines and not lines[0].startswith("##"):
        # Preserve header (before first ##)
        for line in lines:
            if line.startswith("## "):
                break
            compacted_lines.append(line)

    # Add required sections
    for _section_name, section_content in keep_sections:
        compacted_lines.extend(section_content)
        compacted_lines.append("")  # Blank line between sections

    # Archive old sections to PROJECT-HISTORY.md
    if archive_priority:
        context_dir = project_root / ".hestai" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        history_file = context_dir / "PROJECT-HISTORY.md"

        # Prepare archived content
        archived_lines = [
            "# PROJECT-HISTORY",
            "",
            f"*Archived from {target} on {datetime.now().strftime('%Y-%m-%d')}*",
            "",
        ]

        # Add archived sections
        for _priority, _section_name, section_content in archive_priority:
            archived_lines.extend(section_content)
            archived_lines.append("")

        # Append to history file (or create if doesn't exist)
        if history_file.exists():
            existing = history_file.read_text()
            archived_content = "\n".join(archived_lines[4:])  # Skip header
            history_file.write_text(existing + "\n\n---\n\n" + archived_content)
        else:
            history_file.write_text("\n".join(archived_lines))

        logger.info(f"Archived {len(archive_priority)} sections to PROJECT-HISTORY.md")

    # Check if we're still over limit
    compacted = "\n".join(compacted_lines)
    if len(compacted.split("\n")) > max_loc:
        logger.warning(f"Content still exceeds {max_loc} LOC after compaction. Manual review needed.")

    return compacted


class ContextUpdateTool(BaseTool):
    """
    Request updates to context files with AI-driven merge.

    Unlike document_submit (placement only), this tool:
    1. Reads existing content
    2. Uses AI to intelligently merge new content
    3. Detects conflicts with recent changes
    4. Maintains LOC limits via compaction
    """

    def get_name(self) -> str:
        return "contextupdate"

    def get_description(self) -> str:
        return (
            "CONTEXT STEWARD - Request updates to context files with AI-driven merge. "
            "Intelligently merges new content into PROJECT-CONTEXT, PROJECT-CHECKLIST, or PROJECT-ROADMAP."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input."""
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["PROJECT-CONTEXT", "PROJECT-CHECKLIST", "PROJECT-ROADMAP"],
                    "description": "Target context file to update",
                },
                "intent": {"type": "string", "description": "What change is being made"},
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "Update content (if <1KB)",
                },
                "file_ref": {
                    "type": "string",
                    "default": "",
                    "description": "Path to file in inbox (if >1KB)",
                },
                "continuation_id": {
                    "type": "string",
                    "default": "",
                    "description": "For dialogue/conflict resolution",
                },
                "working_dir": {"type": "string", "description": "Project root path"},
            },
            "required": ["target", "intent", "working_dir"],
        }

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool (uses ContextStewardAI internally)."""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation."""
        return ContextUpdateRequest

    def requires_model(self) -> bool:
        """This tool uses ContextStewardAI internally, not a direct model."""
        return False

    async def prepare_prompt(self, request: ContextUpdateRequest) -> str:
        """Not used for this tool."""
        return ""

    def format_response(self, response: str, request: ContextUpdateRequest, model_info: dict = None) -> str:
        """Not used for this tool."""
        return response

    async def run(self, arguments: dict) -> list[TextContent]:
        """
        Process context update request.

        Flow:
        1. ACCEPT: Validate request, determine target file path
        2. ARCHIVE: Save request to inbox for audit trail
        3. CROSS_REFERENCE: Read current target + PROJECT-CHANGELOG
        4. DETECT_CONFLICTS: Check if same section modified recently
        5. MERGE: Use ContextStewardAI.run_task() to merge content
        6. COMPRESS: If >200 LOC, move old content to PROJECT-HISTORY.md
        7. WRITE: Update target file
        8. LOG: Append entry to PROJECT-CHANGELOG.md
        9. RETURN: Summary + changelog entry
        """
        try:
            request = ContextUpdateRequest(**arguments)
            project_root = Path(request.working_dir)

            # 1. ACCEPT - Validate and determine content source
            if request.file_ref:
                file_path = project_root / request.file_ref
                if not file_path.exists():
                    raise FileNotFoundError(f"Referenced file not found: {request.file_ref}")
                new_content = file_path.read_text()
                source = "file_ref"
            elif request.content:
                new_content = request.content
                source = "inline"
            else:
                raise ValueError("Either content or file_ref must be provided")

            # Find target file
            target_filename = f"{request.target}.md"
            target_path = find_context_file(project_root, target_filename)

            if target_path is None:
                # Create new file in .hestai/context/
                context_dir = project_root / ".hestai" / "context"
                context_dir.mkdir(parents=True, exist_ok=True)
                target_path = context_dir / target_filename
                target_path.write_text(f"# {request.target}\n\n")
                logger.info(f"Created new context file: {target_path}")

            # 2. ARCHIVE - Submit to inbox for audit trail
            uuid = submit_to_inbox(
                project_root=project_root,
                content=new_content,
                doc_type="context_update",
                session_id=request.continuation_id or "direct",
            )

            # 3. CROSS_REFERENCE - Read current content and changelog
            existing_content = target_path.read_text()
            changelog_path = project_root / ".hestai" / "context" / "PROJECT-CHANGELOG.md"

            # 4. DETECT_CONFLICTS - Check for section-level conflicts (Phase 2)
            # If continuation_id provided, validate it corresponds to a real conflict
            skip_detection = False
            if request.continuation_id:
                logger.info(f"Conflict resolution attempt via continuation_id: {request.continuation_id}")
                # Security: load and validate conflict state exists and matches target
                try:
                    conflict_state = load_conflict_state(project_root, request.continuation_id)
                except ValueError as e:
                    # Invalid continuation_id format (path traversal attempt)
                    logger.error(f"Invalid continuation_id: {e}")
                    raise ValueError(f"Invalid continuation_id: {e}") from e

                if not conflict_state:
                    # No valid conflict state found - must go through detection
                    logger.warning(
                        f"No conflict state found for continuation_id {request.continuation_id}, "
                        "falling back to conflict detection"
                    )
                    skip_detection = False
                elif conflict_state.get("original_request", {}).get("target") != request.target:
                    # Conflict state is for different target - suspicious
                    logger.error(
                        f"Continuation_id {request.continuation_id} is for "
                        f"{conflict_state.get('original_request', {}).get('target')}, "
                        f"but current request is for {request.target}"
                    )
                    raise ValueError("Continuation_id target mismatch")
                else:
                    # Valid continuation - skip detection and continue to merge
                    logger.info(f"Resolving conflict: {conflict_state.get('conflict', {}).get('details')}")
                    skip_detection = True
                    # Clear conflict state after successful validation
                    from tools.context_steward.changelog_parser import clear_conflict_state

                    clear_conflict_state(project_root, request.continuation_id)

            # Run conflict detection if no valid continuation_id
            if not skip_detection:
                # Parse recent changes from CHANGELOG
                recent_entries = parse_recent_changes(changelog_path, minutes=30)

                # Check for section-level conflicts
                conflict_response = detect_section_conflicts(
                    recent_entries=recent_entries,
                    new_content=new_content,
                    target=request.target,
                )

                if conflict_response:
                    # Store conflict state for resolution via continuation_id
                    store_conflict_state(
                        project_root=project_root,
                        conflict_id=conflict_response["continuation_id"],
                        conflict_data=conflict_response,
                        request_data=request.__dict__,
                    )

                    # Return conflict response (blocks merge until resolved)
                    logger.warning(f"Section-level conflict detected: {conflict_response['details']['section']}")
                    return [
                        TextContent(
                            type="text",
                            text=ToolOutput(
                                status="conflict",
                                content=json.dumps(conflict_response, indent=2),
                                content_type="json",
                                metadata={"tool_name": self.name, "target": request.target},
                            ).model_dump_json(),
                        )
                    ]

                # Legacy: also check old-style conflicts for logging
                conflicts = detect_recent_conflicts(changelog_path, request.target, minutes=30)
                if conflicts:
                    logger.info(f"Legacy detection: {len(conflicts)} potential conflicts for {request.target}")
                    conflict_summary = "; ".join([f"{c['intent']} ({c['timestamp']})" for c in conflicts])
                    logger.info(f"Recent changes: {conflict_summary}")

            # 5. MERGE - Use AI to intelligently merge content
            ai = ContextStewardAI()
            merged_content = existing_content  # Fallback

            if ai.is_task_enabled("project_context_update"):
                result = await ai.run_task(
                    task_key="project_context_update",
                    intent=request.intent,
                    content=new_content,
                    existing_content=existing_content,
                    working_dir=request.working_dir,
                )

                if result.get("status") == "success":
                    # COMPACTION_ENFORCEMENT gate: validate AI response before processing
                    try:
                        validate_ai_response_compaction(result)
                    except ValueError as e:
                        logger.error(f"COMPACTION_ENFORCEMENT gate failure: {e}")
                        raise ValueError(f"AI response validation failed: {e}") from e

                    artifacts = result.get("artifacts", [])

                    # FIX: Select artifact by type, not order
                    # Issue: If AI returns history_archive first, we must select context_update
                    context_artifact = next(
                        (a["content"] for a in artifacts if a.get("type") == "context_update"), None
                    )

                    if context_artifact is None:
                        # No context_update artifact found
                        raise ValueError("AI response missing context_update artifact type")

                    merged_content = context_artifact

                    # Extract and persist history_archive artifact if present
                    # This enforces the COMPACTION_ENFORCEMENT gate (validation + persistence)
                    history_artifact = next(
                        (a["content"] for a in artifacts if a.get("type") == "history_archive"), None
                    )

                    if history_artifact and result.get("compaction_performed"):
                        # AI performed compaction and returned history_archive - persist it
                        context_dir = project_root / ".hestai" / "context"
                        context_dir.mkdir(parents=True, exist_ok=True)
                        history_file = context_dir / "PROJECT-HISTORY.md"

                        # Prepare archived content with date stamp (consistent with compact_if_needed)
                        archived_content = (
                            f"*Archived from {request.target} on {datetime.now().strftime('%Y-%m-%d')}*\n\n"
                        )
                        archived_content += history_artifact

                        # Append to history file (or create if doesn't exist)
                        if history_file.exists():
                            existing = history_file.read_text()
                            history_file.write_text(existing + "\n\n---\n\n" + archived_content)
                        else:
                            history_file.write_text("# PROJECT-HISTORY\n\n" + archived_content)

                        logger.info(f"Persisted history_archive artifact to {history_file}")

                    # Defensive check: AI must return substantial content
                    MIN_CONTENT_LENGTH = 500  # ~10 lines minimum
                    if len(merged_content) < MIN_CONTENT_LENGTH:
                        logger.error(
                            f"AI returned truncated content ({len(merged_content)} chars), "
                            f"expected at least {MIN_CONTENT_LENGTH}. Using fallback."
                        )
                        merged_content = existing_content + "\n\n" + new_content
                    else:
                        logger.info(f"AI merge successful: {result.get('summary', 'merged')}")
                else:
                    logger.warning(f"AI merge failed: {result.get('error', 'unknown')}, using simple append")
                    merged_content = existing_content + "\n\n" + new_content
            else:
                logger.info("AI merge disabled, using simple append")
                merged_content = existing_content + "\n\n" + new_content

            # 6. COMPRESS - Apply LOC limits
            max_loc = PROJECT_CONTEXT_SCHEMA.get("max_loc", 200)
            compacted_content = compact_if_needed(merged_content, request.target, project_root, max_loc=max_loc)

            # 7. WRITE - Update target file
            target_path.write_text(compacted_content)
            logger.info(f"Updated {target_path}")

            # 8. LOG - Append to changelog
            changelog_entry = f"Updated {request.target}"
            if "conflicts" in locals() and conflicts:
                changelog_entry += f" (resolved {len(conflicts)} conflicts)"
            append_changelog(project_root, changelog_entry, request.intent)

            # 9. RETURN - Process inbox and return result
            process_inbox_item(project_root, uuid)

            # Count conflicts for reporting (may be 0 if continuation_id path taken)
            conflicts_count = len(conflicts) if "conflicts" in locals() else 0

            result = {
                "status": "success",
                "uuid": uuid,
                "target": request.target,
                "target_path": str(target_path.relative_to(project_root)),
                "merged": True,
                "compacted": len(merged_content.split("\n")) > max_loc,
                "conflicts_detected": conflicts_count,
                "source": source,
            }

            return [
                TextContent(
                    type="text",
                    text=ToolOutput(
                        status="success",
                        content=json.dumps(result, indent=2),
                        content_type="json",
                        metadata={"tool_name": self.name, "target": request.target},
                    ).model_dump_json(),
                )
            ]

        except Exception as e:
            logger.error(f"Error in context_update: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=ToolOutput(
                        status="error", content=f"Error updating context: {e}", content_type="text"
                    ).model_dump_json(),
                )
            ]

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool by delegating to run()."""
        return await self.run(arguments)

    def get_model_category(self) -> ToolModelCategory:
        return ToolModelCategory.FAST_RESPONSE
