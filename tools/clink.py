"""clink tool - bridge Zen MCP requests to external AI CLIs."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from clink import get_registry
from clink.agents import AgentOutput, CLIAgentError, create_agent
from clink.models import ResolvedCLIClient, ResolvedCLIRole
from config import TEMPERATURE_BALANCED
from tools.models import ToolModelCategory, ToolOutput
from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS
from tools.simple.base import SchemaBuilder, SimpleTool

logger = logging.getLogger(__name__)

MAX_RESPONSE_CHARS = 20_000
SUMMARY_PATTERN = re.compile(r"<SUMMARY>(.*?)</SUMMARY>", re.IGNORECASE | re.DOTALL)


class CLinkRequest(BaseModel):
    """Request model for clink tool."""

    prompt: str = Field(..., description="Prompt forwarded to the target CLI.")
    cli_name: str | None = Field(
        default=None,
        description="Configured CLI client name to invoke. Defaults to the first configured CLI if omitted.",
    )
    role: str | None = Field(
        default=None,
        description="Optional role preset defined in the CLI configuration (defaults to 'default').",
    )
    files: list[str] = Field(
        default_factory=list,
        description=COMMON_FIELD_DESCRIPTIONS["files"],
    )
    images: list[str] = Field(
        default_factory=list,
        description=COMMON_FIELD_DESCRIPTIONS["images"],
    )
    continuation_id: str | None = Field(
        default=None,
        description=COMMON_FIELD_DESCRIPTIONS["continuation_id"],
    )


class CLinkTool(SimpleTool):
    """Bridge MCP requests to configured CLI agents.

    Schema metadata is cached at construction time and execution relies on the shared
    SimpleTool hooks for conversation memory. Prompt preparation is customised so we
    pass instructions and file references suitable for another CLI agent.
    """

    def __init__(self) -> None:
        # Cache registry metadata so the schema surfaces concrete enum values.
        self._registry = get_registry()
        self._cli_names = self._registry.list_clients()
        self._role_map: dict[str, list[str]] = {name: self._registry.list_roles(name) for name in self._cli_names}
        self._all_roles: list[str] = sorted({role for roles in self._role_map.values() for role in roles})
        if "gemini" in self._cli_names:
            self._default_cli_name = "gemini"
        else:
            self._default_cli_name = self._cli_names[0] if self._cli_names else None
        self._active_system_prompt: str = ""
        super().__init__()

    def get_name(self) -> str:
        return "clink"

    def get_description(self) -> str:
        return (
            "Link a request to an external AI CLI (Gemini CLI, Qwen CLI, etc.) through Zen MCP to reuse "
            "their capabilities inside existing workflows."
        )

    def get_annotations(self) -> dict[str, Any]:
        return {"readOnlyHint": True}

    def requires_model(self) -> bool:
        return False

    def get_model_category(self) -> ToolModelCategory:
        return ToolModelCategory.BALANCED

    def get_default_temperature(self) -> float:
        return TEMPERATURE_BALANCED

    def get_system_prompt(self) -> str:
        return self._active_system_prompt or ""

    def get_request_model(self):
        return CLinkRequest

    def get_input_schema(self) -> dict[str, Any]:
        # Surface configured CLI names and roles directly in the schema so MCP clients
        # (and downstream agents) can discover available options without consulting
        # a separate registry call.
        role_descriptions = []
        for name in self._cli_names:
            roles = ", ".join(sorted(self._role_map.get(name, ["default"]))) or "default"
            role_descriptions.append(f"{name}: {roles}")

        if role_descriptions:
            cli_available = ", ".join(self._cli_names) if self._cli_names else "(none configured)"
            default_text = (
                f" Default: {self._default_cli_name}." if self._default_cli_name and len(self._cli_names) <= 1 else ""
            )
            cli_description = (
                "Configured CLI client name (from conf/cli_clients). Available: " + cli_available + default_text
            )
            role_description = (
                "Optional role preset defined for the selected CLI (defaults to 'default'). Roles per CLI: "
                + "; ".join(role_descriptions)
            )
        else:
            cli_description = "Configured CLI client name (from conf/cli_clients)."
            role_description = "Optional role preset defined for the selected CLI (defaults to 'default')."

        properties = {
            "prompt": {
                "type": "string",
                "description": "User request forwarded to the CLI (conversation context is pre-applied).",
            },
            "cli_name": {
                "type": "string",
                "enum": self._cli_names,
                "description": cli_description,
            },
            "role": {
                "type": "string",
                "enum": self._all_roles or ["default"],
                "description": role_description,
            },
            "files": SchemaBuilder.SIMPLE_FIELD_SCHEMAS["files"],
            "images": SchemaBuilder.COMMON_FIELD_SCHEMAS["images"],
            "continuation_id": SchemaBuilder.COMMON_FIELD_SCHEMAS["continuation_id"],
        }

        schema = {
            "type": "object",
            "properties": properties,
            "required": ["prompt"],
            "additionalProperties": False,
        }

        if len(self._cli_names) > 1:
            schema["required"].append("cli_name")

        return schema

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Unused by clink because we override the schema end-to-end."""
        return {}

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        self._current_arguments = arguments
        request = self.get_request_model()(**arguments)

        path_error = self._validate_file_paths(request)
        if path_error:
            return [self._error_response(path_error)]

        selected_cli = request.cli_name or self._default_cli_name
        if not selected_cli:
            return [self._error_response("No CLI clients are configured for clink.")]

        try:
            client_config = self._registry.get_client(selected_cli)
        except KeyError as exc:
            return [self._error_response(str(exc))]

        try:
            role_config = client_config.get_role(request.role)
        except KeyError as exc:
            return [self._error_response(str(exc))]

        files = self.get_request_files(request)
        images = self.get_request_images(request)
        continuation_id = self.get_request_continuation_id(request)

        self._model_context = arguments.get("_model_context")

        # Store client name for prompt preparation
        self._current_client_name = client_config.name

        # For Claude CLI, extract system prompt before prepare_prompt clears it
        # This must be done BEFORE calling _prepare_prompt_for_role because that
        # method clears _active_system_prompt in its finally block
        system_prompt = None
        if client_config.name.lower() == "claude":
            system_prompt = role_config.prompt_path.read_text(encoding="utf-8")

        try:
            prompt_text = await self._prepare_prompt_for_role(request, role_config)
        except Exception as exc:
            logger.exception("Failed to prepare clink prompt")
            return [self._error_response(f"Failed to prepare prompt: {exc}")]

        agent = create_agent(client_config)

        try:
            # Claude agent accepts system_prompt parameter, others ignore it
            result = await agent.run(
                role=role_config, prompt=prompt_text, files=files, images=images, system_prompt=system_prompt
            )
        except CLIAgentError as exc:
            metadata = self._build_error_metadata(client_config, exc)

            # Enhanced error message for workspace directory issues
            error_message = str(exc)
            if "workspace directories" in error_message or "FatalToolExecutionError" in error_message:
                error_message += (
                    "\n\n💡 TIP: To add another directory to this role's workspace, "
                    f"update conf/cli_clients/{client_config.name}.json with:\n"
                    f'  "role_args": ["--include-directories", "/path/to/directory"]'
                )

            error_output = ToolOutput(
                status="error",
                content=f"CLI '{client_config.name}' execution failed: {error_message}",
                content_type="text",
                metadata=metadata,
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]

        metadata = self._build_success_metadata(client_config, role_config, result)
        metadata = self._prune_metadata(metadata, client_config, reason="normal")

        content, metadata = self._apply_output_limit(
            client_config,
            result.parsed.content,
            metadata,
        )

        model_info = {
            "provider": client_config.name,
            "model_name": result.parsed.metadata.get("model_used"),
        }

        if continuation_id:
            try:
                self._record_assistant_turn(continuation_id, content, request, model_info)
            except Exception:
                logger.debug("Failed to record assistant turn for continuation %s", continuation_id, exc_info=True)

        continuation_offer = self._create_continuation_offer(request, model_info)
        if continuation_offer:
            tool_output = self._create_continuation_offer_response(
                content,
                continuation_offer,
                request,
                model_info,
            )
            tool_output.metadata = self._merge_metadata(tool_output.metadata, metadata)
        else:
            tool_output = ToolOutput(
                status="success",
                content=content,
                content_type="text",
                metadata=metadata,
            )

        return [TextContent(type="text", text=tool_output.model_dump_json())]

    async def prepare_prompt(self, request) -> str:
        client_config = self._registry.get_client(request.cli_name)
        role_config = client_config.get_role(request.role)
        return await self._prepare_prompt_for_role(request, role_config)

    async def _prepare_prompt_for_role(self, request: CLinkRequest, role: ResolvedCLIRole) -> str:
        """Load the role prompt and assemble the final user message.

        For Claude CLI, the system prompt is extracted separately and passed via
        --append-system-prompt. For other CLIs, it's embedded in the user prompt.

        FIRST_TURN detection: If no continuation_id, inject explicit activation
        instructions to trigger RAPH constitutional activation. Can be disabled
        with [no-raph] flag in the user prompt.
        """
        self._active_system_prompt = role.prompt_path.read_text(encoding="utf-8")
        try:
            user_content = self.handle_prompt_file_with_fallback(request).strip()

            # FIRST_TURN detection for constitutional activation
            continuation_id = self.get_request_continuation_id(request)
            is_first_turn = not continuation_id

            # Check for [no-raph] flag to skip activation
            skip_activation = is_first_turn and "[no-raph]" in user_content.lower()

            # Determine client name for prompt customization
            client_name = getattr(self, "_current_client_name", "").lower()

            guidance = self._agent_capabilities_guidance(client_name)
            file_section = self._format_file_references(self.get_request_files(request))

            sections: list[str] = []
            active_prompt = self.get_system_prompt().strip()

            # For Claude CLI, system prompt is passed separately via --append-system-prompt
            # For other CLIs, embed it in the user prompt
            if active_prompt and client_name != "claude":
                sections.append(active_prompt)
                # Activation instruction is now embedded in user request below

            sections.append(guidance)

            # For first turn, embed compact RAPH activation with cognitive forcing
            # Requires evidence-based analysis that cannot be faked through parroting
            if is_first_turn and not skip_activation:
                user_content = (
                    "⚠️ CONSTITUTIONAL ACTIVATION REQUIRED (compact evidence-based mode):\n\n"
                    "Before executing the request below, perform constitutional integration in <100 words:\n\n"
                    "**READ**: List 3-4 core constitutional principles most relevant to THIS request (cite line numbers from your system prompt)\n"
                    "**ABSORB**: Identify 1 constitutional tension that applies to THIS SPECIFIC TASK\n"
                    "**PERCEIVE**: Predict 1 edge case where your constitution guides THIS TASK differently than a generic approach\n"
                    "**HARMONISE**: State 1 specific behavioral difference you will apply in YOUR EXECUTION\n\n"
                    "Format your activation as:\n"
                    "```\n"
                    "ACTIVATION:\n"
                    "READ: [3-4 principles with line #s]\n"
                    "ABSORB: [1 tension]\n"
                    "PERCEIVE: [1 edge case]\n"
                    "HARMONISE: [1 behavioral difference]\n"
                    "Activation Ready: READ=X, ABSORB=1, PERCEIVE=1, HARMONISE=1\n"
                    "```\n\n"
                    "Then execute the request with constitutional awareness.\n\n"
                    "=== REQUEST ===\n" + user_content
                )

            sections.append("=== USER REQUEST ===\n" + user_content)
            if file_section:
                sections.append("=== FILE REFERENCES ===\n" + file_section)
            sections.append("Provide your response below using your own CLI tools as needed:")

            final_prompt = "\n\n".join(sections)

            # Debug logging to understand activation behavior
            import sys
            debug_info = f"\n{'='*60}\nCLINK PROMPT DEBUG for {client_name}\nfirst_turn={is_first_turn}, skip_activation={skip_activation}\n{'='*60}\n{final_prompt[:1500]}...\n{'='*60}\n"
            print(debug_info, file=sys.stderr)
            logger.warning(debug_info)  # Use warning to ensure it appears in logs

            return final_prompt
        finally:
            self._active_system_prompt = ""

    def _build_success_metadata(
        self,
        client: ResolvedCLIClient,
        role: ResolvedCLIRole,
        result: AgentOutput,
    ) -> dict[str, Any]:
        """Capture execution metadata for successful CLI calls."""
        metadata: dict[str, Any] = {
            "cli_name": client.name,
            "role": role.name,
            "command": result.sanitized_command,
            "duration_seconds": round(result.duration_seconds, 3),
            "parser": result.parser_name,
            "return_code": result.returncode,
        }
        metadata.update(result.parsed.metadata)

        if result.stderr.strip():
            metadata.setdefault("stderr", result.stderr.strip())
        if result.output_file_content and "raw" not in metadata:
            metadata["raw_output_file"] = result.output_file_content
        return metadata

    def _merge_metadata(self, base: dict[str, Any] | None, extra: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base or {})
        merged.update(extra)
        return merged

    def _apply_output_limit(
        self,
        client: ResolvedCLIClient,
        content: str,
        metadata: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if len(content) <= MAX_RESPONSE_CHARS:
            return content, metadata

        summary = self._extract_summary(content)
        if summary:
            summary_text = summary
            if len(summary_text) > MAX_RESPONSE_CHARS:
                logger.debug(
                    "Clink summary from %s exceeded %d chars; truncating summary to fit.",
                    client.name,
                    MAX_RESPONSE_CHARS,
                )
                summary_text = summary_text[:MAX_RESPONSE_CHARS]
            summary_metadata = self._prune_metadata(metadata, client, reason="summary")
            summary_metadata.update(
                {
                    "output_summarized": True,
                    "output_original_length": len(content),
                    "output_summary_length": len(summary_text),
                    "output_limit": MAX_RESPONSE_CHARS,
                }
            )
            logger.info(
                "Clink compressed %s output via <SUMMARY>: original=%d chars, summary=%d chars",
                client.name,
                len(content),
                len(summary_text),
            )
            return summary_text, summary_metadata

        truncated_metadata = self._prune_metadata(metadata, client, reason="truncated")
        truncated_metadata.update(
            {
                "output_truncated": True,
                "output_original_length": len(content),
                "output_limit": MAX_RESPONSE_CHARS,
            }
        )

        excerpt_limit = min(4000, MAX_RESPONSE_CHARS // 2)
        excerpt = content[:excerpt_limit]
        truncated_metadata["output_excerpt_length"] = len(excerpt)

        logger.warning(
            "Clink truncated %s output: original=%d chars exceeds limit=%d; excerpt_length=%d",
            client.name,
            len(content),
            MAX_RESPONSE_CHARS,
            len(excerpt),
        )

        message = (
            f"CLI '{client.name}' produced {len(content)} characters, exceeding the configured clink limit "
            f"({MAX_RESPONSE_CHARS} characters). The full output was suppressed to stay within MCP response caps. "
            "Please narrow the request (review fewer files, summarize results) or run the CLI directly for the full log.\n\n"
            f"--- Begin excerpt ({len(excerpt)} of {len(content)} chars) ---\n{excerpt}\n--- End excerpt ---"
        )

        return message, truncated_metadata

    def _extract_summary(self, content: str) -> str | None:
        match = SUMMARY_PATTERN.search(content)
        if not match:
            return None
        summary = match.group(1).strip()
        return summary or None

    def _prune_metadata(
        self,
        metadata: dict[str, Any],
        client: ResolvedCLIClient,
        *,
        reason: str,
    ) -> dict[str, Any]:
        cleaned = dict(metadata)
        events = cleaned.pop("events", None)
        if events is not None:
            cleaned[f"events_removed_for_{reason}"] = True
            logger.debug(
                "Clink dropped %s events metadata for %s response (%s)",
                client.name,
                reason,
                type(events).__name__,
            )
        return cleaned

    def _build_error_metadata(self, client: ResolvedCLIClient, exc: CLIAgentError) -> dict[str, Any]:
        """Assemble metadata for failed CLI calls."""
        metadata: dict[str, Any] = {
            "cli_name": client.name,
            "return_code": exc.returncode,
        }
        if exc.stdout:
            metadata["stdout"] = exc.stdout.strip()
        if exc.stderr:
            metadata["stderr"] = exc.stderr.strip()
        return metadata

    def _error_response(self, message: str) -> TextContent:
        error_output = ToolOutput(status="error", content=message, content_type="text")
        return TextContent(type="text", text=error_output.model_dump_json())

    def _agent_capabilities_guidance(self, client_name: str) -> str:
        cli_display = client_name.title() if client_name else "the CLI"
        return (
            f"You are operating through the {cli_display} agent. You have access to your full suite of "
            "CLI capabilities—including launching web searches, reading files, and using any other "
            "available tools. Gather current information yourself and deliver the final answer without "
            "asking the Zen MCP host to perform searches or file reads."
        )

    def _format_file_references(self, files: list[str]) -> str:
        if not files:
            return ""

        references: list[str] = []
        for file_path in files:
            try:
                path = Path(file_path)
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                size = stat.st_size
                references.append(f"- {file_path} (last modified {modified}, {size} bytes)")
            except OSError:
                references.append(f"- {file_path} (unavailable)")
        return "\n".join(references)
