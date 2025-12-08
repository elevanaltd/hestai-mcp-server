"""Tests for Context Steward OCTAVE utilities.

Tests OCTAVE response parsing from AI responses, handling conversational preamble
and robust parsing of nested OCTAVE structures.
"""

from tools.context_steward.octave_utils import (
    extract_octave_response,
    parse_context_steward_response,
)


class TestOCTAVEExtraction:
    """Test OCTAVE response extraction from LLM output."""

    def test_extract_octave_only(self):
        """Pure OCTAVE without preamble should be extracted."""
        octave = "RESPONSE::[STATUS::success]"
        result = extract_octave_response(octave)
        assert result == octave

    def test_extract_with_preamble(self):
        """OCTAVE with conversational preamble should be extracted."""
        raw = "Here's the analysis you requested:\n\n" 'RESPONSE::[STATUS::success, SUMMARY::"All done"]'
        result = extract_octave_response(raw)
        assert result == 'RESPONSE::[STATUS::success, SUMMARY::"All done"]'

    def test_extract_with_postamble(self):
        """OCTAVE with conversational postamble should be extracted."""
        raw = "RESPONSE::[STATUS::success]\n\n" "Let me know if you need anything else!"
        result = extract_octave_response(raw)
        assert result == "RESPONSE::[STATUS::success]"

    def test_extract_with_both(self):
        """OCTAVE with both preamble and postamble should be extracted."""
        raw = "Analysis complete.\n\n" "RESPONSE::[STATUS::success]\n\n" "Feel free to ask questions!"
        result = extract_octave_response(raw)
        assert result == "RESPONSE::[STATUS::success]"

    def test_extract_multiline_octave(self):
        """Multiline OCTAVE should be extracted correctly."""
        raw = """Analysis results:

RESPONSE::[
  STATUS::success,
  SUMMARY::"Everything looks good",
  CHANGES::[
    "Updated context",
    "Added documentation"
  ]
]

Done!"""
        result = extract_octave_response(raw)
        assert "RESPONSE::[" in result
        assert "STATUS::success" in result
        assert "SUMMARY::" in result

    def test_extract_no_octave(self):
        """Response without OCTAVE should return None."""
        raw = "Just a regular text response without OCTAVE"
        result = extract_octave_response(raw)
        assert result is None


class TestResponseParsing:
    """Test parsing of RESPONSE OCTAVE blocks."""

    def test_parse_minimal_response(self):
        """Minimal valid response should parse successfully."""
        octave = "RESPONSE::[STATUS::success]"
        result = parse_context_steward_response(octave)

        assert result["status"] == "success"
        assert result["summary"] is None
        assert result["files_analyzed"] == []
        assert result["changes"] == []
        assert result["artifacts"] == []

    def test_parse_complete_response(self):
        """Complete response with all fields should parse correctly."""
        octave = """RESPONSE::[
  STATUS::success,
  SUMMARY::"Updated PROJECT-CONTEXT with session learnings",
  FILES_ANALYZED::[
    ".hestai/context/PROJECT-CONTEXT.md",
    "src/feature.py"
  ],
  CHANGES::[
    "Added DECISIONS section with architecture choice",
    "Updated BLOCKERS with resolved issues",
    "Merged new learnings into existing wisdom"
  ],
  ARTIFACTS::[
    {type::context_update, path::".hestai/context/PROJECT-CONTEXT.md", action::merged},
    {type::session_note, path::".hestai/sessions/2024-01-15-feature.md", action::created}
  ]
]"""

        result = parse_context_steward_response(octave)

        assert result["status"] == "success"
        assert result["summary"] == "Updated PROJECT-CONTEXT with session learnings"

        # Check files_analyzed
        assert len(result["files_analyzed"]) == 2
        assert ".hestai/context/PROJECT-CONTEXT.md" in result["files_analyzed"]
        assert "src/feature.py" in result["files_analyzed"]

        # Check changes
        assert len(result["changes"]) == 3
        assert "Added DECISIONS section" in result["changes"][0]

        # Check artifacts
        assert len(result["artifacts"]) == 2
        assert result["artifacts"][0]["type"] == "context_update"
        assert result["artifacts"][0]["path"] == ".hestai/context/PROJECT-CONTEXT.md"
        assert result["artifacts"][0]["action"] == "merged"

    def test_parse_with_preamble(self):
        """Response with conversational preamble should parse correctly."""
        raw = """Here's the result of the analysis:

RESPONSE::[
  STATUS::success,
  SUMMARY::"All good"
]

Let me know if you need more details!"""

        result = parse_context_steward_response(raw)

        assert result["status"] == "success"
        assert result["summary"] == "All good"

    def test_parse_no_octave_returns_error(self):
        """Response without OCTAVE should return error status."""
        raw = "Just plain text without any OCTAVE"
        result = parse_context_steward_response(raw)

        assert result["status"] == "error"
        assert "No RESPONSE block found" in result["error"]
        assert "raw_response" in result
        assert result["raw_response"] == raw[:500]

    def test_parse_malformed_octave_returns_error(self):
        """Malformed OCTAVE should return error status."""
        raw = "RESPONSE::[STATUS::success"  # Missing closing bracket
        result = parse_context_steward_response(raw)

        assert result["status"] == "error"
        # Malformed structure is detected during extraction
        assert "no response block" in result["error"].lower() or "parse error" in result["error"].lower()
        assert "raw_response" in result

    def test_parse_partial_status(self):
        """Partial status should be handled correctly."""
        octave = """RESPONSE::[
  STATUS::partial,
  SUMMARY::"Updated context but couldn't write file",
  CHANGES::["Analysis complete"],
  ARTIFACTS::[]
]"""

        result = parse_context_steward_response(octave)

        assert result["status"] == "partial"
        assert "couldn't write file" in result["summary"]
        assert len(result["changes"]) == 1
        assert result["artifacts"] == []

    def test_parse_failure_status(self):
        """Failure status should be handled correctly."""
        octave = """RESPONSE::[
  STATUS::failure,
  SUMMARY::"Unable to access file system"
]"""

        result = parse_context_steward_response(octave)

        assert result["status"] == "failure"
        assert "Unable to access" in result["summary"]

    def test_parse_empty_collections(self):
        """Empty collections should parse as empty lists."""
        octave = """RESPONSE::[
  STATUS::success,
  FILES_ANALYZED::[],
  CHANGES::[],
  ARTIFACTS::[]
]"""

        result = parse_context_steward_response(octave)

        assert result["files_analyzed"] == []
        assert result["changes"] == []
        assert result["artifacts"] == []

    def test_parse_quoted_strings_with_special_chars(self):
        """Strings with special characters should parse correctly."""
        octave = """RESPONSE::[
  STATUS::success,
  SUMMARY::"Updated context: added decisions, blockers resolved",
  CHANGES::[
    "Added DECISIONS::[choice::X]",
    "Merged BLOCKERS::[issue⊗resolved]"
  ]
]"""

        result = parse_context_steward_response(octave)

        assert ":" in result["summary"]
        assert "," in result["summary"]
        assert "::" in result["changes"][0]
        assert "⊗" in result["changes"][1]

    def test_parse_nested_artifact_structure(self):
        """Nested artifact objects should parse correctly."""
        octave = """RESPONSE::[
  STATUS::success,
  ARTIFACTS::[
    {
      type::context_update,
      path::".hestai/context/PROJECT-CONTEXT.md",
      action::merged,
      lines::127
    },
    {type::session_note, path::".hestai/sessions/note.md", action::created}
  ]
]"""

        result = parse_context_steward_response(octave)

        assert len(result["artifacts"]) == 2
        assert result["artifacts"][0]["type"] == "context_update"
        assert result["artifacts"][0]["lines"] == "127"  # Parsed as string
        assert result["artifacts"][1]["action"] == "created"

    def test_parse_truncates_long_error_response(self):
        """Long error responses should be truncated to 500 chars."""
        raw = "x" * 1000  # No OCTAVE, just 1000 chars
        result = parse_context_steward_response(raw)

        assert result["status"] == "error"
        assert len(result["raw_response"]) == 500


class TestEndToEndScenarios:
    """End-to-end scenarios for realistic AI responses."""

    def test_llm_response_with_reasoning(self):
        """Simulate realistic LLM response with reasoning preamble."""
        raw = """I'll analyze the session and provide the results in OCTAVE format.

Based on my analysis, I found several key insights that should be documented.

RESPONSE::[
  STATUS::success,
  SUMMARY::"Session analyzed with 3 key findings merged into PROJECT-CONTEXT",
  FILES_ANALYZED::[
    ".hestai/context/PROJECT-CONTEXT.md",
    "tests/test_feature.py",
    "src/feature.py"
  ],
  CHANGES::[
    "Added architecture decision regarding database choice",
    "Updated performance requirements in CONSTRAINTS section",
    "Merged security constraints into existing REQUIREMENTS"
  ],
  ARTIFACTS::[
    {type::context_update, path::".hestai/context/PROJECT-CONTEXT.md", action::merged}
  ]
]

I hope this analysis is helpful! Let me know if you need any clarification."""

        result = parse_context_steward_response(raw)

        assert result["status"] == "success"
        assert "3 key findings" in result["summary"]
        assert len(result["files_analyzed"]) == 3
        assert len(result["changes"]) == 3
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["type"] == "context_update"

    def test_context_update_scenario(self):
        """Test context update task scenario."""
        raw = """RESPONSE::[
  STATUS::success,
  SUMMARY::"Merged session learnings into PROJECT-CONTEXT DECISIONS and BLOCKERS",
  FILES_ANALYZED::[".hestai/context/PROJECT-CONTEXT.md"],
  CHANGES::[
    "DECISIONS::[database::PostgreSQL→BECAUSE[team_expertise+scaling]]",
    "BLOCKERS::[auth_integration⊗resolved_via_oauth2]"
  ],
  ARTIFACTS::[
    {type::context_update, path::".hestai/context/PROJECT-CONTEXT.md", action::merged}
  ]
]"""

        result = parse_context_steward_response(raw)

        assert result["status"] == "success"
        assert "PROJECT-CONTEXT" in result["summary"]
        assert ".hestai/context/PROJECT-CONTEXT.md" in result["files_analyzed"]
        assert "DECISIONS::" in result["changes"][0]
        assert "BLOCKERS::" in result["changes"][1]

    def test_workflow_checklist_update_scenario(self):
        """Test workflow checklist update scenario."""
        raw = """RESPONSE::[
  STATUS::success,
  SUMMARY::"Updated workflow checklist with completed B2 tasks",
  FILES_ANALYZED::[".hestai/workflow/PROJECT-CHECKLIST.md"],
  CHANGES::[
    "Marked B2_01 complete: Feature implementation",
    "Marked B2_02 complete: Test coverage achieved",
    "Updated B2_03 status: In progress - code review pending"
  ],
  ARTIFACTS::[
    {type::workflow_update, path::".hestai/workflow/PROJECT-CHECKLIST.md", action::updated}
  ]
]"""

        result = parse_context_steward_response(raw)

        assert result["status"] == "success"
        assert "workflow checklist" in result["summary"].lower()
        assert len(result["changes"]) == 3
        assert "B2_01" in result["changes"][0]
        assert "B2_03" in result["changes"][2]
