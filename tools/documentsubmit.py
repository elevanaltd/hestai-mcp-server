"""
Document Submit Tool - Routes documents via visibility rules.
Part of Context Steward v2 Shell layer.

Flow: ACCEPT → CLASSIFY → PROCESS → PLACE → ARCHIVE → NOTIFY
"""

import json
import logging
from pathlib import Path
from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from tools.context_steward.inbox import (
    process_inbox_item,
    submit_to_inbox,
)
from tools.context_steward.utils import append_changelog, sanitize_filename
from tools.context_steward.visibility_rules import DOCUMENT_TYPES
from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class DocumentSubmitRequest(BaseModel):
    """Request model for document_submit tool."""

    type: Literal["adr", "session_note", "workflow", "config"] = Field(..., description="Type of document to submit")
    intent: str = Field(..., description="What this document is about")
    content: str = Field("", description="Document content (if <1KB)")
    file_ref: str = Field("", description="Path to file in inbox (if >1KB)")
    priority: Literal["blocking", "normal"] = Field("normal", description="Processing priority")
    continuation_id: str = Field("", description="For dialogue support")
    working_dir: str = Field(..., description="Project root path")


class DocumentSubmitTool(BaseTool):
    """
    Submit documents for routing/placement via visibility rules.

    This tool handles document placement only (no AI merging).
    For context file updates with AI merge, use context_update tool.
    """

    def get_name(self) -> str:
        return "documentsubmit"

    def get_description(self) -> str:
        return (
            "CONTEXT STEWARD - Submit documents for routing/placement. "
            "Routes via visibility rules to correct location and format."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input."""
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["adr", "session_note", "workflow", "config"],
                    "description": "Type of document to submit",
                },
                "intent": {"type": "string", "description": "What this document is about"},
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "Document content (if <1KB)",
                },
                "file_ref": {
                    "type": "string",
                    "default": "",
                    "description": "Path to file in inbox (if >1KB)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["blocking", "normal"],
                    "default": "normal",
                    "description": "Processing priority",
                },
                "continuation_id": {
                    "type": "string",
                    "default": "",
                    "description": "For dialogue support",
                },
                "working_dir": {"type": "string", "description": "Project root path"},
            },
            "required": ["type", "intent", "working_dir"],
        }

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool."""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation."""
        return DocumentSubmitRequest

    def requires_model(self) -> bool:
        """This is a utility tool that doesn't need an AI model."""
        return False

    async def prepare_prompt(self, request: DocumentSubmitRequest) -> str:
        """Not used for this utility tool."""
        return ""

    def format_response(self, response: str, request: DocumentSubmitRequest, model_info: dict = None) -> str:
        """Not used for this utility tool."""
        return response

    async def run(self, arguments: dict) -> list[TextContent]:
        """
        Process document submission.

        Flow:
        1. ACCEPT: Validate request, write to inbox if content provided
        2. CLASSIFY: Determine destination from DOCUMENT_TYPES
        3. PROCESS: OCTAVE compress if >1KB and compress=True
        4. PLACE: Write to destination directory
        5. ARCHIVE: Move original to processed/
        6. NOTIFY: Update index.json, return result
        """
        try:
            request = DocumentSubmitRequest(**arguments)
            project_root = Path(request.working_dir)

            # 1. ACCEPT
            doc_config = DOCUMENT_TYPES.get(request.type)
            if not doc_config:
                raise ValueError(f"Unknown document type: {request.type}")

            # Determine content source
            if request.file_ref:
                content = (project_root / request.file_ref).read_text()
                source = "file_ref"
            elif request.content:
                content = request.content
                source = "inline"
            else:
                raise ValueError("Either content or file_ref must be provided")

            # Submit to inbox for audit trail
            uuid = submit_to_inbox(
                project_root=project_root,
                content=content,
                doc_type=request.type,
                session_id=request.continuation_id or "direct",
            )

            # 2. CLASSIFY
            destination = doc_config["destination"]
            doc_format = doc_config["format"]
            should_compress = doc_config.get("compress", False)

            # 3. PROCESS
            processed_content = content
            if should_compress and len(content) > 1024:
                # TODO: Implement OCTAVE compression
                # For now, just note it should be compressed
                logger.info(f"Document {uuid} should be OCTAVE compressed (>1KB)")

            # 4. PLACE
            dest_dir = project_root / destination
            dest_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{sanitize_filename(request.intent)}.md"
            if doc_format == "OCTAVE":
                filename = f"{sanitize_filename(request.intent)}.oct.md"

            dest_path = dest_dir / filename
            dest_path.write_text(processed_content)

            # 5. ARCHIVE
            process_result = process_inbox_item(project_root, uuid)

            # 6. NOTIFY
            # Note: update_index() is already called by process_inbox_item()
            # We just need to track our additional metadata in the result

            # Append to changelog
            append_changelog(
                project_root,
                f"Document submitted: {request.type} → {dest_path.relative_to(project_root)}",
                request.intent,
            )

            result = {
                "status": "success",
                "uuid": uuid,
                "destination": str(dest_path.relative_to(project_root)),
                "format": doc_format,
                "source": source,
                "archived": process_result.get("archived_path", ""),
            }

            return [
                TextContent(
                    type="text",
                    text=ToolOutput(
                        status="success",
                        content=json.dumps(result, indent=2),
                        content_type="json",
                        metadata={"tool_name": self.name, "doc_type": request.type},
                    ).model_dump_json(),
                )
            ]

        except Exception as e:
            logger.error(f"Error in document_submit: {e}")
            return [
                TextContent(
                    type="text",
                    text=ToolOutput(
                        status="error", content=f"Error submitting document: {e}", content_type="text"
                    ).model_dump_json(),
                )
            ]

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool by delegating to run()."""
        return await self.run(arguments)

    def get_model_category(self) -> ToolModelCategory:
        return ToolModelCategory.FAST_RESPONSE
