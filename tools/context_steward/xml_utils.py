"""XML utilities for Context Steward AI integration.

Provides robust XML parsing and CDATA escaping to handle LLM-generated
XML responses with potential conversational preamble and CDATA injection risks.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

logger = logging.getLogger(__name__)


def escape_cdata_content(content: str) -> str:
    """Escape ]]> sequences for safe CDATA embedding.

    If transcript content contains ]]>, it breaks XML parsing. This function
    escapes it using the standard CDATA escape pattern.

    Args:
        content: Raw string content that may contain ]]>

    Returns:
        Escaped content safe for CDATA wrapping

    Example:
        >>> escape_cdata_content("some text ]]> more text")
        'some text ]]]]><![CDATA[> more text'
    """
    return content.replace("]]>", "]]]]><![CDATA[>")


def wrap_cdata(content: str) -> str:
    """Wrap content in CDATA with proper escaping.

    Args:
        content: Raw string content to wrap

    Returns:
        CDATA-wrapped content with escaped sequences

    Example:
        >>> wrap_cdata("hello world")
        '<![CDATA[hello world]]>'
        >>> wrap_cdata("text with ]]> sequence")
        '<![CDATA[text with ]]]]><![CDATA[> sequence]]>'
    """
    escaped = escape_cdata_content(content)
    return f"<![CDATA[{escaped}]]>"


def extract_xml_response(raw_response: str) -> Optional[str]:
    """Extract context-steward-response XML from LLM output.

    The LLM may include conversational preamble before/after the XML block.
    This function extracts just the XML portion for parsing.

    Args:
        raw_response: Raw LLM response that may contain XML

    Returns:
        Extracted XML string if found, None otherwise

    Example:
        >>> raw = "Here's the result:\\n<context-steward-response>...</context-steward-response>"
        >>> extract_xml_response(raw)
        '<context-steward-response>...</context-steward-response>'
    """
    pattern = r"<context-steward-response.*?>.*?</context-steward-response>"
    match = re.search(pattern, raw_response, re.DOTALL)
    return match.group(0) if match else None


def _get_text(root: ET.Element, tag: str) -> Optional[str]:
    """Safely extract text from XML element.

    Args:
        root: XML root element
        tag: Tag name to find

    Returns:
        Text content if found, None otherwise
    """
    elem = root.find(tag)
    return elem.text if elem is not None else None


def _extract_artifacts(root: ET.Element) -> list[dict[str, str]]:
    """Extract artifacts from XML response.

    Args:
        root: XML root element

    Returns:
        List of artifact dictionaries with type, label, and content
    """
    artifacts = []
    artifacts_elem = root.find("artifacts")
    if artifacts_elem is not None:
        for artifact in artifacts_elem.findall("artifact"):
            artifacts.append(
                {
                    "type": artifact.get("type", ""),
                    "label": artifact.get("label", ""),
                    "content": artifact.text or "",
                }
            )
    return artifacts


def _extract_risks(root: ET.Element) -> list[dict[str, str]]:
    """Extract risks from XML response.

    Args:
        root: XML root element

    Returns:
        List of risk dictionaries with severity and description
    """
    risks = []
    risks_elem = root.find("risks")
    if risks_elem is not None:
        for risk in risks_elem.findall("risk"):
            risks.append(
                {
                    "severity": risk.get("severity", ""),
                    "description": risk.text or "",
                }
            )
    return risks


def _extract_actions(root: ET.Element) -> list[dict[str, str]]:
    """Extract next actions from XML response.

    Args:
        root: XML root element

    Returns:
        List of action dictionaries with owner and description
    """
    actions = []
    actions_elem = root.find("next-actions")
    if actions_elem is not None:
        for action in actions_elem.findall("action"):
            actions.append(
                {
                    "owner": action.get("owner", ""),
                    "description": action.text or "",
                }
            )
    return actions


def parse_context_steward_response(raw_response: str) -> dict[str, Any]:
    """Parse context-steward-response XML with robust error handling.

    Handles:
    - Conversational preamble before/after XML
    - Flexible tag ordering (not strict)
    - Parse errors with debug logging

    Args:
        raw_response: Raw LLM response containing XML

    Returns:
        Dictionary with parsed response fields:
        - status: "success", "error", or extracted status
        - task_id: Task identifier if present
        - summary: Summary text if present
        - artifacts: List of artifact dictionaries
        - risks: List of risk dictionaries
        - next_actions: List of action dictionaries
        - error: Error message if parsing failed
        - raw_response: First 500 chars of raw response on error

    Example:
        >>> response = parse_context_steward_response(xml_string)
        >>> if response["status"] == "success":
        ...     print(response["summary"])
    """
    xml_content = extract_xml_response(raw_response)
    if not xml_content:
        logger.warning("No context-steward-response XML found in LLM output")
        return {
            "status": "error",
            "error": "No context-steward-response XML found",
            "raw_response": raw_response[:500],  # First 500 chars for debugging
        }

    try:
        root = ET.fromstring(xml_content)

        # Extract fields flexibly (not requiring strict order)
        result = {
            "status": _get_text(root, "status") or "unknown",
            "task_id": _get_text(root, "task-id"),
            "summary": _get_text(root, "summary"),
            "artifacts": _extract_artifacts(root),
            "risks": _extract_risks(root),
            "next_actions": _extract_actions(root),
        }

        logger.debug(f"Successfully parsed context-steward-response: {result['status']}")
        return result

    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        logger.debug(f"Failed to parse XML: {xml_content[:500]}")
        return {
            "status": "error",
            "error": f"XML parse error: {e}",
            "raw_response": raw_response[:500],
        }
    except Exception as e:
        logger.error(f"Unexpected error parsing context-steward-response: {e}")
        return {
            "status": "error",
            "error": f"Unexpected error: {e}",
            "raw_response": raw_response[:500],
        }
