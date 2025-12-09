"""
Tests for ClockIn tool State Vector integration.

Part of Context Steward v2 Shell layer - Phase 1 clock_in enhancements.
"""

import json

import pytest

from tools.clockin import ClockInTool


class TestClockInStateVectorIntegration:
    """Test clock_in integration with State Vector and Context Negatives."""

    @pytest.mark.asyncio
    async def test_clockin_includes_state_vector_if_exists(self, tmp_path):
        """Test clock_in includes state vector content when file exists."""
        # Setup
        tool = ClockInTool()

        # Create state vector file
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Valid state vector with all required fields (OCTAVE dict syntax)
        state_vector_content = """STATE_VECTOR::[
  IDENTITY::{project_name:"test",type:"service",purpose:"testing"},
  AUTHORITY::{current_owner:"implementation-lead",phase:"B2",blocking_items:[]},
  QUALITY::{branch:"main",lint_status:"pass",typecheck_status:"pass",test_status:"pass"},
  FOCUS::{top_3_active_items:["item1","item2","item3"]},
  SIGNALS::{latest_commit:"abc123",dependent_projects:[]}
]"""
        state_vector_path = context_dir / "current_state.oct"
        state_vector_path.write_text(state_vector_content)

        # Execute
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        assert "state_vector" in content
        # Content should be included directly if < 1KB
        assert content["state_vector"] == state_vector_content

    @pytest.mark.asyncio
    async def test_clockin_includes_state_vector_path_if_large(self, tmp_path):
        """Test clock_in includes path instead of content if state vector > 1KB."""
        # Setup
        tool = ClockInTool()

        # Create large state vector file
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Create content > 1KB with valid structure
        large_content = (
            """STATE_VECTOR::[
  IDENTITY::{project_name:"test",type:"service",purpose:"testing"},
  AUTHORITY::{current_owner:"implementation-lead",phase:"B2",blocking_items:[]},
  QUALITY::{branch:"main",lint_status:"pass",typecheck_status:"pass",test_status:"pass"},
  FOCUS::{top_3_active_items:["item1","item2","item3"]},
  SIGNALS::{latest_commit:"abc123",dependent_projects:[]},
  EXTRA_DATA:"""
            + '"'
            + ("x" * 1000)
            + '"\n]'
        )
        state_vector_path = context_dir / "current_state.oct"
        state_vector_path.write_text(large_content)

        # Execute
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        assert "state_vector" in content
        # Should include path instead of content
        assert "current_state.oct" in content["state_vector"]

    @pytest.mark.asyncio
    async def test_clockin_includes_context_negatives_if_exists(self, tmp_path):
        """Test clock_in includes context negatives when file exists."""
        # Setup
        tool = ClockInTool()

        # Create context negatives file
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        # Valid context negatives with minimum 10 anti-patterns (need ANTI_PATTERN_N keys)
        negatives_content = """CONTEXT_NEGATIVES::[
  ANTI_PATTERN_1::{pattern:"skip_tests",description:"Skipping tests",instead:"Write tests",severity:"high"},
  ANTI_PATTERN_2::{pattern:"use_deprecated_api",description:"Using deprecated API",instead:"Use new API",severity:"medium"},
  ANTI_PATTERN_3::{pattern:"manual_db_migrations",description:"Manual DB migrations",instead:"Use migration tool",severity:"high"},
  ANTI_PATTERN_4::{pattern:"hardcoded_secrets",description:"Hardcoded secrets",instead:"Use env vars",severity:"critical"},
  ANTI_PATTERN_5::{pattern:"no_error_handling",description:"Missing error handling",instead:"Add try/catch",severity:"high"},
  ANTI_PATTERN_6::{pattern:"global_state",description:"Using global state",instead:"Pass dependencies",severity:"medium"},
  ANTI_PATTERN_7::{pattern:"long_functions",description:"Functions > 50 lines",instead:"Extract functions",severity:"low"},
  ANTI_PATTERN_8::{pattern:"no_types",description:"Missing type hints",instead:"Add types",severity:"medium"},
  ANTI_PATTERN_9::{pattern:"no_docs",description:"Missing documentation",instead:"Add docstrings",severity:"low"},
  ANTI_PATTERN_10::{pattern:"magic_numbers",description:"Magic numbers",instead:"Use constants",severity:"low"}
]"""
        negatives_path = context_dir / "CONTEXT-NEGATIVES.oct"
        negatives_path.write_text(negatives_content)

        # Execute
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        assert "context_negatives" in content
        # Could be content or path depending on size
        if len(negatives_content) < 1024:
            assert content["context_negatives"] == negatives_content
        else:
            assert "CONTEXT-NEGATIVES.oct" in content["context_negatives"]

    @pytest.mark.asyncio
    async def test_clockin_validates_state_vector_before_including(self, tmp_path):
        """Test clock_in validates state vector before including in response."""
        # Setup
        tool = ClockInTool()

        # Create INVALID state vector (missing required fields)
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        invalid_content = """STATE_VECTOR::[
  INVALID::missing_phase
]"""
        state_vector_path = context_dir / "current_state.oct"
        state_vector_path.write_text(invalid_content)

        # Execute
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        # Should NOT include invalid state vector
        # Or should include validation_error field
        if "state_vector" in content:
            # If included, should have validation warning
            assert "validation_error" in content or "validation_warning" in content

    @pytest.mark.asyncio
    async def test_clockin_validates_context_negatives_before_including(self, tmp_path):
        """Test clock_in validates context negatives before including."""
        # Setup
        tool = ClockInTool()

        # Create INVALID context negatives (wrong structure)
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        invalid_content = """CONTEXT_NEGATIVES::[
  WRONG_FIELD::[something]
]"""
        negatives_path = context_dir / "CONTEXT-NEGATIVES.oct"
        negatives_path.write_text(invalid_content)

        # Execute
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        # Should NOT include invalid context negatives
        # Or should include validation warning
        if "context_negatives" in content:
            assert "validation_error" in content or "validation_warning" in content

    @pytest.mark.asyncio
    async def test_clockin_works_without_state_vector(self, tmp_path):
        """Test clock_in works normally when state vector doesn't exist."""
        # Setup
        tool = ClockInTool()

        # Execute (no state vector file created)
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        assert output["status"] == "success"
        assert "session_id" in content
        # State vector should not be included
        assert "state_vector" not in content or content.get("state_vector") is None

    @pytest.mark.asyncio
    async def test_clockin_includes_both_state_vector_and_negatives(self, tmp_path):
        """Test clock_in includes both state vector and context negatives."""
        # Setup
        tool = ClockInTool()

        # Create both files
        context_dir = tmp_path / ".hestai" / "context"
        context_dir.mkdir(parents=True)

        state_vector_content = """STATE_VECTOR::[
  IDENTITY::{project_name:"test",type:"service",purpose:"testing"},
  AUTHORITY::{current_owner:"implementation-lead",phase:"B2",blocking_items:[]},
  QUALITY::{branch:"main",lint_status:"pass",typecheck_status:"pass",test_status:"pass"},
  FOCUS::{top_3_active_items:["feature"]},
  SIGNALS::{latest_commit:"abc123",dependent_projects:[]}
]"""
        (context_dir / "current_state.oct").write_text(state_vector_content)

        negatives_content = """CONTEXT_NEGATIVES::[
  ANTI_PATTERN_1::{pattern:"skip_tests",description:"Skipping tests",instead:"Write tests",severity:"high"},
  ANTI_PATTERN_2::{pattern:"use_deprecated_api",description:"Using deprecated API",instead:"Use new API",severity:"medium"},
  ANTI_PATTERN_3::{pattern:"manual_db_migrations",description:"Manual DB migrations",instead:"Use migration tool",severity:"high"},
  ANTI_PATTERN_4::{pattern:"hardcoded_secrets",description:"Hardcoded secrets",instead:"Use env vars",severity:"critical"},
  ANTI_PATTERN_5::{pattern:"no_error_handling",description:"Missing error handling",instead:"Add try/catch",severity:"high"},
  ANTI_PATTERN_6::{pattern:"global_state",description:"Using global state",instead:"Pass dependencies",severity:"medium"},
  ANTI_PATTERN_7::{pattern:"long_functions",description:"Functions > 50 lines",instead:"Extract functions",severity:"low"},
  ANTI_PATTERN_8::{pattern:"no_types",description:"Missing type hints",instead:"Add types",severity:"medium"},
  ANTI_PATTERN_9::{pattern:"no_docs",description:"Missing documentation",instead:"Add docstrings",severity:"low"},
  ANTI_PATTERN_10::{pattern:"magic_numbers",description:"Magic numbers",instead:"Use constants",severity:"low"}
]"""
        (context_dir / "CONTEXT-NEGATIVES.oct").write_text(negatives_content)

        # Execute
        result = await tool.execute({"role": "implementation-lead", "working_dir": str(tmp_path)})

        # Verify
        output = json.loads(result[0].text)
        content = json.loads(output["content"])

        assert "state_vector" in content
        assert "context_negatives" in content
        assert content["state_vector"] == state_vector_content
        # Context negatives could be content or path depending on size
        if len(negatives_content) < 1024:
            assert content["context_negatives"] == negatives_content
        else:
            assert "CONTEXT-NEGATIVES.oct" in content["context_negatives"]
