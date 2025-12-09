"""Context Steward utilities for HestAI MCP Server.

This module provides utilities for the Context Steward AI integration,
including XML parsing and CDATA escaping for safe transcript handling,
Kernel validation components for Context Steward v2, and Shell layer
shared modules (visibility rules, file lookup, utilities).
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
from .file_lookup import find_context_file
from .inbox import (
    ensure_inbox_structure,
    get_inbox_status,
    process_inbox_item,
    submit_to_inbox,
    update_index,
)
from .schemas import (
    CONTEXT_NEGATIVES_SCHEMA,
    LKG_SCHEMA,
    PROJECT_CONTEXT_SCHEMA,
    STATE_VECTOR_SCHEMA,
)
from .utils import append_changelog, sanitize_filename
from .visibility_rules import DOCUMENT_TYPES, VISIBILITY_RULES
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
    # Shell layer shared modules
    "VISIBILITY_RULES",
    "DOCUMENT_TYPES",
    "find_context_file",
    "sanitize_filename",
    "append_changelog",
    # Inbox management
    "ensure_inbox_structure",
    "submit_to_inbox",
    "process_inbox_item",
    "update_index",
    "get_inbox_status",
]
