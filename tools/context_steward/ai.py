"""AI helper module for Context Steward tasks.

Configuration-driven integration with clink for delegating tasks to
system-steward role via external AI CLIs (primarily Gemini for free quota).

Provides:
- Configuration loading and caching
- Task enabled checks (global + per-task)
- Prompt template building with variable substitution
- End-to-end task execution via clink with XML response parsing
- Graceful degradation on errors
- Runtime signal gathering for AI context enrichment
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from tools.clink import CLinkTool
from tools.context_steward.octave_utils import parse_context_steward_response

logger = logging.getLogger(__name__)

# Configuration file path (can be overridden for testing)
CONFIG_FILE = Path(__file__).parent.parent.parent / "conf" / "context_steward.json"


def _gather_signals_sync(working_dir: str) -> dict[str, str]:
    """Synchronous helper for signal gathering (internal use only).

    This function performs blocking subprocess calls and should only be
    called via asyncio.to_thread() to avoid blocking the event loop.

    Args:
        working_dir: Project working directory path

    Returns:
        Dictionary with signal keys (see gather_signals for details)
    """
    signals = {
        "branch": "unknown",
        "commit": "unknown",
        "lint_status": "pending",
        "typecheck_status": "pending",
        "test_status": "pending",
        "authority": "unassigned",
    }

    # Gather git signals
    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            signals["branch"] = result.stdout.strip()

        # Get latest commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            signals["commit"] = result.stdout.strip()

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.debug(f"Git signal gathering failed (using fallbacks): {e}")

    # Quality gate status would be gathered from recent CI runs or log files
    # For now, we use "pending" as the default
    # Future enhancement: Parse logs or CI status files

    # Authority would be gathered from state vector or .hestai/state.json
    # For now, we use "unassigned" as the default
    # Future enhancement: Read from state management system

    return signals


async def gather_signals(working_dir: str) -> dict[str, str]:
    """Gather runtime signals for AI context enrichment (async).

    Collects contextual information about the current state of the project:
    - Git branch and commit hash
    - Quality gate status (lint, typecheck, test)
    - Authority ownership from state vector

    This function runs blocking subprocess calls in a background thread to
    avoid blocking the event loop.

    Args:
        working_dir: Project working directory path

    Returns:
        Dictionary with signal keys:
        - branch: Current git branch (fallback: "unknown")
        - commit: Latest commit hash (fallback: "unknown")
        - lint_status: Lint status ("passing", "failing", or "pending")
        - typecheck_status: Typecheck status ("passing", "failing", or "pending")
        - test_status: Test status ("passing", "failing", or "pending")
        - authority: Authority owner from state vector (fallback: "unassigned")

    Example:
        >>> signals = await gather_signals("/path/to/project")
        >>> print(signals["branch"])
        'feature/context-steward-octave'
        >>> print(signals["commit"])
        'dcb28e9abc123...'
    """
    # Offload blocking subprocess calls to background thread
    return await asyncio.to_thread(_gather_signals_sync, working_dir)


class ContextStewardAI:
    """AI integration for Context Steward tasks via clink delegation.

    Features:
    - Configuration-driven task orchestration
    - Prompt template loading with variable substitution
    - clink integration for system-steward role execution
    - XML response parsing with robust error handling
    - Graceful degradation (returns error status vs raising)

    Example:
        >>> ai = ContextStewardAI()
        >>> if ai.is_task_enabled("session_compression"):
        ...     result = await ai.run_task("session_compression", session_id="abc123")
        ...     if result["status"] == "success":
        ...         print(result["summary"])
    """

    def __init__(self):
        """Initialize Context Steward AI helper.

        Loads configuration on first use (lazy loading with caching).
        """
        self._config: Optional[dict[str, Any]] = None
        self._clink_tool: Optional[CLinkTool] = None

    def load_config(self) -> dict[str, Any]:
        """Load configuration from conf/context_steward.json with caching.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration file contains invalid JSON

        Example:
            >>> ai = ContextStewardAI()
            >>> config = ai.load_config()
            >>> print(config["version"])
            '1.0.0'
        """
        # Return cached config if available
        if self._config is not None:
            return self._config

        # Load config from file
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

        try:
            config_text = CONFIG_FILE.read_text(encoding="utf-8")
            self._config = json.loads(config_text)
            logger.debug(f"Loaded Context Steward configuration from {CONFIG_FILE}")
            return self._config
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}") from e

    def is_task_enabled(self, task_key: str) -> bool:
        """Check if a task is enabled (global + per-task checks).

        Args:
            task_key: Task identifier (e.g., "session_compression")

        Returns:
            True if task is enabled, False otherwise

        Example:
            >>> ai = ContextStewardAI()
            >>> if ai.is_task_enabled("session_compression"):
            ...     # Execute task
            ...     pass
        """
        try:
            config = self.load_config()

            # Check global enabled flag
            if not config.get("enabled", False):
                return False

            # Check task exists
            tasks = config.get("tasks", {})
            if task_key not in tasks:
                return False

            # Check task enabled flag
            task_config = tasks[task_key]
            return task_config.get("enabled", False)

        except Exception as e:
            logger.warning(f"Error checking task enabled status: {e}")
            return False

    def build_prompt(self, task_key: str, **context) -> str:
        """Build prompt from template with variable substitution.

        Uses simple {{variable}} syntax for template variables. Missing variables
        are left as placeholders for debugging.

        Args:
            task_key: Task identifier
            **context: Variables for template substitution

        Returns:
            Rendered prompt string

        Raises:
            FileNotFoundError: If template file doesn't exist
            KeyError: If task not found in configuration

        Example:
            >>> ai = ContextStewardAI()
            >>> prompt = ai.build_prompt("session_compression", session_id="abc123", role="lead")
            >>> print(prompt)
            'Compress session: abc123...'
        """
        config = self.load_config()
        tasks = config.get("tasks", {})

        if task_key not in tasks:
            raise KeyError(f"Task '{task_key}' not found in configuration")

        task_config = tasks[task_key]
        template_path = Path(task_config["prompt_template"])

        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        # Load template
        template_text = template_path.read_text(encoding="utf-8")

        # Simple variable substitution using {{variable}} syntax
        # Missing variables are left as {{variable}} for debugging
        rendered = template_text
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            rendered = rendered.replace(placeholder, str(value))

        return rendered

    async def run_task(self, task_key: str, **context) -> dict[str, Any]:
        """Execute task via clink with XML response parsing.

        Orchestrates:
        1. Task enabled check
        2. Signal gathering (branch, commit, quality gates, authority)
        3. Prompt building from template with signals
        4. clink execution with system-steward role
        5. XML response parsing
        6. Error handling with graceful degradation

        Args:
            task_key: Task identifier
            **context: Variables for template substitution and clink params.
                      Must include 'working_dir' for signal gathering.

        Returns:
            Dictionary with parsed response:
            - status: "success", "skipped", "error"
            - task_id: Task identifier if successful
            - summary: Summary text if successful
            - artifacts: List of artifact dicts if successful
            - reason: Skip/error reason if not successful
            - error: Error details if error occurred

        Example:
            >>> ai = ContextStewardAI()
            >>> result = await ai.run_task("session_compression",
            ...                           session_id="abc123",
            ...                           working_dir="/path/to/project")
            >>> if result["status"] == "success":
            ...     octave_content = result["artifacts"][0]["content"]
        """
        # Check if task is enabled
        if not self.is_task_enabled(task_key):
            return {"status": "skipped", "reason": f"Task '{task_key}' is disabled in configuration"}

        try:
            config = self.load_config()
            task_config = config["tasks"][task_key]

            # Gather runtime signals if working_dir is provided
            working_dir = context.get("working_dir", ".")
            signals = await gather_signals(working_dir)

            # Merge signals into context (signals can be overridden by explicit context)
            enriched_context = {**signals, **context}

            logger.debug(
                f"Enriched context for task '{task_key}': branch={signals['branch']}, "
                f"commit={signals['commit'][:8]}..., quality_gates=pending"
            )

            # Build prompt from template with enriched context
            prompt = self.build_prompt(task_key, **enriched_context)

            # Get CLI configuration
            cli_name = task_config.get("cli", config.get("default_cli", "gemini"))
            role = task_config.get("role", "system-steward")

            # Get files from task config or context
            files = context.get("files", task_config.get("files", []))
            # Substitute variables in file paths (e.g., {transcript_path})
            resolved_files = []
            for file_path in files:
                # Simple variable substitution for file paths
                for key, value in context.items():
                    file_path = file_path.replace(f"{{{key}}}", str(value))
                resolved_files.append(file_path)

            # Initialize clink tool if needed
            if self._clink_tool is None:
                self._clink_tool = CLinkTool()

            # Execute via clink
            arguments = {
                "prompt": prompt,
                "cli_name": cli_name,
                "role": role,
                "files": resolved_files,
            }

            logger.info(f"Executing task '{task_key}' via clink (cli={cli_name}, role={role})")
            clink_response = await self._clink_tool.execute(arguments)

            # Parse clink response
            if not clink_response:
                return {"status": "error", "error": "Empty response from clink"}

            response_text = clink_response[0].text
            response_data = json.loads(response_text)

            # Clink returns "success" or "continuation_available" for successful calls
            clink_status = response_data.get("status", "")
            if clink_status not in ("success", "continuation_available"):
                return {
                    "status": "error",
                    "error": f"Clink execution failed: {response_data.get('content', 'Unknown error')}",
                }

            # Parse OCTAVE response from clink content
            octave_content = response_data.get("content", "")
            parsed = parse_context_steward_response(octave_content)

            logger.info(f"Task '{task_key}' completed with status: {parsed.get('status')}")
            return parsed

        except Exception as e:
            logger.error(f"Error executing task '{task_key}': {e}", exc_info=True)
            return {"status": "error", "error": str(e), "exception": type(e).__name__}
