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
    working_dir: str = Field(..., description="Project root path")


class RequestDocTool(BaseTool):
    """
    Context Steward tool for routing documentation requests.

    Routes documentation to correct location via visibility rules (ADR-003),
    applies appropriate format, and queues or creates based on priority.
    """

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
