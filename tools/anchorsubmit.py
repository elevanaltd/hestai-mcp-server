"""
AnchorSubmit Tool - Validate agent anchor and return enforcement rules

This tool enables agents to submit their constitutional anchor (SHANK+ARM+FLUKE)
for validation, drift detection, and enforcement rule retrieval.

Part of the Context Steward session lifecycle management system.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from mcp.types import TextContent
from pydantic import BaseModel, Field

from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


# Role-based enforcement rules
ROLE_ENFORCEMENT = {
    "holistic-orchestrator": {
        "blocked_paths": ["src/**", "apps/**", "packages/**", "tools/*.py"],
        "delegation_required": ["implementation-lead"],
    },
    "implementation-lead": {"blocked_paths": [], "delegation_required": []},
    # Default for other roles
    "default": {"blocked_paths": [], "delegation_required": []},
}


class AnchorSubmitRequest(BaseModel):
    """Request model for anchor_submit tool"""

    session_id: str = Field(..., description="Session ID from clock_in")
    working_dir: str = Field(..., description="Project root path")
    anchor: dict = Field(..., description="SHANK + ARM + FLUKE structure")


class AnchorSubmitTool(BaseTool):
    """
    Context Steward tool for validating agent anchors.

    Validates SHANK+ARM+FLUKE structure, detects phase drift,
    stores anchor to session, and returns role-based enforcement rules.
    """

    def get_name(self) -> str:
        return "anchorsubmit"

    def get_description(self) -> str:
        return (
            "CONTEXT STEWARD - Validate agent anchor and return enforcement rules. "
            "Validates SHANK+ARM+FLUKE structure, detects drift, and provides role-based constraints."
        )

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID from clock_in"},
                "working_dir": {"type": "string", "description": "Project root path"},
                "anchor": {
                    "type": "object",
                    "description": "SHANK + ARM + FLUKE structure",
                    "properties": {
                        "SHANK": {
                            "type": "object",
                            "description": "Constitutional identity (role, cognition, archetypes, constraints)",
                        },
                        "ARM": {
                            "type": "object",
                            "description": "Contextual positioning (phase, focus, blockers)",
                        },
                        "FLUKE": {"type": "object", "description": "Operational state (skills, patterns)"},
                    },
                    "required": ["SHANK", "ARM", "FLUKE"],
                },
            },
            "required": ["session_id", "working_dir", "anchor"],
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """This tool modifies filesystem (stores anchor file)"""
        return None  # Not read-only - stores anchor files

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool"""
        return ""

    def get_request_model(self):
        """Return the Pydantic model for request validation"""
        return AnchorSubmitRequest

    def requires_model(self) -> bool:
        """This is a utility tool that doesn't need an AI model"""
        return False

    async def prepare_prompt(self, request: AnchorSubmitRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: AnchorSubmitRequest, model_info: dict = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Validate agent anchor and return enforcement rules.

        Validates SHANK+ARM+FLUKE structure, detects phase drift,
        stores anchor to session directory, and returns role-based
        enforcement rules.

        Args:
            arguments: Tool arguments containing session_id, working_dir, anchor

        Returns:
            Anchor validation response with validated, drift_warning, enforcement, anchor_path
        """
        try:
            # Validate request
            request = AnchorSubmitRequest(**arguments)

            # Get project root (from session context or working_dir)
            session_context = arguments.get("_session_context")
            if session_context:
                project_root = Path(session_context.project_root)
            else:
                project_root = Path(request.working_dir)

            # Verify session exists
            hestai_dir = project_root / ".hestai"
            sessions_dir = hestai_dir / "sessions"
            active_dir = sessions_dir / "active"
            session_dir = active_dir / request.session_id

            if not session_dir.exists():
                raise FileNotFoundError(f"Session {request.session_id} not found in active sessions")

            # Validate anchor structure
            validation_result = self._validate_anchor_structure(request.anchor)
            if not validation_result["valid"]:
                raise ValueError(validation_result["error"])

            # Load session metadata to check for drift
            session_file = session_dir / "session.json"
            session_data = json.loads(session_file.read_text())

            # Detect drift (phase mismatch)
            drift_warning = self._detect_drift(request.anchor, session_data)

            # Store anchor to session directory
            anchor_path = session_dir / "anchor.json"
            anchor_path.write_text(json.dumps(request.anchor, indent=2))

            logger.info(f"Stored anchor for session {request.session_id}")

            # Get enforcement rules based on role
            role = request.anchor["SHANK"]["role"]
            enforcement = self._get_enforcement_rules(role)

            # Create response content
            content = {
                "validated": True,
                "drift_warning": drift_warning,
                "enforcement": enforcement,
                "anchor_path": str(anchor_path),
            }

            tool_output = ToolOutput(
                status="success",
                content=json.dumps(content, indent=2),
                content_type="json",
                metadata={"tool_name": self.name, "session_id": request.session_id},
            )

            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            logger.error(f"Error in anchor_submit: {str(e)}")
            error_output = ToolOutput(status="error", content=f"Error validating anchor: {str(e)}", content_type="text")
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _validate_anchor_structure(self, anchor: dict) -> dict[str, Any]:
        """
        Validate that anchor has complete SHANK+ARM+FLUKE structure.

        Args:
            anchor: Anchor dict to validate

        Returns:
            Validation result with valid bool and error message if invalid
        """
        # Check for required top-level components
        if "SHANK" not in anchor:
            return {"valid": False, "error": "Anchor missing required component: SHANK"}

        if "ARM" not in anchor:
            return {"valid": False, "error": "Anchor missing required component: ARM"}

        if "FLUKE" not in anchor:
            return {"valid": False, "error": "Anchor missing required component: FLUKE"}

        # Validate SHANK structure
        shank = anchor["SHANK"]
        required_shank_fields = ["role", "cognition", "archetypes", "key_constraints"]
        for field in required_shank_fields:
            if field not in shank:
                return {"valid": False, "error": f"SHANK missing required field: {field}"}

        # Validate ARM structure
        arm = anchor["ARM"]
        required_arm_fields = ["phase_context", "current_focus", "blockers"]
        for field in required_arm_fields:
            if field not in arm:
                return {"valid": False, "error": f"ARM missing required field: {field}"}

        # Validate FLUKE structure
        fluke = anchor["FLUKE"]
        required_fluke_fields = ["skills_loaded", "patterns_active"]
        for field in required_fluke_fields:
            if field not in fluke:
                return {"valid": False, "error": f"FLUKE missing required field: {field}"}

        return {"valid": True, "error": None}

    def _detect_drift(self, anchor: dict, session_data: dict) -> Optional[str]:
        """
        Detect phase drift between anchor and session metadata.

        Args:
            anchor: Agent anchor
            session_data: Session metadata

        Returns:
            Warning message if drift detected, None otherwise
        """
        # Extract phase from ARM.phase_context
        phase_context = anchor["ARM"]["phase_context"]
        session_focus = session_data.get("focus", "")

        # Simple heuristic: check if phase mentions (D0-D3 or B0-B4) match focus
        # This is a basic implementation - could be enhanced with more sophisticated logic
        phases = ["D0", "D1", "D2", "D3", "B0", "B1", "B2", "B3", "B4"]

        anchor_phase = None
        for phase in phases:
            if phase in phase_context:
                anchor_phase = phase
                break

        session_phase = None
        for phase in phases:
            if phase in session_focus:
                session_phase = phase
                break

        # If both phases detected and they differ, warn about drift
        if anchor_phase and session_phase and anchor_phase != session_phase:
            return f"Phase drift detected: Anchor shows {anchor_phase} but session focus is {session_phase}"

        return None

    def _get_enforcement_rules(self, role: str) -> dict[str, list[str]]:
        """
        Get enforcement rules for the given role.

        Args:
            role: Agent role name

        Returns:
            Enforcement rules dict with blocked_paths and delegation_required
        """
        # Look up role-specific enforcement or use default
        enforcement = ROLE_ENFORCEMENT.get(role, ROLE_ENFORCEMENT["default"])

        return {
            "blocked_paths": enforcement["blocked_paths"],
            "delegation_required": enforcement["delegation_required"],
        }

    def get_model_category(self) -> ToolModelCategory:
        """Return the model category for this tool"""
        return ToolModelCategory.FAST_RESPONSE  # Utility tool, no AI needed
