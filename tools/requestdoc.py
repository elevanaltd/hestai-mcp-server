"""
RequestDoc Tool - Documentation routing via visibility rules

This tool enables agents to request documentation creation with proper
routing to the correct location based on document type and visibility rules.

Part of the Context Steward session lifecycle management system.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from mcp.types import TextContent
from pydantic import BaseModel, Field

from tools.context_steward.ai import ContextStewardAI
from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


# Visibility rules from ADR-003
VISIBILITY_RULES = {
    "adr": {"path": "docs/adr/", "format": "ADR_template"},
    "context_update": {"path": ".hestai/context/", "format": "OCTAVE"},
    "session_note": {"path": ".hestai/sessions/", "format": "OCTAVE"},
    "workflow_update": {"path": ".hestai/workflow/", "format": "OCTAVE"},
}

# Map request types to Context Steward AI task keys
TASK_MAPPING = {
    "context_update": "project_context_update",
    "workflow_update": "project_checklist_update",
    # session_note doesn't have AI integration yet
    # adr doesn't have AI integration yet
}


class RequestDocRequest(BaseModel):
    """Request model for request_doc tool"""

    type: Literal["adr", "context_update", "session_note", "workflow_update"] = Field(
        ..., description="Type of documentation to create"
    )
    intent: str = Field(..., description="What should be documented")
    scope: Literal["full_session", "from_marker", "specific"] = Field(
        "specific", description="Scope of content to document"
    )
    priority: Literal["blocking", "end_of_session", "background"] = Field(
        "end_of_session", description="Priority level for documentation"
    )
    content: str = Field("", description="Content to document (if scope=specific)")
    files: list[str] = Field(
        default_factory=list, description="Files to analyze for context (paths relative to working_dir)"
    )
    working_dir: str = Field(..., description="Project root path")


class RequestDocTool(BaseTool):
    """
    Context Steward tool for routing documentation requests.

    Routes documentation to correct location via visibility rules (ADR-003),
    applies appropriate format, and queues or creates based on priority.

    For context_update and workflow_update types, delegates to ContextStewardAI
    for intelligent document merging and updates.
    """

    def __init__(self):
        super().__init__()
        self._ai_helper: Optional[ContextStewardAI] = None

    @property
    def ai_helper(self) -> ContextStewardAI:
        """Lazy-load AI helper on first access"""
        if self._ai_helper is None:
            self._ai_helper = ContextStewardAI()
        return self._ai_helper

    def get_name(self) -> str:
        return "requestdoc"

    def get_description(self) -> str:
        return (
            "CONTEXT STEWARD - Route documentation requests to correct location. "
            "Applies visibility rules and format standards based on document type."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["adr", "context_update", "session_note", "workflow_update"],
                    "description": "Type of documentation to create",
                },
                "intent": {"type": "string", "description": "What should be documented"},
                "scope": {
                    "type": "string",
                    "enum": ["full_session", "from_marker", "specific"],
                    "default": "specific",
                    "description": "Scope of content to document",
                },
                "priority": {
                    "type": "string",
                    "enum": ["blocking", "end_of_session", "background"],
                    "default": "end_of_session",
                    "description": "Priority level for documentation",
                },
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "Content to document (if scope=specific)",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Files to analyze for context (paths relative to working_dir)",
                },
                "working_dir": {"type": "string", "description": "Project root path"},
            },
            "required": ["type", "intent", "working_dir"],
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """This tool modifies filesystem (creates documentation files)"""
        return None  # Not read-only - creates documentation files

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool"""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation"""
        return RequestDocRequest

    def requires_model(self) -> bool:
        """This is a utility tool that doesn't need an AI model"""
        return False

    async def prepare_prompt(self, request: RequestDocRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: RequestDocRequest, model_info: dict = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Route documentation request to correct location.

        Applies visibility rules, creates directory structure if needed,
        and creates or queues documentation based on priority.

        For context_update and workflow_update, attempts to use AI for
        intelligent document merging if enabled. Falls back to templates.

        Args:
            arguments: Tool arguments containing type, intent, scope, priority, content, working_dir

        Returns:
            Documentation routing response with status, path, steward, format_applied
        """
        try:
            # Validate request
            request = RequestDocRequest(**arguments)

            # Get project root (from session context or working_dir)
            session_context = arguments.get("_session_context")
            if session_context:
                project_root = Path(session_context.project_root)
            else:
                project_root = Path(request.working_dir)

            # Get visibility rules for this doc type
            rules = VISIBILITY_RULES[request.type]
            base_path = rules["path"]
            doc_format = rules["format"]

            # Construct full path
            doc_dir = project_root / base_path
            doc_dir.mkdir(parents=True, exist_ok=True)

            # Try AI integration for supported types
            task_key = TASK_MAPPING.get(request.type)
            ai_result = None

            # Check if AI is enabled for this task (synchronous check)
            ai_enabled = task_key and self.ai_helper.is_task_enabled(task_key)

            if ai_enabled:
                logger.info(f"Attempting AI processing for {request.type} via task {task_key}")
                try:
                    # Read existing document if it exists (using multi-location lookup)
                    existing_content = None
                    if request.type == "context_update":
                        context_file = self._find_context_file(project_root, "PROJECT-CONTEXT.md")
                        if context_file:
                            existing_content = context_file.read_text()
                    elif request.type == "workflow_update":
                        checklist_file = self._find_context_file(project_root, "PROJECT-CHECKLIST.md")
                        if checklist_file:
                            existing_content = checklist_file.read_text()

                    # Prepare AI context with files
                    ai_context = {
                        "intent": request.intent,
                        "content": request.content,
                        "existing_content": existing_content or "",
                        "project_root": str(project_root),
                        "files": request.files,  # Pass files to AI
                    }

                    # Execute AI task
                    ai_result = await self.ai_helper.run_task(task_key, **ai_context)

                    if ai_result["status"] == "success":
                        logger.info(f"AI processing succeeded: {ai_result['summary']}")

                        # Extract updated content from artifacts
                        for artifact in ai_result.get("artifacts", []):
                            if artifact.get("type") in ["context_update", "workflow_update"]:
                                artifact_path = project_root / artifact["path"]
                                # Content would come from artifact, but for now just log
                                logger.info(f"AI would update: {artifact_path}")

                        # Create response from AI result
                        content = {
                            "status": "updated_by_ai",
                            "path": str(doc_dir.relative_to(project_root)),
                            "steward": "system-steward",
                            "format_applied": doc_format,
                            "ai_summary": ai_result["summary"],
                            "changes": ai_result.get("changes", []),
                        }

                        tool_output = ToolOutput(
                            status="success",
                            content=json.dumps(content, indent=2),
                            content_type="json",
                            metadata={"tool_name": self.name, "doc_type": request.type, "ai_used": True},
                        )

                        return [TextContent(type="text", text=tool_output.model_dump_json())]

                    else:
                        logger.warning(f"AI processing failed: {ai_result.get('error')}, falling back to template")

                except Exception as e:
                    logger.warning(f"AI processing error: {e}, falling back to template")

            # Fallback to template-based document creation
            # Generate filename based on type and intent
            timestamp = datetime.now().strftime("%Y-%m-%d")
            safe_intent = self._sanitize_filename(request.intent)

            if request.type == "adr":
                # ADR filename: YYYY-MM-DD-description.md
                filename = f"{timestamp}-{safe_intent}.md"
            else:
                # OCTAVE format filename
                filename = f"{timestamp}-{safe_intent}.oct.md"

            doc_path = doc_dir / filename

            # Determine status based on priority
            if request.priority == "blocking":
                # Create immediately for blocking priority
                status = "created"
                self._create_document(doc_path, request, doc_format)
                logger.info(f"Created {request.type} document at {doc_path}")
            else:
                # Queue for later processing
                status = "queued"
                logger.info(f"Queued {request.type} document for {doc_path}")

            # Create response content
            content = {
                "status": status,
                "path": str(doc_path.relative_to(project_root)),
                "steward": "system-steward",
                "format_applied": doc_format,
            }

            tool_output = ToolOutput(
                status="success",
                content=json.dumps(content, indent=2),
                content_type="json",
                metadata={"tool_name": self.name, "doc_type": request.type},
            )

            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            logger.error(f"Error in request_doc: {str(e)}")
            error_output = ToolOutput(
                status="error", content=f"Error routing documentation: {str(e)}", content_type="text"
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _find_context_file(self, project_root: Path, filename: str) -> Path | None:
        """
        Find context file in priority order across multiple locations.

        Searches for the file in:
        1. .hestai/context/
        2. .coord/
        3. project root

        Args:
            project_root: Project root directory
            filename: Filename to search for (e.g., "PROJECT-CONTEXT.md")

        Returns:
            Path to found file, or None if not found in any location
        """
        search_paths = [
            project_root / ".hestai" / "context" / filename,
            project_root / ".coord" / filename,
            project_root / filename,
        ]

        for path in search_paths:
            if path.exists():
                logger.debug(f"Found {filename} at {path}")
                return path

        logger.debug(f"{filename} not found in any location")
        return None

    def _sanitize_filename(self, text: str) -> str:
        """
        Sanitize text for use in filename.

        Args:
            text: Raw text to sanitize

        Returns:
            Sanitized filename-safe string
        """
        # Convert to lowercase, replace spaces with hyphens
        sanitized = text.lower().replace(" ", "-")
        # Remove any characters that aren't alphanumeric or hyphens
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "-")
        # Limit length
        return sanitized[:50]

    def _create_document(self, doc_path: Path, request: RequestDocRequest, doc_format: str):
        """
        Create documentation file with appropriate format.

        Args:
            doc_path: Path where document should be created
            request: Documentation request
            doc_format: Format to apply (ADR_template or OCTAVE)
        """
        if doc_format == "ADR_template":
            # Create ADR using standard template
            content = self._format_adr(request)
        else:
            # Create OCTAVE format document
            content = self._format_octave(request)

        doc_path.write_text(content)

    def _format_adr(self, request: RequestDocRequest) -> str:
        """
        Format content as ADR using standard template.

        Args:
            request: Documentation request

        Returns:
            Formatted ADR content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")

        if request.content:
            # Use provided content
            body = request.content
        else:
            # Generate template
            body = f"""## Context

{request.intent}

## Decision

[Document the decision made]

## Consequences

[Document the consequences of this decision]

## Status

Proposed

## Date

{timestamp}
"""

        return f"""# {request.intent}

{body}
"""

    def _format_octave(self, request: RequestDocRequest) -> str:
        """
        Format content as OCTAVE document.

        Args:
            request: Documentation request

        Returns:
            Formatted OCTAVE content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")

        if request.content:
            # Use provided content
            body = request.content
        else:
            # Generate minimal OCTAVE structure
            body = f"""DOCUMENT::[
  TYPE::{request.type.upper()},
  INTENT::{request.intent},
  SCOPE::{request.scope},
  CREATED::{timestamp}
]

CONTENT::[
  [Document content here]
]
"""

        return f"""# {request.intent}

{body}
"""

    def get_model_category(self) -> ToolModelCategory:
        """Return the model category for this tool"""
        return ToolModelCategory.FAST_RESPONSE  # Utility tool, no AI needed
