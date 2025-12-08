"""Tests for Context Steward XML utilities.

Tests CDATA escaping, XML extraction, and robust parsing of LLM responses
with conversational preamble.
"""

from tools.context_steward.xml_utils import (
    escape_cdata_content,
    extract_xml_response,
    parse_context_steward_response,
    wrap_cdata,
)


class TestCDATAEscaping:
    """Test CDATA content escaping."""

    def test_escape_simple_content(self):
        """Simple content without special sequences should remain unchanged."""
        content = "Hello world"
        result = escape_cdata_content(content)
        assert result == "Hello world"

    def test_escape_cdata_terminator(self):
        """Content with ]]> should be escaped."""
        content = "Some text ]]> more text"
        result = escape_cdata_content(content)
        assert result == "Some text ]]]]><![CDATA[> more text"

    def test_escape_multiple_terminators(self):
        """Multiple ]]> sequences should all be escaped."""
        content = "First ]]> second ]]> third"
        result = escape_cdata_content(content)
        assert result == "First ]]]]><![CDATA[> second ]]]]><![CDATA[> third"

    def test_wrap_cdata_simple(self):
        """Simple content should be wrapped in CDATA."""
        content = "hello world"
        result = wrap_cdata(content)
        assert result == "<![CDATA[hello world]]>"

    def test_wrap_cdata_with_terminator(self):
        """Content with ]]> should be escaped before wrapping."""
        content = "text with ]]> sequence"
        result = wrap_cdata(content)
        assert result == "<![CDATA[text with ]]]]><![CDATA[> sequence]]>"

    def test_wrap_empty_content(self):
        """Empty content should produce empty CDATA."""
        result = wrap_cdata("")
        assert result == "<![CDATA[]]>"


class TestXMLExtraction:
    """Test XML response extraction from LLM output."""

    def test_extract_xml_only(self):
        """Pure XML without preamble should be extracted."""
        xml = "<context-steward-response><status>success</status></context-steward-response>"
        result = extract_xml_response(xml)
        assert result == xml

    def test_extract_with_preamble(self):
        """XML with conversational preamble should be extracted."""
        raw = (
            "Here's the analysis you requested:\n\n"
            "<context-steward-response><status>success</status></context-steward-response>"
        )
        result = extract_xml_response(raw)
        assert result == "<context-steward-response><status>success</status></context-steward-response>"

    def test_extract_with_postamble(self):
        """XML with conversational postamble should be extracted."""
        raw = (
            "<context-steward-response><status>success</status></context-steward-response>\n\n"
            "Let me know if you need anything else!"
        )
        result = extract_xml_response(raw)
        assert result == "<context-steward-response><status>success</status></context-steward-response>"

    def test_extract_with_both(self):
        """XML with both preamble and postamble should be extracted."""
        raw = (
            "Analysis complete.\n\n"
            "<context-steward-response><status>success</status></context-steward-response>\n\n"
            "Feel free to ask questions!"
        )
        result = extract_xml_response(raw)
        assert result == "<context-steward-response><status>success</status></context-steward-response>"

    def test_extract_multiline_xml(self):
        """Multiline XML should be extracted correctly."""
        raw = """Analysis results:

<context-steward-response>
  <status>success</status>
  <summary>Everything looks good</summary>
</context-steward-response>

Done!"""
        result = extract_xml_response(raw)
        assert "<context-steward-response>" in result
        assert "<status>success</status>" in result
        assert "<summary>Everything looks good</summary>" in result

    def test_extract_no_xml(self):
        """Response without XML should return None."""
        raw = "Just a regular text response without XML"
        result = extract_xml_response(raw)
        assert result is None


class TestResponseParsing:
    """Test parsing of context-steward-response XML."""

    def test_parse_minimal_response(self):
        """Minimal valid response should parse successfully."""
        xml = "<context-steward-response><status>success</status></context-steward-response>"
        result = parse_context_steward_response(xml)

        assert result["status"] == "success"
        assert result["task_id"] is None
        assert result["summary"] is None
        assert result["artifacts"] == []
        assert result["risks"] == []
        assert result["next_actions"] == []

    def test_parse_complete_response(self):
        """Complete response with all fields should parse correctly."""
        xml = """<context-steward-response>
  <status>success</status>
  <task-id>TASK-123</task-id>
  <summary>Analysis complete</summary>
  <artifacts>
    <artifact type="transcript" label="Session Transcript">
      <![CDATA[Example transcript content]]>
    </artifact>
    <artifact type="analysis" label="Findings">
      <![CDATA[Key findings here]]>
    </artifact>
  </artifacts>
  <risks>
    <risk severity="medium">Potential data loss</risk>
    <risk severity="low">Performance impact</risk>
  </risks>
  <next-actions>
    <action owner="developer">Review findings</action>
    <action owner="qa">Validate changes</action>
  </next-actions>
</context-steward-response>"""

        result = parse_context_steward_response(xml)

        assert result["status"] == "success"
        assert result["task_id"] == "TASK-123"
        assert result["summary"] == "Analysis complete"

        # Check artifacts
        assert len(result["artifacts"]) == 2
        assert result["artifacts"][0]["type"] == "transcript"
        assert result["artifacts"][0]["label"] == "Session Transcript"
        assert "Example transcript content" in result["artifacts"][0]["content"]

        # Check risks
        assert len(result["risks"]) == 2
        assert result["risks"][0]["severity"] == "medium"
        assert result["risks"][0]["description"] == "Potential data loss"

        # Check actions
        assert len(result["next_actions"]) == 2
        assert result["next_actions"][0]["owner"] == "developer"
        assert result["next_actions"][0]["description"] == "Review findings"

    def test_parse_with_preamble(self):
        """Response with conversational preamble should parse correctly."""
        raw = """Here's the result of the analysis:

<context-steward-response>
  <status>success</status>
  <summary>All good</summary>
</context-steward-response>

Let me know if you need more details!"""

        result = parse_context_steward_response(raw)

        assert result["status"] == "success"
        assert result["summary"] == "All good"

    def test_parse_no_xml_returns_error(self):
        """Response without XML should return error status."""
        raw = "Just plain text without any XML"
        result = parse_context_steward_response(raw)

        assert result["status"] == "error"
        assert "No context-steward-response XML found" in result["error"]
        assert "raw_response" in result
        assert result["raw_response"] == raw[:500]

    def test_parse_malformed_xml_returns_error(self):
        """Malformed XML should return error status."""
        raw = "<context-steward-response><status>success</context-steward-response>"
        result = parse_context_steward_response(raw)

        assert result["status"] == "error"
        assert "XML parse error" in result["error"]
        assert "raw_response" in result

    def test_parse_flexible_field_order(self):
        """Fields in different order should parse correctly."""
        xml = """<context-steward-response>
  <summary>Summary first</summary>
  <task-id>TASK-456</task-id>
  <status>pending</status>
</context-steward-response>"""

        result = parse_context_steward_response(xml)

        assert result["status"] == "pending"
        assert result["task_id"] == "TASK-456"
        assert result["summary"] == "Summary first"

    def test_parse_empty_collections(self):
        """Empty collections should parse as empty lists."""
        xml = """<context-steward-response>
  <status>success</status>
  <artifacts></artifacts>
  <risks></risks>
  <next-actions></next-actions>
</context-steward-response>"""

        result = parse_context_steward_response(xml)

        assert result["artifacts"] == []
        assert result["risks"] == []
        assert result["next_actions"] == []

    def test_parse_artifact_with_cdata_injection(self):
        """Artifact containing ]]> should be handled correctly."""
        xml = """<context-steward-response>
  <status>success</status>
  <artifacts>
    <artifact type="transcript" label="Test">
      <![CDATA[Content with ]]]]><![CDATA[> escaped sequence]]>
    </artifact>
  </artifacts>
</context-steward-response>"""

        result = parse_context_steward_response(xml)

        assert len(result["artifacts"]) == 1
        # The content should contain the original ]]> after escaping
        assert "]]>" in result["artifacts"][0]["content"]

    def test_parse_truncates_long_error_response(self):
        """Long error responses should be truncated to 500 chars."""
        raw = "x" * 1000  # No XML, just 1000 chars
        result = parse_context_steward_response(raw)

        assert result["status"] == "error"
        assert len(result["raw_response"]) == 500


class TestEndToEndScenarios:
    """End-to-end scenarios combining multiple utilities."""

    def test_create_and_parse_transcript_artifact(self):
        """Create CDATA-wrapped transcript and parse it."""
        transcript_content = "User: What is ]]> this?\nAI: That's a CDATA terminator."
        wrapped = wrap_cdata(transcript_content)

        xml = f"""<context-steward-response>
  <status>success</status>
  <artifacts>
    <artifact type="transcript" label="Chat">{wrapped}</artifact>
  </artifacts>
</context-steward-response>"""

        result = parse_context_steward_response(xml)

        assert result["status"] == "success"
        assert len(result["artifacts"]) == 1
        # The ]]> should be present in the parsed content
        assert "]]>" in result["artifacts"][0]["content"]

    def test_llm_response_with_reasoning(self):
        """Simulate realistic LLM response with reasoning preamble."""
        raw = """I'll analyze the session and provide the results in the requested format.

Based on my analysis, I found several key insights that should be documented.

<context-steward-response>
  <status>success</status>
  <task-id>SESSION-2024-001</task-id>
  <summary>Session analyzed successfully with 3 key findings</summary>
  <artifacts>
    <artifact type="analysis" label="Key Findings">
      <![CDATA[
1. Architecture decision made regarding database choice
2. Performance requirements clarified
3. Security constraints identified
      ]]>
    </artifact>
  </artifacts>
  <risks>
    <risk severity="high">Database migration complexity underestimated</risk>
  </risks>
  <next-actions>
    <action owner="architect">Create database migration plan</action>
    <action owner="security">Review security requirements</action>
  </next-actions>
</context-steward-response>

I hope this analysis is helpful! Let me know if you need any clarification."""

        result = parse_context_steward_response(raw)

        assert result["status"] == "success"
        assert result["task_id"] == "SESSION-2024-001"
        assert "3 key findings" in result["summary"]
        assert len(result["artifacts"]) == 1
        assert len(result["risks"]) == 1
        assert len(result["next_actions"]) == 2
        assert result["risks"][0]["severity"] == "high"
