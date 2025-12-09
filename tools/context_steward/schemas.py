"""
Schema definitions for Context Steward v2 validation.

This module defines the expected structure and constraints for:
- PROJECT-CONTEXT.md (sections, LOC limits)
- current_state.oct (State Vector format)
- CONTEXT-NEGATIVES.oct (anti-pattern format)

These schemas are the authoritative source of truth for context file validation.
The Kernel validates against these schemas; the Shell cannot modify the Kernel.
"""

from dataclasses import dataclass
from typing import Any

# ============================================================================
# PROJECT-CONTEXT.md Schema
# ============================================================================

PROJECT_CONTEXT_SCHEMA = {
    "max_loc": 200,
    "warning_threshold_loc": 180,
    "required_sections": [
        "IDENTITY",
        "ARCHITECTURE",
        "CURRENT_STATE",
        "DEVELOPMENT_GUIDELINES",
        "QUICK_REFERENCES",
        "CONTEXT_LIFECYCLE",
    ],
    "identity_required_fields": [
        "NAME",
        "TYPE",
        "PURPOSE",
    ],
    "octave_syntax_patterns": [
        # Pattern: KEY::value or KEY::[items]
        r"^[A-Z_]+::",
        # Pattern: KEY::{dict}
        r"^[A-Z_]+::\{",
        # Pattern: KEY::\[list\]
        r"^[A-Z_]+::\[",
    ],
}


# ============================================================================
# State Vector (current_state.oct) Schema
# ============================================================================

STATE_VECTOR_SCHEMA = {
    "required_fields": [
        "IDENTITY",
        "AUTHORITY",
        "QUALITY",
        "FOCUS",
        "SIGNALS",
    ],
    "identity_subfields": {
        "required": ["project_name", "type", "purpose"],
        "optional": ["origin", "version"],
    },
    "authority_subfields": {
        "required": ["current_owner", "phase", "blocking_items"],
        "optional": ["session_id", "last_updated"],
    },
    "quality_subfields": {
        "required": ["branch", "lint_status", "typecheck_status", "test_status"],
        "optional": ["coverage", "build_status"],
    },
    "focus_subfields": {
        "required": ["top_3_active_items"],
        "optional": ["next_milestone", "dependencies"],
    },
    "signals_subfields": {
        "required": ["latest_commit", "dependent_projects"],
        "optional": ["last_deployment", "health_check"],
    },
    "valid_status_values": ["pass", "fail", "unknown", "n/a"],
    "valid_phases": [
        "D0",
        "D1",
        "D2",
        "D3",
        "B0",
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
        "maintenance",
    ],
}


# ============================================================================
# Context Negatives (CONTEXT-NEGATIVES.oct) Schema
# ============================================================================

CONTEXT_NEGATIVES_SCHEMA = {
    "min_anti_patterns": 10,
    "required_fields": [
        "pattern",
        "description",
        "instead",
        "severity",
    ],
    "valid_severity_values": ["low", "medium", "high", "critical"],
    "recommended_categories": [
        "deprecated_tools",
        "quality_gate_violations",
        "architecture_anti_patterns",
        "workflow_violations",
        "testing_mistakes",
        "documentation_errors",
        "security_issues",
        "performance_anti_patterns",
    ],
}


# ============================================================================
# LKG (Last Known Good) Schema
# ============================================================================

LKG_SCHEMA = {
    "snapshot_dir": ".lkg",
    "snapshot_extension": ".lkg",
    "metadata_extension": ".lkg.meta",
    "metadata_fields": {
        "timestamp": "ISO 8601 timestamp of snapshot creation",
        "original_path": "Original file path",
        "validator_version": "Version of validator that created snapshot",
        "validation_passed": "Boolean indicating validation status",
        "file_hash": "SHA256 hash of original file",
    },
}


# ============================================================================
# Validation Result Data Class
# ============================================================================


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metadata: dict[str, Any]

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)
        if not other.is_valid:
            self.is_valid = False


# ============================================================================
# Helper Functions
# ============================================================================


def get_project_context_required_sections() -> list[str]:
    """Get list of required sections for PROJECT-CONTEXT.md."""
    return PROJECT_CONTEXT_SCHEMA["required_sections"].copy()


def get_state_vector_required_fields() -> list[str]:
    """Get list of required fields for State Vector."""
    return STATE_VECTOR_SCHEMA["required_fields"].copy()


def get_context_negatives_required_fields() -> list[str]:
    """Get list of required fields for each anti-pattern."""
    return CONTEXT_NEGATIVES_SCHEMA["required_fields"].copy()


def get_valid_quality_status_values() -> list[str]:
    """Get list of valid quality status values."""
    return STATE_VECTOR_SCHEMA["valid_status_values"].copy()


def get_valid_severity_values() -> list[str]:
    """Get list of valid severity values for anti-patterns."""
    return CONTEXT_NEGATIVES_SCHEMA["valid_severity_values"].copy()


def get_valid_phases() -> list[str]:
    """Get list of valid HestAI workflow phases."""
    return STATE_VECTOR_SCHEMA["valid_phases"].copy()
