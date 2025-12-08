"""OCTAVE utilities for Context Steward AI integration.

Provides robust OCTAVE parsing to handle LLM-generated responses in OCTAVE format
with potential conversational preamble and complex nested structures.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def extract_octave_response(raw_response: str) -> Optional[str]:
    """Extract RESPONSE OCTAVE block from LLM output.

    The LLM may include conversational preamble before/after the OCTAVE block.
    This function extracts just the RESPONSE portion for parsing.

    Args:
        raw_response: Raw LLM response that may contain OCTAVE

    Returns:
        Extracted OCTAVE string if found, None otherwise

    Example:
        >>> raw = "Here's the result:\\nRESPONSE::[STATUS::success]"
        >>> extract_octave_response(raw)
        'RESPONSE::[STATUS::success]'
    """
    # Find RESPONSE::[ and then match brackets with proper depth tracking
    if "RESPONSE::[" not in raw_response:
        return None

    start_idx = raw_response.find("RESPONSE::[")
    if start_idx == -1:
        return None

    # Track bracket depth to find matching closing bracket
    depth = 0
    i = start_idx + 11  # Skip "RESPONSE::["
    in_quotes = False
    escape_next = False

    while i < len(raw_response):
        char = raw_response[i]

        # Handle escape sequences
        if escape_next:
            escape_next = False
            i += 1
            continue

        if char == "\\" and in_quotes:
            escape_next = True
            i += 1
            continue

        # Handle quotes
        if char == '"':
            in_quotes = not in_quotes
            i += 1
            continue

        # Only count brackets outside quotes
        if not in_quotes:
            if char == "[":
                depth += 1
            elif char == "]":
                if depth == 0:
                    # Found the matching closing bracket
                    return raw_response[start_idx : i + 1]
                depth -= 1

        i += 1

    # No matching bracket found
    return None


def _parse_value(value_str: str) -> Any:
    """Parse a value from OCTAVE format.

    Handles:
    - Quoted strings: "text"
    - Arrays: [item1, item2]
    - Objects: {key::value, key2::value2}
    - Simple values: bareword

    Args:
        value_str: String representation of value

    Returns:
        Parsed value (str, list, dict, or original string)
    """
    value_str = value_str.strip()

    # Empty value
    if not value_str:
        return None

    # Quoted string
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]  # Remove quotes

    # Array: [item1, item2, ...]
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1].strip()
        if not inner:
            return []

        # Split by comma, but respect nested structures
        items = _split_by_comma(inner)
        return [_parse_value(item.strip()) for item in items]

    # Object: {key::value, key2::value2, ...}
    if value_str.startswith("{") and value_str.endswith("}"):
        inner = value_str[1:-1].strip()
        if not inner:
            return {}

        obj = {}
        # Split by comma, but respect nested structures
        pairs = _split_by_comma(inner)
        for pair in pairs:
            pair = pair.strip()
            if "::" in pair:
                key, val = pair.split("::", 1)
                obj[key.strip()] = _parse_value(val.strip())

        return obj

    # Simple bareword value
    return value_str


def _split_by_comma(text: str) -> list[str]:
    """Split text by comma, respecting nested brackets and braces.

    Args:
        text: Text to split

    Returns:
        List of split segments
    """
    segments = []
    current = []
    depth_square = 0
    depth_curly = 0
    depth_quote = False

    for char in text:
        if char == '"' and (not current or current[-1] != "\\"):
            depth_quote = not depth_quote
            current.append(char)
        elif depth_quote:
            current.append(char)
        elif char == "[":
            depth_square += 1
            current.append(char)
        elif char == "]":
            depth_square -= 1
            current.append(char)
        elif char == "{":
            depth_curly += 1
            current.append(char)
        elif char == "}":
            depth_curly -= 1
            current.append(char)
        elif char == "," and depth_square == 0 and depth_curly == 0:
            segments.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        segments.append("".join(current))

    return segments


def parse_context_steward_response(raw_response: str) -> dict[str, Any]:
    """Parse RESPONSE OCTAVE block with robust error handling.

    Handles:
    - Conversational preamble before/after OCTAVE
    - Nested structures (arrays, objects)
    - Parse errors with debug logging

    Args:
        raw_response: Raw LLM response containing OCTAVE

    Returns:
        Dictionary with parsed response fields:
        - status: "success", "partial", "failure", or "error"
        - summary: Summary text if present
        - files_analyzed: List of file paths
        - changes: List of change descriptions
        - artifacts: List of artifact dictionaries
        - error: Error message if parsing failed
        - raw_response: First 500 chars of raw response on error

    Example:
        >>> response = parse_context_steward_response(octave_string)
        >>> if response["status"] == "success":
        ...     print(response["summary"])
    """
    octave_content = extract_octave_response(raw_response)
    if not octave_content:
        logger.warning("No RESPONSE block found in LLM output")
        return {
            "status": "error",
            "error": "No RESPONSE block found in output",
            "raw_response": raw_response[:500],  # First 500 chars for debugging
        }

    try:
        # Extract the content between RESPONSE::[ and ]
        # Remove the RESPONSE::[ prefix and ] suffix
        if not octave_content.startswith("RESPONSE::["):
            raise ValueError("Invalid RESPONSE format")

        content = octave_content[11:-1].strip()  # Remove "RESPONSE::[" and "]"

        # Parse the key-value pairs
        result = {
            "status": "unknown",
            "summary": None,
            "files_analyzed": [],
            "changes": [],
            "artifacts": [],
            "changelog_entry": None,
            "compaction_performed": False,
        }

        # Split by comma at top level
        pairs = _split_by_comma(content)

        for pair in pairs:
            pair = pair.strip()
            if not pair or "::" not in pair:
                continue

            key, value = pair.split("::", 1)
            key = key.strip().lower()
            value = value.strip()

            # Parse based on key
            if key == "status":
                result["status"] = _parse_value(value)
            elif key == "summary":
                result["summary"] = _parse_value(value)
            elif key == "files_analyzed":
                result["files_analyzed"] = _parse_value(value) or []
            elif key == "changes":
                result["changes"] = _parse_value(value) or []
            elif key == "artifacts":
                result["artifacts"] = _parse_value(value) or []
            elif key == "changelog_entry":
                result["changelog_entry"] = _parse_value(value)
            elif key == "compaction_performed":
                parsed_val = _parse_value(value)
                result["compaction_performed"] = parsed_val in (True, "true", "True")

        logger.debug(f"Successfully parsed RESPONSE: {result['status']}")
        return result

    except Exception as e:
        logger.error(f"OCTAVE parse error: {e}")
        logger.debug(f"Failed to parse OCTAVE: {octave_content[:500]}")
        return {
            "status": "error",
            "error": f"OCTAVE parse error: {e}",
            "raw_response": raw_response[:500],
        }
