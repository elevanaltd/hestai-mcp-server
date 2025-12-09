"""
Context Validator - Kernel component for Context Steward v2.

This is DETERMINISTIC validation - no AI, no flexibility.
The Kernel validates the Shell; the Shell cannot modify the Kernel.

Validates:
- PROJECT-CONTEXT.md: Structure, LOC limits, required sections
- current_state.oct: State Vector format and required fields
- CONTEXT-NEGATIVES.oct: Anti-pattern structure and minimum count
- LKG (Last Known Good): Snapshot creation and recovery mechanisms
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .schemas import (
    CONTEXT_NEGATIVES_SCHEMA,
    LKG_SCHEMA,
    PROJECT_CONTEXT_SCHEMA,
    STATE_VECTOR_SCHEMA,
    ValidationResult,
    get_context_negatives_required_fields,
    get_project_context_required_sections,
    get_state_vector_required_fields,
    get_valid_phases,
    get_valid_quality_status_values,
    get_valid_severity_values,
)

# Version of this validator (used in LKG metadata)
VALIDATOR_VERSION = "2.0.0"


# ============================================================================
# PROJECT-CONTEXT.md Validation
# ============================================================================


def validate_project_context(content: str) -> ValidationResult:
    """
    Validate PROJECT-CONTEXT.md structure.

    Checks:
    - Required sections present
    - LOC limit (200 max, warning at 180)
    - Required IDENTITY fields
    - OCTAVE syntax correctness (if used)

    Args:
        content: File content to validate

    Returns:
        ValidationResult with validation status and details
    """
    result = ValidationResult(is_valid=True, errors=[], warnings=[], metadata={})

    # Count lines
    lines = content.split("\n")
    loc = len(lines)
    result.metadata["loc"] = loc

    # Check LOC limit
    max_loc = PROJECT_CONTEXT_SCHEMA["max_loc"]
    warning_threshold = PROJECT_CONTEXT_SCHEMA["warning_threshold_loc"]

    if loc > max_loc:
        result.add_error(f"LOC limit exceeded: {loc}/{max_loc} lines")
    elif loc > warning_threshold:
        result.add_warning(f"LOC approaching limit: {loc}/{max_loc} lines (warning at {warning_threshold})")

    # Check required sections
    required_sections = get_project_context_required_sections()
    found_sections = []

    for section in required_sections:
        # Match section headers like "## SECTION_NAME"
        pattern = rf"^##\s+{section}\s*$"
        if re.search(pattern, content, re.MULTILINE):
            found_sections.append(section)
        else:
            result.add_error(f"Missing required section: {section}")

    result.metadata["sections_found"] = len(found_sections)
    result.metadata["sections_required"] = len(required_sections)

    # Check IDENTITY required fields
    identity_match = re.search(r"##\s+IDENTITY\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if identity_match:
        identity_content = identity_match.group(1)
        for field in PROJECT_CONTEXT_SCHEMA["identity_required_fields"]:
            if not re.search(rf"^{field}::", identity_content, re.MULTILINE):
                result.add_error(f"Missing required IDENTITY field: {field}")

    # Validate OCTAVE syntax if present
    octave_issues = _validate_octave_syntax(content)
    if octave_issues:
        for issue in octave_issues:
            result.add_warning(f"OCTAVE syntax issue: {issue}")

    return result


def _validate_octave_syntax(content: str) -> list[str]:
    """
    Validate OCTAVE syntax patterns in content.

    Checks for common OCTAVE mistakes:
    - Missing brackets in list/dict assignments
    - Incorrect use of :: operator
    - Malformed nested structures

    Args:
        content: Content to check

    Returns:
        List of OCTAVE syntax issues found
    """
    issues = []

    # Find lines that look like OCTAVE but may have issues
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Check for OCTAVE assignment without proper brackets
        if "::" in line and not line.strip().startswith("#"):
            # Pattern should be KEY::value, KEY::[list], or KEY::{dict}
            if re.match(r"^[A-Z_]+::[^:\[\{\"'\d]", line.strip()):
                # Check if it looks like it should have brackets but doesn't
                if "," in line or line.strip().endswith(","):
                    issues.append(f"Line {i}: Missing brackets for list/dict assignment: {line.strip()[:50]}")

    return issues


# ============================================================================
# State Vector (current_state.oct) Validation
# ============================================================================


def validate_state_vector(content: str) -> ValidationResult:
    """
    Validate current_state.oct State Vector structure.

    Checks:
    - STATE_VECTOR:: wrapper present
    - All required fields present (IDENTITY, AUTHORITY, QUALITY, FOCUS, SIGNALS)
    - Required subfields for each section
    - Valid status values (pass/fail/unknown/n/a)
    - Valid phase values (D0-D3, B0-B5, maintenance)

    Args:
        content: File content to validate

    Returns:
        ValidationResult with validation status and details
    """
    result = ValidationResult(is_valid=True, errors=[], warnings=[], metadata={})

    # Check for STATE_VECTOR:: wrapper
    if not re.search(r"STATE_VECTOR::\[", content):
        result.add_error("Missing STATE_VECTOR::[ wrapper")
        return result

    # Check required fields
    required_fields = get_state_vector_required_fields()
    found_fields = []

    for field in required_fields:
        pattern = rf"{field}::\s*\{{"
        if re.search(pattern, content):
            found_fields.append(field)
        else:
            result.add_error(f"Missing required field: {field}")

    result.metadata["fields_found"] = len(found_fields)
    result.metadata["fields_required"] = len(required_fields)

    # Validate IDENTITY subfields
    _validate_state_vector_section(
        content,
        "IDENTITY",
        STATE_VECTOR_SCHEMA["identity_subfields"]["required"],
        result,
    )

    # Validate AUTHORITY subfields
    _validate_state_vector_section(
        content,
        "AUTHORITY",
        STATE_VECTOR_SCHEMA["authority_subfields"]["required"],
        result,
    )

    # Validate QUALITY subfields and status values
    quality_result = _validate_state_vector_section(
        content,
        "QUALITY",
        STATE_VECTOR_SCHEMA["quality_subfields"]["required"],
        result,
    )

    # Check quality status values
    if quality_result:
        _validate_quality_status_values(quality_result, result)

    # Validate FOCUS subfields
    _validate_state_vector_section(
        content,
        "FOCUS",
        STATE_VECTOR_SCHEMA["focus_subfields"]["required"],
        result,
    )

    # Validate SIGNALS subfields
    _validate_state_vector_section(
        content,
        "SIGNALS",
        STATE_VECTOR_SCHEMA["signals_subfields"]["required"],
        result,
    )

    # Validate phase value
    _validate_phase_value(content, result)

    return result


def _validate_state_vector_section(
    content: str, section: str, required_subfields: list[str], result: ValidationResult
) -> Optional[str]:
    """
    Validate a State Vector section for required subfields.

    Args:
        content: Full content
        section: Section name (e.g., "IDENTITY")
        required_subfields: List of required subfield names
        result: ValidationResult to update

    Returns:
        Section content if found, None otherwise
    """
    section_pattern = rf"{section}::\s*\{{([^}}]+)\}}"
    section_match = re.search(section_pattern, content, re.DOTALL)

    if not section_match:
        return None

    section_content = section_match.group(1)

    for subfield in required_subfields:
        if not re.search(rf"{subfield}:", section_content):
            result.add_error(f"Missing required {section} subfield: {subfield}")

    return section_content


def _validate_quality_status_values(section_content: str, result: ValidationResult) -> None:
    """
    Validate quality status values are valid.

    Args:
        section_content: QUALITY section content
        result: ValidationResult to update
    """
    valid_values = get_valid_quality_status_values()
    status_fields = ["lint_status", "typecheck_status", "test_status"]

    for field in status_fields:
        match = re.search(rf'{field}:"([^"]+)"', section_content)
        if match:
            value = match.group(1)
            if value not in valid_values:
                result.add_warning(f"Invalid {field} value: '{value}' (valid: {', '.join(valid_values)})")


def _validate_phase_value(content: str, result: ValidationResult) -> None:
    """
    Validate phase value is a valid HestAI workflow phase.

    Args:
        content: Full content
        result: ValidationResult to update
    """
    valid_phases = get_valid_phases()
    phase_match = re.search(r'phase:"([^"]+)"', content)

    if phase_match:
        phase = phase_match.group(1)
        if phase not in valid_phases:
            result.add_warning(f"Invalid phase value: '{phase}' (valid: {', '.join(valid_phases)})")


# ============================================================================
# Context Negatives (CONTEXT-NEGATIVES.oct) Validation
# ============================================================================


def validate_context_negatives(content: str) -> ValidationResult:
    """
    Validate CONTEXT-NEGATIVES.oct structure.

    Checks:
    - Minimum anti-pattern count (10+)
    - Required fields for each anti-pattern
    - Valid severity values

    Args:
        content: File content to validate

    Returns:
        ValidationResult with validation status and details
    """
    result = ValidationResult(is_valid=True, errors=[], warnings=[], metadata={})

    # Check for CONTEXT_NEGATIVES:: wrapper
    if not re.search(r"CONTEXT_NEGATIVES::\[", content):
        result.add_error("Missing CONTEXT_NEGATIVES::[ wrapper")
        return result

    # Count anti-patterns
    anti_patterns = re.findall(r"ANTI_PATTERN_\d+::\s*\{", content)
    anti_pattern_count = len(anti_patterns)
    result.metadata["anti_pattern_count"] = anti_pattern_count

    min_patterns = CONTEXT_NEGATIVES_SCHEMA["min_anti_patterns"]
    if anti_pattern_count < min_patterns:
        result.add_error(f"Insufficient anti-patterns: {anti_pattern_count} (minimum: {min_patterns})")

    # Validate each anti-pattern has required fields
    required_fields = get_context_negatives_required_fields()
    valid_severities = get_valid_severity_values()

    for i in range(1, anti_pattern_count + 1):
        pattern_match = re.search(rf"ANTI_PATTERN_{i}::\s*\{{([^}}]+)\}}", content, re.DOTALL)

        if pattern_match:
            pattern_content = pattern_match.group(1)

            # Check required fields
            for field in required_fields:
                if not re.search(rf"{field}:", pattern_content):
                    result.add_error(f"ANTI_PATTERN_{i} missing required field: {field}")

            # Validate severity value
            severity_match = re.search(r'severity:"([^"]+)"', pattern_content)
            if severity_match:
                severity = severity_match.group(1)
                if severity not in valid_severities:
                    result.add_warning(
                        f"ANTI_PATTERN_{i} invalid severity: '{severity}' (valid: {', '.join(valid_severities)})"
                    )

    return result


# ============================================================================
# LKG (Last Known Good) Snapshot and Recovery
# ============================================================================


def create_lkg_snapshot(file_path: Path) -> None:
    """
    Create Last Known Good snapshot after validation passes.

    Creates:
    - .lkg/{filename}.lkg: Snapshot of file content
    - .lkg/{filename}.lkg.meta: Metadata (timestamp, hash, validator version)

    Args:
        file_path: Path to file to snapshot
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Cannot snapshot non-existent file: {file_path}")

    # Create LKG directory if it doesn't exist
    lkg_dir = file_path.parent / LKG_SCHEMA["snapshot_dir"]
    lkg_dir.mkdir(exist_ok=True)

    # Read file content
    content = file_path.read_text(encoding="utf-8")

    # Calculate file hash
    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Create snapshot file
    snapshot_file = lkg_dir / f"{file_path.name}{LKG_SCHEMA['snapshot_extension']}"
    snapshot_file.write_text(content, encoding="utf-8")

    # Create metadata file
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "original_path": str(file_path.absolute()),
        "validator_version": VALIDATOR_VERSION,
        "validation_passed": True,
        "file_hash": file_hash,
    }

    metadata_file = lkg_dir / f"{file_path.name}{LKG_SCHEMA['metadata_extension']}"
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def recover_from_lkg(file_path: Path) -> bool:
    """
    Recover corrupted context from LKG snapshot.

    Args:
        file_path: Path to file to recover

    Returns:
        True if recovery successful, False if no LKG snapshot exists
    """
    file_path = Path(file_path)

    # Find LKG snapshot
    lkg_dir = file_path.parent / LKG_SCHEMA["snapshot_dir"]
    snapshot_file = lkg_dir / f"{file_path.name}{LKG_SCHEMA['snapshot_extension']}"

    if not snapshot_file.exists():
        return False

    # Restore from snapshot
    content = snapshot_file.read_text(encoding="utf-8")
    file_path.write_text(content, encoding="utf-8")

    return True


def get_lkg_metadata(file_path: Path) -> Optional[dict[str, Any]]:
    """
    Get metadata for LKG snapshot.

    Args:
        file_path: Path to original file

    Returns:
        Metadata dict if snapshot exists, None otherwise
    """
    file_path = Path(file_path)
    lkg_dir = file_path.parent / LKG_SCHEMA["snapshot_dir"]
    metadata_file = lkg_dir / f"{file_path.name}{LKG_SCHEMA['metadata_extension']}"

    if not metadata_file.exists():
        return None

    return json.loads(metadata_file.read_text(encoding="utf-8"))
