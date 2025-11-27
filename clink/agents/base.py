"""Execute configured CLI agents for the clink tool and parse output."""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import signal
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from clink.constants import DEFAULT_STREAM_LIMIT
from clink.models import ResolvedCLIClient, ResolvedCLIRole
from clink.parsers import BaseParser, ParsedCLIResponse, ParserError, get_parser

logger = logging.getLogger("clink.agent")

# Timeout for cleanup operations after killing a process (seconds)
CLEANUP_TIMEOUT_SECONDS = 30


@dataclass
class AgentOutput:
    """Container returned by CLI agents after successful execution."""

    parsed: ParsedCLIResponse
    sanitized_command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    parser_name: str
    output_file_content: str | None = None


class CLIAgentError(RuntimeError):
    """Raised when a CLI agent fails (non-zero exit, timeout, parse errors)."""

    def __init__(self, message: str, *, returncode: int | None = None, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class BaseCLIAgent:
    """Execute a configured CLI command and parse its output."""

    def __init__(self, client: ResolvedCLIClient):
        self.client = client
        self._parser: BaseParser = get_parser(client.parser)
        self._logger = logging.getLogger(f"clink.runner.{client.name}")

    async def run(
        self,
        *,
        role: ResolvedCLIRole,
        prompt: str,
        system_prompt: str | None = None,
        files: Sequence[str],
        images: Sequence[str],
    ) -> AgentOutput:
        # Files and images are already embedded into the prompt by the tool; they are
        # accepted here only to keep parity with SimpleTool callers.
        _ = (files, images)
        # The runner simply executes the configured CLI command for the selected role.
        command = self._build_command(role=role, system_prompt=system_prompt)
        env = self._build_environment()
        sanitized_command = list(command)

        cwd = str(self.client.working_dir) if self.client.working_dir else None
        limit = DEFAULT_STREAM_LIMIT

        stdout_text = ""
        stderr_text = ""
        output_file_content: str | None = None
        start_time = time.monotonic()

        output_file_path: Path | None = None
        command_with_output_flag = list(command)

        if self.client.output_to_file:
            fd, tmp_path = tempfile.mkstemp(prefix="clink-", suffix=".json")
            os.close(fd)
            output_file_path = Path(tmp_path)
            flag_template = self.client.output_to_file.flag_template
            try:
                rendered_flag = flag_template.format(path=str(output_file_path))
            except KeyError as exc:  # pragma: no cover - defensive
                raise CLIAgentError(f"Invalid output flag template '{flag_template}': missing placeholder {exc}")
            command_with_output_flag.extend(shlex.split(rendered_flag))
            sanitized_command = list(command_with_output_flag)

        self._logger.debug("Executing CLI command: %s", " ".join(sanitized_command))
        if cwd:
            self._logger.debug("Working directory: %s", cwd)

        # Determine if we can use process groups (POSIX only)
        use_process_group = sys.platform != "win32"

        try:
            # On POSIX systems, use start_new_session=True to create a new process group.
            # This allows us to kill all child processes (including grandchildren) on timeout.
            process = await asyncio.create_subprocess_exec(
                *command_with_output_flag,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                limit=limit,
                env=env,
                start_new_session=use_process_group,
            )
        except FileNotFoundError as exc:
            raise CLIAgentError(f"Executable not found for CLI '{self.client.name}': {exc}") from exc

        pid = process.pid
        timeout_seconds = self.client.timeout_seconds

        self._logger.info(
            "[SUBPROCESS] Started CLI '%s' (PID=%d, process_group=%s, timeout=%ds)",
            self.client.name,
            pid,
            use_process_group,
            timeout_seconds,
        )

        # Use two-stage timeout pattern to avoid hanging on cleanup
        communicate_task = asyncio.create_task(process.communicate(prompt.encode("utf-8")))

        try:
            # Wait for subprocess to complete with timeout
            done, pending = await asyncio.wait({communicate_task}, timeout=timeout_seconds)

            if communicate_task in done:
                # Normal completion
                stdout_bytes, stderr_bytes = communicate_task.result()
                duration = time.monotonic() - start_time
                self._logger.info(
                    "[SUBPROCESS] CLI '%s' (PID=%d) completed normally in %.1fs",
                    self.client.name,
                    pid,
                    duration,
                )
            else:
                # Timeout occurred - need to kill process and cleanup
                duration = time.monotonic() - start_time
                self._logger.error(
                    "[SUBPROCESS] TIMEOUT after %.1fs for CLI '%s' (PID=%d) - initiating kill sequence",
                    duration,
                    self.client.name,
                    pid,
                )

                # Cancel the communicate task first
                communicate_task.cancel()
                try:
                    await communicate_task
                except asyncio.CancelledError:
                    pass

                # Kill the process (and entire process group on POSIX)
                await self._kill_process_tree(process, use_process_group)

                raise CLIAgentError(
                    f"CLI '{self.client.name}' timed out after {timeout_seconds} seconds (PID={pid})",
                    returncode=None,
                )

        except asyncio.CancelledError:
            # Task was cancelled externally - still need to cleanup
            self._logger.warning(
                "[SUBPROCESS] Task cancelled for CLI '%s' (PID=%d) - cleaning up",
                self.client.name,
                pid,
            )
            communicate_task.cancel()
            try:
                await communicate_task
            except asyncio.CancelledError:
                pass
            await self._kill_process_tree(process, use_process_group)
            raise

        duration = time.monotonic() - start_time
        return_code = process.returncode
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        if output_file_path and output_file_path.exists():
            output_file_content = output_file_path.read_text(encoding="utf-8", errors="replace")
            if self.client.output_to_file and self.client.output_to_file.cleanup:
                try:
                    output_file_path.unlink()
                except OSError:  # pragma: no cover - best effort cleanup
                    pass

            if output_file_content and not stdout_text.strip():
                stdout_text = output_file_content

        if return_code != 0:
            recovered = self._recover_from_error(
                returncode=return_code,
                stdout=stdout_text,
                stderr=stderr_text,
                sanitized_command=sanitized_command,
                duration_seconds=duration,
                output_file_content=output_file_content,
            )
            if recovered is not None:
                return recovered

        if return_code != 0:
            raise CLIAgentError(
                f"CLI '{self.client.name}' exited with status {return_code}",
                returncode=return_code,
                stdout=stdout_text,
                stderr=stderr_text,
            )

        try:
            parsed = self._parser.parse(stdout_text, stderr_text)
        except ParserError as exc:
            raise CLIAgentError(
                f"Failed to parse output from CLI '{self.client.name}': {exc}",
                returncode=return_code,
                stdout=stdout_text,
                stderr=stderr_text,
            ) from exc

        return AgentOutput(
            parsed=parsed,
            sanitized_command=sanitized_command,
            returncode=return_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_seconds=duration,
            parser_name=self._parser.name,
            output_file_content=output_file_content,
        )

    async def _kill_process_tree(self, process: asyncio.subprocess.Process, use_process_group: bool) -> None:
        """Kill the process and all its children, with robust cleanup.

        On POSIX systems with process groups enabled, kills the entire process group.
        Falls back to killing just the process on Windows or if process group kill fails.
        """
        pid = process.pid

        if use_process_group:
            # Try to kill the entire process group (SIGKILL to all children)
            try:
                self._logger.info("[SUBPROCESS] Killing process group for PID=%d", pid)
                os.killpg(pid, signal.SIGKILL)
                self._logger.info("[SUBPROCESS] Process group kill signal sent for PID=%d", pid)
            except (ProcessLookupError, PermissionError) as e:
                # Process group may already be dead or we don't have permission
                self._logger.warning(
                    "[SUBPROCESS] Process group kill failed for PID=%d: %s - falling back to direct kill",
                    pid,
                    e,
                )
                try:
                    process.kill()
                except ProcessLookupError:
                    pass  # Already dead
        else:
            # Windows or fallback: just kill the direct process
            self._logger.info("[SUBPROCESS] Killing process PID=%d (no process group)", pid)
            try:
                process.kill()
            except ProcessLookupError:
                pass  # Already dead

        # Close the pipes explicitly to prevent hanging on grandchild processes
        # that may have inherited the file descriptors
        self._logger.debug("[SUBPROCESS] Closing pipes for PID=%d", pid)
        if process.stdin:
            try:
                process.stdin.close()
            except Exception:
                pass
        if process.stdout:
            try:
                process.stdout.feed_eof()
            except Exception:
                pass
        if process.stderr:
            try:
                process.stderr.feed_eof()
            except Exception:
                pass

        # Wait for process to actually terminate with a timeout
        # Don't use communicate() here as it can hang if grandchildren hold pipes
        self._logger.debug("[SUBPROCESS] Waiting for process PID=%d to terminate", pid)
        try:
            await asyncio.wait_for(process.wait(), timeout=CLEANUP_TIMEOUT_SECONDS)
            self._logger.info("[SUBPROCESS] Process PID=%d terminated with code %s", pid, process.returncode)
        except asyncio.TimeoutError:
            self._logger.error(
                "[SUBPROCESS] Process PID=%d did not terminate within %ds after kill - possible zombie",
                pid,
                CLEANUP_TIMEOUT_SECONDS,
            )

    def _build_command(self, *, role: ResolvedCLIRole, system_prompt: str | None) -> list[str]:
        base = list(self.client.executable)
        base.extend(self.client.internal_args)
        base.extend(self.client.config_args)
        base.extend(role.role_args)

        return base

    def _build_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(self.client.env)
        return env

    # ------------------------------------------------------------------
    # Error recovery hooks
    # ------------------------------------------------------------------

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
        """Hook for subclasses to convert CLI errors into successful outputs.

        Return an AgentOutput to treat the failure as success, or None to signal
        that normal error handling should proceed.
        """

        return None
