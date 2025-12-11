import json

import pytest

from tools.clockout import ClockOutTool


class TestClockOutEdgeCases:
    """Critical validation for edge cases in content parsing"""

    @pytest.fixture
    def clockout_tool(self):
        return ClockOutTool()

    def test_malformed_list_contents(self, clockout_tool, tmp_path):
        """Test parsing robustly handles malformed list items"""
        jsonl_path = tmp_path / "malformed.jsonl"
        jsonl_content = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        None,  # NoneType
                        "just a string",  # String in list (not dict)
                        {"type": "image"},  # Non-text dict
                        {"text": "valid"},  # Missing type
                        {"type": "text", "text": "OK"},  # Valid
                    ],
                },
            }
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        # Should not raise AttributeError or TypeError
        messages, model_history = clockout_tool._parse_session_transcript(jsonl_path)

        assert len(messages) == 1
        # Only the valid "OK" should be extracted.
        # "valid" (missing type) is skipped because code checks type=="text"
        assert messages[0]["content"] == "OK"

    def test_invalid_content_types(self, clockout_tool, tmp_path):
        """Test parsing handles non-string/non-list content types safely"""
        jsonl_path = tmp_path / "invalid_types.jsonl"
        jsonl_content = [
            {"type": "user", "message": {"role": "user", "content": 12345}},  # Integer
            {"type": "assistant", "message": {"role": "assistant", "content": None}},  # None
            {"type": "user", "message": {"role": "user", "content": {"complex": "object"}}},  # Dict (not list or str)
        ]

        with open(jsonl_path, "w") as f:
            for entry in jsonl_content:
                f.write(json.dumps(entry) + "\n")

        messages, model_history = clockout_tool._parse_session_transcript(jsonl_path)

        # Should result in empty content -> filtered out if text check passes?
        # The code:
        # else: text = ""
        # if text: messages.append(...)

        # So these should NOT produce messages
        assert len(messages) == 0
