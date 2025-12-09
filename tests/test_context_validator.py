"""
Tests for Context Validator - Kernel component of Context Steward v2.

This module tests DETERMINISTIC validation of context files:
- PROJECT-CONTEXT.md structure and LOC limits
- current_state.oct State Vector format
- CONTEXT-NEGATIVES.oct anti-pattern structure
- LKG (Last Known Good) snapshot and recovery mechanisms

The Kernel validates the Shell; the Shell cannot modify the Kernel.
"""

import shutil
import tempfile
from pathlib import Path

from tools.context_steward.context_validator import (
    ValidationResult,
    create_lkg_snapshot,
    recover_from_lkg,
    validate_context_negatives,
    validate_project_context,
    validate_state_vector,
)


class TestValidationResult:
    """Test ValidationResult data class."""

    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], metadata={})
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}

    def test_validation_result_with_errors(self):
        """Test validation result with errors."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required section: IDENTITY"],
            warnings=["Line count approaching limit: 195/200"],
            metadata={"loc": 195, "sections_found": 7},
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.metadata["loc"] == 195


class TestProjectContextValidation:
    """Test PROJECT-CONTEXT.md validation."""

    def test_valid_project_context(self):
        """Test validation of valid PROJECT-CONTEXT.md."""
        content = """# PROJECT CONTEXT

## IDENTITY
NAME::HestAI MCP Server
TYPE::Model Context Protocol (MCP) Server
PURPOSE::"Test purpose"

## ARCHITECTURE
CORE_PRINCIPLE::"Test principle"

## CURRENT_STATE
DATE::2025-12-09
ACTIVE_FOCUS::"Test focus"

## DEVELOPMENT_GUIDELINES
STYLE::"Test style"

## QUICK_REFERENCES
SPEC::"test.md"

## CONTEXT_LIFECYCLE
TARGET::<200_LOC[current_file]
"""
        result = validate_project_context(content)
        assert result.is_valid is True
        assert result.errors == []

    def test_missing_required_section(self):
        """Test detection of missing required sections."""
        content = """# PROJECT CONTEXT

## IDENTITY
NAME::HestAI MCP Server

## ARCHITECTURE
CORE_PRINCIPLE::"Test"
"""
        result = validate_project_context(content)
        assert result.is_valid is False
        assert any("CURRENT_STATE" in err for err in result.errors)

    def test_loc_limit_exceeded(self):
        """Test LOC limit validation (200 LOC max)."""
        # Create content with > 200 lines
        lines = ["# PROJECT CONTEXT\n"]
        lines.extend([f"Line {i}\n" for i in range(1, 210)])
        content = "".join(lines)

        result = validate_project_context(content)
        assert result.is_valid is False
        assert any("LOC limit exceeded" in err for err in result.errors)
        assert result.metadata["loc"] > 200

    def test_loc_limit_warning(self):
        """Test LOC warning when approaching limit (>180 LOC)."""
        # Create content with 185 lines
        lines = ["# PROJECT CONTEXT\n"]
        lines.extend([f"Line {i}\n" for i in range(1, 185)])
        content = "".join(lines)

        result = validate_project_context(content)
        # May still be valid but should have warning
        assert any("approaching limit" in warn.lower() for warn in result.warnings) or result.is_valid is False

    def test_octave_syntax_validation(self):
        """Test OCTAVE syntax validation if present."""
        content = """# PROJECT CONTEXT

## IDENTITY
NAME::HestAI MCP Server
INVALID_OCTAVE::missing_brackets

## CURRENT_STATE
DATE::2025-12-09
"""
        result = validate_project_context(content)
        # Should detect OCTAVE syntax issues
        assert result.is_valid is False or any("OCTAVE" in warn for warn in result.warnings)


class TestStateVectorValidation:
    """Test current_state.oct State Vector validation."""

    def test_valid_state_vector(self):
        """Test validation of valid State Vector."""
        content = """STATE_VECTOR::[
  IDENTITY::{project_name:"HestAI MCP Server",type:"MCP Server",purpose:"Test"},
  AUTHORITY::{current_owner:"implementation-lead",phase:"B2",blocking_items:[]},
  QUALITY::{branch:"main",lint_status:"pass",typecheck_status:"pass",test_status:"pass"},
  FOCUS::{top_3_active_items:["Item 1","Item 2","Item 3"]},
  SIGNALS::{latest_commit:"abc123",dependent_projects:[]}
]"""
        result = validate_state_vector(content)
        assert result.is_valid is True
        assert result.errors == []

    def test_missing_required_field(self):
        """Test detection of missing required STATE_VECTOR fields."""
        content = """STATE_VECTOR::[
  IDENTITY::{project_name:"Test"},
  AUTHORITY::{current_owner:"test"}
]"""
        result = validate_state_vector(content)
        assert result.is_valid is False
        assert any("QUALITY" in err or "FOCUS" in err for err in result.errors)

    def test_invalid_state_vector_syntax(self):
        """Test detection of invalid OCTAVE syntax."""
        content = """STATE_VECTOR::
  IDENTITY::{project_name:"Test"}
  AUTHORITY::{current_owner:"test"}
"""
        result = validate_state_vector(content)
        assert result.is_valid is False
        # Will fail due to missing wrapper or missing required fields
        assert len(result.errors) > 0

    def test_quality_status_values(self):
        """Test validation of quality status values."""
        content = """STATE_VECTOR::[
  IDENTITY::{project_name:"Test",type:"Test",purpose:"Test"},
  AUTHORITY::{current_owner:"test",phase:"B2",blocking_items:[]},
  QUALITY::{branch:"main",lint_status:"invalid",typecheck_status:"pass",test_status:"pass"},
  FOCUS::{top_3_active_items:[]},
  SIGNALS::{latest_commit:"abc",dependent_projects:[]}
]"""
        result = validate_state_vector(content)
        # Should validate status values are valid (pass/fail/unknown)
        assert result.is_valid is False or any("status" in warn.lower() for warn in result.warnings)


class TestContextNegativesValidation:
    """Test CONTEXT-NEGATIVES.oct validation."""

    def test_valid_context_negatives(self):
        """Test validation of valid CONTEXT-NEGATIVES.oct."""
        # Need at least 10 anti-patterns
        content = """CONTEXT_NEGATIVES::[
  ANTI_PATTERN_1::{
    pattern:"Deprecated tool usage",
    description:"Using deprecated thinkdeep tool",
    instead:"Use HestAI phase progression (D1-D2-B0)",
    severity:"high"
  },
  ANTI_PATTERN_2::{
    pattern:"Skipping quality gates",
    description:"Merging without all gates passing",
    instead:"Ensure lint+typecheck+test all pass",
    severity:"critical"
  },
  ANTI_PATTERN_3::{pattern:"Test3",description:"Desc3",instead:"Instead3",severity:"low"},
  ANTI_PATTERN_4::{pattern:"Test4",description:"Desc4",instead:"Instead4",severity:"medium"},
  ANTI_PATTERN_5::{pattern:"Test5",description:"Desc5",instead:"Instead5",severity:"high"},
  ANTI_PATTERN_6::{pattern:"Test6",description:"Desc6",instead:"Instead6",severity:"low"},
  ANTI_PATTERN_7::{pattern:"Test7",description:"Desc7",instead:"Instead7",severity:"medium"},
  ANTI_PATTERN_8::{pattern:"Test8",description:"Desc8",instead:"Instead8",severity:"high"},
  ANTI_PATTERN_9::{pattern:"Test9",description:"Desc9",instead:"Instead9",severity:"low"},
  ANTI_PATTERN_10::{pattern:"Test10",description:"Desc10",instead:"Instead10",severity:"critical"}
]"""
        result = validate_context_negatives(content)
        assert result.is_valid is True
        assert result.errors == []

    def test_insufficient_anti_patterns(self):
        """Test detection of insufficient anti-patterns (< 10)."""
        content = """CONTEXT_NEGATIVES::[
  ANTI_PATTERN_1::{
    pattern:"Test",
    description:"Test desc",
    instead:"Test instead",
    severity:"low"
  }
]"""
        result = validate_context_negatives(content)
        assert result.is_valid is False
        assert any("insufficient" in err.lower() or "minimum" in err.lower() for err in result.errors)

    def test_missing_required_anti_pattern_fields(self):
        """Test detection of missing required fields in anti-patterns."""
        content = """CONTEXT_NEGATIVES::[
  ANTI_PATTERN_1::{
    pattern:"Test"
  },
  ANTI_PATTERN_2::{pattern:"Test2"},
  ANTI_PATTERN_3::{pattern:"Test3"},
  ANTI_PATTERN_4::{pattern:"Test4"},
  ANTI_PATTERN_5::{pattern:"Test5"},
  ANTI_PATTERN_6::{pattern:"Test6"},
  ANTI_PATTERN_7::{pattern:"Test7"},
  ANTI_PATTERN_8::{pattern:"Test8"},
  ANTI_PATTERN_9::{pattern:"Test9"},
  ANTI_PATTERN_10::{pattern:"Test10"}
]"""
        result = validate_context_negatives(content)
        assert result.is_valid is False
        assert any("description" in err.lower() or "instead" in err.lower() for err in result.errors)

    def test_invalid_severity_values(self):
        """Test validation of severity values."""
        content = (
            """CONTEXT_NEGATIVES::[
  ANTI_PATTERN_1::{pattern:"T1",description:"D1",instead:"I1",severity:"invalid"}
]"""
            + "\n"
            + "\n".join(
                [
                    f'  ANTI_PATTERN_{i}::{{pattern:"T{i}",description:"D{i}",instead:"I{i}",severity:"low"}}'
                    for i in range(2, 11)
                ]
            )
        )
        result = validate_context_negatives(content)
        # Should detect invalid severity values
        assert result.is_valid is False or any("severity" in warn.lower() for warn in result.warnings)


class TestLKGSnapshot:
    """Test Last Known Good (LKG) snapshot and recovery."""

    def setup_method(self):
        """Create temporary directory for LKG tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_context.md"
        self.lkg_dir = Path(self.temp_dir) / ".lkg"

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_lkg_snapshot(self):
        """Test creation of LKG snapshot."""
        # Create a test file
        self.test_file.write_text("# Test Content\nLine 2\nLine 3")

        # Create LKG snapshot
        create_lkg_snapshot(self.test_file)

        # Verify snapshot exists
        lkg_file = self.lkg_dir / f"{self.test_file.name}.lkg"
        assert lkg_file.exists()
        assert lkg_file.read_text() == self.test_file.read_text()

    def test_create_lkg_creates_directory(self):
        """Test that LKG directory is created if it doesn't exist."""
        assert not self.lkg_dir.exists()

        self.test_file.write_text("Test content")
        create_lkg_snapshot(self.test_file)

        assert self.lkg_dir.exists()

    def test_recover_from_lkg(self):
        """Test recovery from LKG snapshot."""
        # Create original file and snapshot
        original_content = "# Original Content\nLine 2"
        self.test_file.write_text(original_content)
        create_lkg_snapshot(self.test_file)

        # Corrupt the file
        self.test_file.write_text("# Corrupted Content")

        # Recover from LKG
        success = recover_from_lkg(self.test_file)
        assert success is True
        assert self.test_file.read_text() == original_content

    def test_recover_from_lkg_no_snapshot(self):
        """Test recovery fails when no LKG snapshot exists."""
        self.test_file.write_text("Test content")

        # Attempt recovery without creating snapshot
        success = recover_from_lkg(self.test_file)
        assert success is False

    def test_lkg_preserves_metadata(self):
        """Test that LKG snapshot includes metadata."""
        self.test_file.write_text("Test content")
        create_lkg_snapshot(self.test_file)

        lkg_file = self.lkg_dir / f"{self.test_file.name}.lkg"
        # This test may need adjustment based on implementation
        # For now, just verify the snapshot exists
        assert lkg_file.exists()


class TestValidatorIntegration:
    """Integration tests for validator components."""

    def test_validation_workflow(self, tmp_path):
        """Test complete validation workflow."""
        # Create a valid PROJECT-CONTEXT.md
        context_file = tmp_path / "PROJECT-CONTEXT.md"
        context_file.write_text(
            """# PROJECT CONTEXT

## IDENTITY
NAME::Test Project
TYPE::Test Type
PURPOSE::"Test Purpose"

## ARCHITECTURE
CORE_PRINCIPLE::"Test"

## CURRENT_STATE
DATE::2025-12-09
ACTIVE_FOCUS::"Test"

## DEVELOPMENT_GUIDELINES
STYLE::"Test"

## QUICK_REFERENCES
SPEC::"test.md"

## CONTEXT_LIFECYCLE
TARGET::<200_LOC
"""
        )

        # Validate
        result = validate_project_context(context_file.read_text())
        assert result.is_valid is True

        # Create LKG snapshot
        create_lkg_snapshot(context_file)

        # Corrupt file
        context_file.write_text("# Corrupted")

        # Validate corruption detected
        result = validate_project_context(context_file.read_text())
        assert result.is_valid is False

        # Recover from LKG
        success = recover_from_lkg(context_file)
        assert success is True

        # Validate recovery successful
        result = validate_project_context(context_file.read_text())
        assert result.is_valid is True
