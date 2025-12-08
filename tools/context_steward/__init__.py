"""Context Steward utilities for HestAI MCP Server.

This module provides utilities for the Context Steward AI integration,
including XML parsing and CDATA escaping for safe transcript handling.
"""

from .xml_utils import (
    escape_cdata_content,
    extract_xml_response,
    parse_context_steward_response,
    wrap_cdata,
)

__all__ = [
    "escape_cdata_content",
    "wrap_cdata",
    "extract_xml_response",
    "parse_context_steward_response",
]
