"""AI helper module for Context Steward tasks.

Configuration-driven integration with clink for delegating tasks to
system-steward role via external AI CLIs (primarily Gemini for free quota).

Provides:
- Configuration loading and caching
- Task enabled checks (global + per-task)
- Prompt template building with variable substitution
- End-to-end task execution via clink with XML response parsing
- Graceful degradation on errors
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from tools.clink import CLinkTool
from tools.context_steward.octave_utils import parse_context_steward_response

logger = logging.getLogger(__name__)

# Configuration file path (can be overridden for testing)
CONFIG_FILE = Path(__file__).parent.parent.parent / "conf" / "context_steward.json"


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
        2. Prompt building from template
        3. clink execution with system-steward role
        4. XML response parsing
        5. Error handling with graceful degradation

        Args:
            task_key: Task identifier
            **context: Variables for template substitution and clink params

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
            >>> result = await ai.run_task("session_compression", session_id="abc123")
            >>> if result["status"] == "success":
            ...     octave_content = result["artifacts"][0]["content"]
        """
        # Check if task is enabled
        if not self.is_task_enabled(task_key):
            return {"status": "skipped", "reason": f"Task '{task_key}' is disabled in configuration"}

        try:
            config = self.load_config()
            task_config = config["tasks"][task_key]

            # Build prompt from template
            prompt = self.build_prompt(task_key, **context)

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

            if response_data.get("status") != "success":
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
