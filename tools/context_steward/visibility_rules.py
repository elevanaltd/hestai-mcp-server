"""
Visibility rules and document type configurations for Context Steward.

Defines where different document types should be placed and how they should
be formatted according to ADR-003 visibility protocols.

Part of Context Steward v2 Shell layer.
"""

from typing import TypedDict


class VisibilityRule(TypedDict):
    """Visibility rule for a document type."""

    path: str
    format: str


class DocumentTypeConfig(TypedDict, total=False):
    """Document type configuration for document_submit tool."""

    destination: str
    format: str
    compress: bool
    requires_validation: bool


# Visibility rules from ADR-003
# Used by requestdoc tool for legacy compatibility
VISIBILITY_RULES: dict[str, VisibilityRule] = {
    "adr": {"path": "docs/adr/", "format": "ADR_template"},
    "context_update": {"path": ".hestai/context/", "format": "OCTAVE"},
    "session_note": {"path": ".hestai/sessions/", "format": "OCTAVE"},
    "workflow_update": {"path": ".hestai/workflow/", "format": "OCTAVE"},
}

# Document types for document_submit tool (Context Steward v2)
DOCUMENT_TYPES: dict[str, DocumentTypeConfig] = {
    "adr": {
        "destination": "docs/adr/",
        "format": "ADR_template",
        "compress": False,
    },
    "session_note": {
        "destination": ".hestai/sessions/notes/",
        "format": "OCTAVE",
        "compress": True,
    },
    "workflow": {
        "destination": ".hestai/workflow/",
        "format": "OCTAVE",
        "compress": True,
    },
    "config": {
        "destination": ".claude/",
        "format": "preserve",
        "compress": False,
        "requires_validation": True,
    },
}
