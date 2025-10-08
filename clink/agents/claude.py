"""Claude-specific CLI agent hooks."""

from __future__ import annotations

from clink.models import ResolvedCLIRole
from clink.parsers.base import ParserError

from .base import AgentOutput, BaseCLIAgent


class ClaudeAgent(BaseCLIAgent):
    """Claude CLI agent with system-prompt injection and JSON recovery support.

    This agent enhances Claude CLI execution by:
    1. Injecting role-specific system prompts via --append-system-prompt
    2. Providing graceful error recovery for non-zero exit codes with valid JSON

    The system prompt injection enables cleaner separation between system instructions
    and user content, leveraging Claude CLI's native system prompt handling.
    """

    def _build_command(self, *, role: ResolvedCLIRole, system_prompt: str | None) -> list[str]:
        """Build command with Claude CLI system prompt injection support.

        Claude CLI supports --append-system-prompt to inject role-specific behavior
        without embedding it in the user prompt. This provides cleaner separation
        between system instructions and user content.
        """
        command = list(self.client.executable)
        command.extend(self.client.internal_args)
        command.extend(self.client.config_args)

        # Inject system prompt via --append-system-prompt if not already configured
        if system_prompt and "--append-system-prompt" not in self.client.config_args:
            command.extend(["--append-system-prompt", system_prompt])

        command.extend(role.role_args)
        return command

    def _recover_from_error(
        self,
        *,
        returncode: int,
        stdout: str,
        stderr: str,
        sanitized_command: list[str],
        duration_seconds: float,
        output_file_content: str | None,
    ) -> AgentOutput | None:
        """Attempt to recover from Claude CLI errors by parsing JSON output.

        Claude CLI can return valid JSON even when exit code is non-zero,
        particularly when errors occur during execution but a response was
        generated (e.g., permission denials, MCP errors).
        """
        try:
            parsed = self._parser.parse(stdout, stderr)
        except ParserError:
            return None

        return AgentOutput(
            parsed=parsed,
            sanitized_command=sanitized_command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration_seconds,
            parser_name=self._parser.name,
            output_file_content=output_file_content,
        )
