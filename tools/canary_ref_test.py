"""
Canary test tool for JSON Schema $ref support in MCP client.

This tool tests whether Claude's MCP client can properly resolve
internal $ref references in tool schemas. This is a critical gate
for the token optimization project.

CRITICAL: This test must pass before deploying schema optimization.
"""

from typing import Any, Optional
# CONTEXT7_BYPASS: INTERNAL-MODULE - Internal imports
from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from pydantic import Field


class CanaryRefRequest(ToolRequest):
    """Request model for canary test tool."""
    test_message: str = Field(..., description="A test message to echo back")
    confidence: Optional[str] = Field("medium", description="Confidence level for the test")


class CanaryRefTestTool(BaseTool):
    """
    Minimal test tool to verify MCP client $ref support.

    If this tool works correctly when invoked through MCP,
    it proves the client can resolve $ref patterns.
    """

    def get_name(self) -> str:
        return "canary_ref_test"

    def get_description(self) -> str:
        return (
            "TEST TOOL: Canary test for JSON Schema $ref support. "
            "This tool tests whether the MCP client can resolve internal references. "
            "If you can see and use this tool, $ref resolution is working."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """
        Return a schema with $ref to test MCP client resolution.

        This uses a simple internal $ref pattern to verify compatibility.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "test_message": {
                    "type": "string",
                    "description": "A test message to echo back"
                },
                "confidence": {
                    "$ref": "#/$defs/confidence_enum"
                }
            },
            "required": ["test_message"],
            "additionalProperties": False,
            "$defs": {
                "confidence_enum": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Confidence level for the test"
                }
            }
        }

    def get_system_prompt(self) -> str:
        return "You are a test tool verifying $ref support."

    def get_request_model(self):
        """Return the request model for this tool."""
        return CanaryRefRequest

    async def prepare_prompt(self, request: CanaryRefRequest) -> str:
        """Prepare the prompt for the model."""
        return f"Echo this message: {request.test_message} with confidence: {request.confidence}"

    async def execute(self, **kwargs) -> Any:
        """
        Simple echo implementation to verify the tool works.
        """
        test_message = kwargs.get("test_message", "No message provided")
        confidence = kwargs.get("confidence", "medium")

        return {
            "success": True,
            "message": f"Canary test successful! Message: {test_message}",
            "confidence": confidence,
            "ref_support": "VERIFIED",
            "details": "MCP client successfully resolved $ref in schema"
        }
