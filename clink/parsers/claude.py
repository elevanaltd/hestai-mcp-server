"""Parser for Claude CLI JSON output."""

from __future__ import annotations

import json
from typing import Any

from .base import BaseParser, ParsedCLIResponse, ParserError


class ClaudeJSONParser(BaseParser):
    """Parse stdout produced by `claude --output-format json`."""

    name = "claude_json"

    def parse(self, stdout: str, stderr: str) -> ParsedCLIResponse:
        if not stdout.strip():
            raise ParserError("Claude CLI returned empty stdout while JSON output was expected")

        try:
            loaded = json.loads(stdout)
        except json.JSONDecodeError:
            # Fallback: Try parsing as NDJSON (stream-json output)
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            if not lines:
                raise ParserError("Failed to decode Claude CLI output as JSON or NDJSON") from None

            try:
                events = [json.loads(line) for line in lines]
                loaded = self._aggregate_ndjson(events)
            except json.JSONDecodeError as exc:
                raise ParserError(f"Failed to decode Claude CLI JSON output: {exc}") from exc

        events: list[dict[str, Any]] | None = None
        assistant_entry: dict[str, Any] | None = None

        if isinstance(loaded, dict):
            payload: dict[str, Any] = loaded
        elif isinstance(loaded, list):
            events = [item for item in loaded if isinstance(item, dict)]
            result_entry = next(
                (item for item in events if item.get("type") == "result" or "result" in item),
                None,
            )
            assistant_entry = next(
                (item for item in reversed(events) if item.get("type") == "assistant"),
                None,
            )
            payload = result_entry or assistant_entry or (events[-1] if events else {})
            if not payload:
                raise ParserError("Claude CLI JSON array did not contain any parsable objects")
        else:
            raise ParserError("Claude CLI returned unexpected JSON payload")

        metadata = self._build_metadata(payload, stderr)
        if events is not None:
            metadata["raw_events"] = events
            metadata["raw"] = loaded

        result = payload.get("result")
        content: str = ""
        if isinstance(result, str):
            content = result.strip()
        elif isinstance(result, list):
            # Some CLI flows may emit a list of strings; join them conservatively.
            joined = [part.strip() for part in result if isinstance(part, str) and part.strip()]
            content = "\n".join(joined)

        if content:
            return ParsedCLIResponse(content=content, metadata=metadata)

        message = self._extract_message(payload)
        if message is None and assistant_entry and assistant_entry is not payload:
            message = self._extract_message(assistant_entry)
        if message:
            return ParsedCLIResponse(content=message, metadata=metadata)

        stderr_text = stderr.strip()
        if stderr_text:
            metadata.setdefault("stderr", stderr_text)
            return ParsedCLIResponse(
                content="Claude CLI returned no textual result. Raw stderr was preserved for troubleshooting.",
                metadata=metadata,
            )

        raise ParserError("Claude CLI response did not contain a textual result")

    def _aggregate_ndjson(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate a stream of JSON events into a single result-like object."""
        # Find the final result or valid message stop
        final_event = next((e for e in reversed(events) if e.get("type") == "message_stop"), None)

        # Accumulate text content from deltas
        text_parts = []
        for event in events:
            # Handle text deltas
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text_parts.append(delta.get("text", ""))

            # Handle legacy/alternative event structures if necessary
            # (Claude CLI structure for stream-json needs to be robustly handled)

        # If no deltas found, check for 'message_start' -> 'message' -> 'content'
        if not text_parts:
            # Try to find any content blocks in message_start
            start = next((e for e in events if e.get("type") == "message_start"), None)
            if start and "message" in start:
                content = start["message"].get("content", [])
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

        full_content = "".join(text_parts)

        # Construct a synthetic payload that mimics the non-streaming output
        payload = final_event or (events[-1] if events else {})
        # Ensure we have a structure that the rest of the parser recognizes
        if "type" not in payload:
            payload["type"] = "aggregated_stream"

        # Inject the accumulated content as 'result' or inside 'message'
        # The existing parser looks for payload["result"] or payload["message"]
        # We'll inject it into a 'message' field which _extract_message looks for
        payload["message"] = full_content

        # Preserve all events for debugging
        payload["_raw_stream_events"] = events

        return payload

    def _build_metadata(self, payload: dict[str, Any], stderr: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "raw": payload,
            "is_error": bool(payload.get("is_error")),
        }

        type_field = payload.get("type")
        if isinstance(type_field, str):
            metadata["type"] = type_field
        subtype_field = payload.get("subtype")
        if isinstance(subtype_field, str):
            metadata["subtype"] = subtype_field

        duration_ms = payload.get("duration_ms")
        if isinstance(duration_ms, (int, float)):
            metadata["duration_ms"] = duration_ms
        api_duration = payload.get("duration_api_ms")
        if isinstance(api_duration, (int, float)):
            metadata["duration_api_ms"] = api_duration

        usage = payload.get("usage")
        if isinstance(usage, dict):
            metadata["usage"] = usage

        model_usage = payload.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage:
            metadata["model_usage"] = model_usage
            first_model = next(iter(model_usage.keys()))
            metadata["model_used"] = first_model

        permission_denials = payload.get("permission_denials")
        if isinstance(permission_denials, list) and permission_denials:
            metadata["permission_denials"] = permission_denials

        session_id = payload.get("session_id")
        if isinstance(session_id, str) and session_id:
            metadata["session_id"] = session_id
        uuid_field = payload.get("uuid")
        if isinstance(uuid_field, str) and uuid_field:
            metadata["uuid"] = uuid_field

        stderr_text = stderr.strip()
        if stderr_text:
            metadata.setdefault("stderr", stderr_text)

        return metadata

    def _extract_message(self, payload: dict[str, Any]) -> str | None:
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

        error_field = payload.get("error")
        if isinstance(error_field, dict):
            error_message = error_field.get("message")
            if isinstance(error_message, str) and error_message.strip():
                return error_message.strip()

        return None
