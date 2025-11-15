"""
Shared JSON Schema Definitions for HestAI MCP Tools

STATUS: EXPERIMENTAL - DISABLED BY DEFAULT
===========================================
This feature is currently disabled due to MCP client limitations.
The Claude MCP client does not properly resolve $ref pointers in JSON schemas.

To enable when ready: Set USE_SCHEMA_REFS=true in .env
Current achievement: 18% token reduction (target: 40%)

BLOCKER: MCP client needs to support JSON Schema $ref resolution
TODO: Re-enable when Anthropic updates MCP client infrastructure
TODO: Improve optimization to reach 40% reduction target

GOVERNANCE:
- Owner: Implementation Lead
- Review Authority: Critical Engineer + Technical Architect
- Change Threshold: 3+ tools must benefit from a shared definition
- Breaking Changes: Require versioning and deprecation cycle

Token Optimization Impact:
- Model enum/descriptions: ~1,921 chars per tool → $ref (45% reduction)
- Common parameters: ~500 chars per tool → $ref (20% reduction)
- Total estimated savings: 15-20k tokens across all tools

VERSIONING STRATEGY:
- Current Version: v1 (initial release)
- Schema paths: #/$defs/v1/{field_name}
- Deprecation cycle: 2 releases minimum
- Fallback: USE_SCHEMA_REFS environment variable controls feature
"""

import os
from typing import Any

# Feature flag for schema refs (defaults to False for safety)
USE_SCHEMA_REFS = os.environ.get("USE_SCHEMA_REFS", "false").lower() == "true"

# Current schema version
SCHEMA_VERSION = "v1"


class SharedSchemaDefinitions:
    """
    Centralized schema definitions for MCP tools.

    Uses JSON Schema $defs pattern for internal references.
    Organized into logical categories to prevent "God object" anti-pattern.
    """

    @staticmethod
    def get_base_definitions() -> dict[str, Any]:
        """
        Get the complete $defs object for inclusion in tool schemas.

        Returns:
            Dict containing all shared schema definitions under $defs key
        """
        # Return empty definitions if feature is disabled
        if not USE_SCHEMA_REFS:
            return {"$defs": {}}

        # Include versioned definitions
        return {
            "$defs": {
                SCHEMA_VERSION: {
                    **SharedSchemaDefinitions._get_model_definitions(),
                    **SharedSchemaDefinitions._get_common_parameters(),
                    **SharedSchemaDefinitions._get_workflow_fields(),
                    **SharedSchemaDefinitions._get_context_fields(),
                }
            }
        }

    @staticmethod
    def _get_model_definitions() -> dict[str, Any]:
        """Model selection field definitions."""
        return {
            "modelEnum": {
                "type": "array",
                "description": "Available model names from enabled providers",
                # This will be populated dynamically by BaseTool
                "items": {"type": "string"},
            },
            "modelFieldAutoMode": {
                "type": "object",
                "properties": {
                    "type": {"const": "string"},
                    "description": {"type": "string"},
                    "enum": {"$ref": "#/$defs/modelEnum"},
                },
                "required": ["type", "description", "enum"],
            },
            "modelFieldNormalMode": {
                "type": "object",
                "properties": {"type": {"const": "string"}, "description": {"type": "string"}},
                "required": ["type", "description"],
            },
        }

    @staticmethod
    def _get_common_parameters() -> dict[str, Any]:
        """Common tool parameter definitions."""
        return {
            "temperature": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": (
                    "Temperature for response (0.0 to 1.0). Lower values are more focused and deterministic, "
                    "higher values are more creative. Tool-specific defaults apply if not specified."
                ),
            },
            "thinkingMode": {
                "type": "string",
                "enum": ["minimal", "low", "medium", "high", "max"],
                "description": (
                    "Thinking depth: minimal (0.5% of model max), low (8%), medium (33%), high (67%), "
                    "max (100% of model max). Higher modes enable deeper reasoning at the cost of speed."
                ),
            },
            "useWebsearch": {
                "type": "boolean",
                "default": True,
                "description": (
                    "Enable web search for documentation, best practices, and current information. "
                    "When enabled, the model can request Claude to perform web searches and share results back "
                    "during conversations. Particularly useful for: brainstorming sessions, architectural design "
                    "discussions, exploring industry best practices, working with specific frameworks/technologies, "
                    "researching solutions to complex problems, or when current documentation and community insights "
                    "would enhance the analysis."
                ),
            },
            "continuationId": {
                "type": "string",
                "description": (
                    "Thread continuation ID for multi-turn conversations. When provided, the complete conversation "
                    "history is automatically embedded as context. Your response should build upon this history "
                    "without repeating previous analysis or instructions. Focus on providing only new insights, "
                    "additional findings, or answers to follow-up questions. Can be used across different tools."
                ),
            },
        }

    @staticmethod
    def _get_workflow_fields() -> dict[str, Any]:
        """Workflow-specific field definitions."""
        return {
            "workflowStep": {
                "type": "string",
                "description": "Current work step content and findings from your overall work",
            },
            "workflowStepNumber": {
                "type": "integer",
                "minimum": 1,
                "description": "Current step number in the work sequence (starts at 1)",
            },
            "workflowTotalSteps": {
                "type": "integer",
                "minimum": 1,
                "description": "Estimated total steps needed to complete the work",
            },
            "workflowNextStepRequired": {
                "type": "boolean",
                "description": "Whether another work step is needed after this one",
            },
            "workflowFindings": {
                "type": "string",
                "description": "Important findings, evidence and insights discovered in this step of the work",
            },
            "workflowConfidence": {
                "type": "string",
                "enum": ["exploring", "low", "medium", "high", "very_high", "almost_certain", "certain"],
                "description": (
                    "Confidence level in findings: exploring (just starting), low (early investigation), "
                    "medium (some evidence), high (strong evidence), very_high (comprehensive understanding), "
                    "almost_certain (near complete confidence), certain (100% confidence locally - no external validation needed)"
                ),
            },
            "workflowFilesChecked": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of files examined during this work step",
            },
            "workflowRelevantFiles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files identified as relevant to the issue/goal",
            },
            "workflowRelevantContext": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Methods/functions identified as involved in the issue",
            },
            "workflowIssuesFound": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Issues identified with severity levels during work",
            },
            "workflowHypothesis": {
                "type": "string",
                "description": "Current theory about the issue/goal based on work",
            },
            "workflowBacktrackFromStep": {
                "type": "integer",
                "minimum": 1,
                "description": "Step number to backtrack from if work needs revision",
            },
            "workflowUseAssistantModel": {
                "type": "boolean",
                "default": True,
                "description": (
                    "Whether to use assistant model for expert analysis after completing the workflow steps. "
                    "Set to False to skip expert analysis and rely solely on Claude's investigation. "
                    "Defaults to True for comprehensive validation."
                ),
            },
        }

    @staticmethod
    def _get_context_fields() -> dict[str, Any]:
        """File and image context field definitions."""
        return {
            "contextFiles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional files for context (must be FULL absolute paths to real files / folders - DO NOT SHORTEN)",
            },
            "contextImages": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional image(s) for visual context. Accepts absolute file paths or "
                    "base64 data URLs. Only provide when user explicitly mentions images. "
                    "When including images, please describe what you believe each image contains "
                    "to aid with contextual understanding. Useful for UI discussions, diagrams, "
                    "visual problems, error screens, architecture mockups, and visual analysis tasks."
                ),
            },
        }

    @staticmethod
    def get_model_field_ref(is_auto_mode: bool) -> dict[str, Any]:
        """
        Get a $ref for the model field based on auto mode.

        Args:
            is_auto_mode: Whether the tool is in auto mode (model required)

        Returns:
            Dict with $ref to appropriate model field definition OR inline schema if disabled
        """
        if not USE_SCHEMA_REFS:
            # Return None to signal inline schema should be used
            return None

        if is_auto_mode:
            return {"$ref": f"#/$defs/{SCHEMA_VERSION}/modelFieldAutoMode"}
        else:
            return {"$ref": f"#/$defs/{SCHEMA_VERSION}/modelFieldNormalMode"}

    @staticmethod
    def get_parameter_ref(param_name: str) -> dict[str, Any]:
        """
        Get a $ref for a common parameter.

        Args:
            param_name: Name of the parameter (e.g., 'temperature', 'thinking_mode')

        Returns:
            Dict with $ref to the parameter definition OR None if disabled
        """
        if not USE_SCHEMA_REFS:
            return None

        # Convert snake_case to camelCase for $defs keys
        ref_name = "".join(word.capitalize() if i > 0 else word for i, word in enumerate(param_name.split("_")))
        return {"$ref": f"#/$defs/{SCHEMA_VERSION}/{ref_name}"}

    @staticmethod
    def get_workflow_field_ref(field_name: str) -> dict[str, Any]:
        """
        Get a $ref for a workflow field.

        Args:
            field_name: Name of the workflow field

        Returns:
            Dict with $ref to the workflow field definition OR None if disabled
        """
        if not USE_SCHEMA_REFS:
            return None

        # Convert to camelCase and prefix with 'workflow'
        parts = field_name.split("_")
        ref_name = "workflow" + "".join(word.capitalize() for word in parts)
        return {"$ref": f"#/$defs/{SCHEMA_VERSION}/{ref_name}"}

    @staticmethod
    def get_context_field_ref(field_name: str) -> dict[str, Any]:
        """
        Get a $ref for a context field.

        Args:
            field_name: Name of the context field ('files' or 'images')

        Returns:
            Dict with $ref to the context field definition OR None if disabled
        """
        if not USE_SCHEMA_REFS:
            return None

        ref_name = f"context{field_name.capitalize()}"
        return {"$ref": f"#/$defs/{SCHEMA_VERSION}/{ref_name}"}


def create_optimized_schema(
    properties: dict[str, Any],
    required: list[str],
    include_model_enum: bool = True,
    model_enum_values: list[str] = None,
) -> dict[str, Any]:
    """
    Create an optimized schema with shared definitions.

    This is a helper function for tools to easily create schemas that use
    the shared definitions instead of duplicating content.

    Args:
        properties: The tool-specific properties
        required: List of required property names
        include_model_enum: Whether to include the model enum in $defs
        model_enum_values: The actual model enum values to include

    Returns:
        Complete JSON Schema with $defs and $refs (or inline if disabled)
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }

    # Only add definitions if feature is enabled
    if USE_SCHEMA_REFS:
        # Add base definitions
        base_defs = SharedSchemaDefinitions.get_base_definitions()

        # If model enum values provided, update the modelEnum definition
        if include_model_enum and model_enum_values:
            base_defs["$defs"][SCHEMA_VERSION]["modelEnum"] = {"type": "string", "enum": model_enum_values}

        schema["$defs"] = base_defs["$defs"]

    return schema
