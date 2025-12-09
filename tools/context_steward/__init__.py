"""Context Steward utilities for HestAI MCP Server.

This module provides utilities for the Context Steward AI integration,
including XML parsing and CDATA escaping for safe transcript handling,
and Kernel validation components for Context Steward v2.
"""

from .context_validator import (
    ValidationResult,
    create_lkg_snapshot,
    get_lkg_metadata,
    recover_from_lkg,
    validate_context_negatives,
    validate_project_context,
    validate_state_vector,
)
from .schemas import (
    CONTEXT_NEGATIVES_SCHEMA,
    LKG_SCHEMA,
    PROJECT_CONTEXT_SCHEMA,
    STATE_VECTOR_SCHEMA,
)
from .xml_utils import (
    escape_cdata_content,
    extract_xml_response,
    parse_context_steward_response,
    wrap_cdata,
)

__all__ = [
    # XML utilities
    "escape_cdata_content",
    "wrap_cdata",
    "extract_xml_response",
    "parse_context_steward_response",
    # Validation components (Kernel)
    "ValidationResult",
    "validate_project_context",
    "validate_state_vector",
    "validate_context_negatives",
    "create_lkg_snapshot",
    "recover_from_lkg",
    "get_lkg_metadata",
    # Schemas
    "PROJECT_CONTEXT_SCHEMA",
    "STATE_VECTOR_SCHEMA",
    "CONTEXT_NEGATIVES_SCHEMA",
    "LKG_SCHEMA",
]
