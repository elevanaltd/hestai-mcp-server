#!/usr/bin/env python3
"""
Agent Routing Config Generator

Generates CLI client configurations from agent-routing.yaml.
Each agent can be configured individually with specific models per CLI.

Usage:
    python scripts/generate_client_configs.py              # Generate configs
    python scripts/generate_client_configs.py --check      # Validate configs are in sync (CI)
    python scripts/generate_client_configs.py --dry-run    # Show what would change
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigGenerator:
    """Generates CLI client configs from agent-routing.yaml."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize generator.

        Args:
            base_dir: Base directory (defaults to repo root)
        """
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent
        else:
            self.base_dir = base_dir

        self.cli_clients_dir = self.base_dir / "conf" / "cli_clients"
        self.routing_config_path = self.base_dir / "conf" / "agent-routing.yaml"
        self.systemprompts_dir = self.base_dir / "systemprompts" / "clink"

        self.routing_config: dict[str, Any] = {}
        self.client_configs: dict[str, dict[str, Any]] = {}

    def load_routing_config(self) -> None:
        """Load agent-routing.yaml."""
        if not self.routing_config_path.exists():
            raise FileNotFoundError(f"Routing config not found: {self.routing_config_path}")

        with open(self.routing_config_path) as f:
            self.routing_config = yaml.safe_load(f)

    def load_client_configs(self, cli_names: list[str]) -> None:
        """Load existing client configurations.

        Args:
            cli_names: List of CLI client names (e.g., ["claude", "codex", "gemini"])
        """
        for cli_name in cli_names:
            config_path = self.cli_clients_dir / f"{cli_name}.json"
            if config_path.exists():
                with open(config_path) as f:
                    self.client_configs[cli_name] = json.load(f)
            else:
                # Create minimal config if doesn't exist
                self.client_configs[cli_name] = {
                    "name": cli_name,
                    "command": cli_name,
                    "additional_args": [],
                    "env": {},
                    "roles": {},
                }

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """Get configuration for a specific agent.

        Args:
            agent_name: Agent name

        Returns:
            Agent configuration dict, or defaults if not found
        """
        agents = self.routing_config.get("agents", {})
        if agent_name in agents:
            return agents[agent_name]

        # Return defaults
        return self.routing_config.get("defaults", {})

    def get_model_for_agent(self, agent_name: str, cli_name: str) -> Optional[str]:
        """Get the model for an agent on a specific CLI.

        Args:
            agent_name: Agent name
            cli_name: CLI name (claude/codex/gemini)

        Returns:
            Model ID or None if agent excluded from this CLI
        """
        agent_config = self.get_agent_config(agent_name)
        model = agent_config.get(cli_name)

        # Handle explicit null (excluded) vs missing (use default)
        if model is None and cli_name not in agent_config:
            # Not explicitly configured, use default
            defaults = self.routing_config.get("defaults", {})
            model = defaults.get(cli_name)

        return model

    def get_reasoning_effort(self, agent_name: str) -> Optional[str]:
        """Get reasoning effort level for an agent (Codex-specific).

        Args:
            agent_name: Agent name

        Returns:
            Reasoning effort level (high/medium/low) or None
        """
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get("reasoning_effort")

    def get_prompt_path(self, agent_name: str, cli_name: str = None) -> Optional[str]:
        """Get the system prompt path for an agent.

        Args:
            agent_name: Agent name
            cli_name: CLI name (for prompt_override lookup)

        Returns:
            Relative path to prompt file, or None if not found
        """
        agent_config = self.get_agent_config(agent_name)

        # Check for CLI-specific prompt override
        if cli_name and "prompt_override" in agent_config:
            override = agent_config["prompt_override"].get(cli_name)
            if override:
                prompt_file = self.systemprompts_dir / override
                if prompt_file.exists():
                    return f"systemprompts/clink/{override}"

        # Check for agent-specific prompt
        prompt_file = self.systemprompts_dir / f"{agent_name}.txt"
        if prompt_file.exists():
            return f"systemprompts/clink/{agent_name}.txt"

        # Check for default prompt
        default_prompt = self.systemprompts_dir / "default.txt"
        if default_prompt.exists():
            return "systemprompts/clink/default.txt"

        return None

    def discover_agents(self) -> set[str]:
        """Discover all available agents from systemprompts directory.

        Returns:
            Set of agent names
        """
        agents = set()
        if self.systemprompts_dir.exists():
            for prompt_file in self.systemprompts_dir.glob("*.txt"):
                agent_name = prompt_file.stem
                # Skip internal files
                if agent_name.startswith("_"):
                    continue
                # Skip CLI-specific variants (handled separately)
                if agent_name.startswith("codex_") or agent_name.startswith("default_"):
                    agents.add(agent_name)  # Include these as valid roles
                else:
                    agents.add(agent_name)
        return agents

    def build_role_args(self, agent_name: str, cli_name: str, model: str) -> list[str]:
        """Build role_args for a specific agent/CLI combination.

        Args:
            agent_name: Agent name
            cli_name: CLI name
            model: Model ID

        Returns:
            List of role arguments
        """
        role_args = []

        if cli_name == "claude":
            # Claude uses --model in role_args
            if model:
                role_args = ["--model", model]

        elif cli_name == "codex":
            # Codex uses -c model_reasoning_effort in role_args
            reasoning_effort = self.get_reasoning_effort(agent_name)
            if reasoning_effort:
                role_args = ["-c", f"model_reasoning_effort={reasoning_effort}"]

        elif cli_name == "gemini":
            # Gemini uses --model in additional_args (global), role_args typically empty
            pass

        return role_args

    def generate_client_config(
        self, cli_name: str, dry_run: bool = False
    ) -> dict[str, Any]:
        """Generate a complete client configuration.

        Args:
            cli_name: CLI name
            dry_run: If True, don't modify anything

        Returns:
            Dict with 'config' and 'changes' keys
        """
        # Start with existing config or minimal template
        if cli_name in self.client_configs:
            config = self.client_configs[cli_name].copy()
        else:
            config = {
                "name": cli_name,
                "command": cli_name,
                "additional_args": [],
                "env": {},
                "roles": {},
            }

        changes = []
        new_roles = {}

        # Get all agents from routing config
        agents = self.routing_config.get("agents", {})

        for agent_name, agent_config in agents.items():
            model = agent_config.get(cli_name)

            # Skip if agent is excluded from this CLI (explicit null)
            if model is None:
                if agent_name in config.get("roles", {}):
                    changes.append(f"REMOVE {agent_name} (excluded from {cli_name})")
                continue

            # Get prompt path (with CLI-specific override support)
            prompt_path = self.get_prompt_path(agent_name, cli_name)
            if not prompt_path:
                changes.append(f"SKIP {agent_name} (no prompt file)")
                continue

            # Build role args
            role_args = self.build_role_args(agent_name, cli_name, model)

            # Check for changes
            existing_role = config.get("roles", {}).get(agent_name, {})
            new_role = {"prompt_path": prompt_path, "role_args": role_args}

            if existing_role != new_role:
                if agent_name in config.get("roles", {}):
                    changes.append(f"UPDATE {agent_name}: {existing_role} -> {new_role}")
                else:
                    changes.append(f"ADD {agent_name}: {new_role}")

            new_roles[agent_name] = new_role

        # Check for removed roles
        for existing_agent in config.get("roles", {}).keys():
            if existing_agent not in new_roles:
                # Check if it's explicitly excluded or just not in routing config
                if existing_agent in agents:
                    agent_config = agents[existing_agent]
                    if agent_config.get(cli_name) is None:
                        changes.append(f"REMOVE {existing_agent} (excluded)")
                # Keep roles that aren't in routing config (legacy compatibility)
                else:
                    new_roles[existing_agent] = config["roles"][existing_agent]

        # Update config
        if not dry_run:
            config["roles"] = dict(sorted(new_roles.items()))
            config["_generated_by"] = "scripts/generate_client_configs.py"
            config["_routing_version"] = self.routing_config.get("schema_version", "2.0.0")

        return {"config": config, "changes": changes}

    def validate_routing_config(self) -> list[str]:
        """Validate the routing configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        available_models = self.routing_config.get("available_models", {})

        for agent_name, agent_config in self.routing_config.get("agents", {}).items():
            for cli_name in ["claude", "codex", "gemini"]:
                model = agent_config.get(cli_name)
                if model is None:
                    continue  # null is valid (exclusion)

                valid_models = available_models.get(cli_name, [])
                if valid_models and model not in valid_models:
                    errors.append(
                        f"Invalid model '{model}' for {cli_name} in agent {agent_name}. "
                        f"Valid: {valid_models}"
                    )

            # Validate primary CLI
            primary = agent_config.get("primary")
            if primary and primary not in ["claude", "codex", "gemini"]:
                errors.append(
                    f"Invalid primary CLI '{primary}' for agent {agent_name}"
                )

            # Validate reasoning_effort
            reasoning = agent_config.get("reasoning_effort")
            if reasoning and reasoning not in ["high", "medium", "low"]:
                errors.append(
                    f"Invalid reasoning_effort '{reasoning}' for agent {agent_name}"
                )

        return errors

    def validate_prompt_coverage(self) -> list[str]:
        """Validate that all configured agents have prompt files.

        Returns:
            List of warnings (not errors)
        """
        warnings = []

        for agent_name in self.routing_config.get("agents", {}).keys():
            prompt_path = self.get_prompt_path(agent_name)
            if not prompt_path:
                warnings.append(f"No prompt file for agent: {agent_name}")

        return warnings

    def write_client_config(self, cli_name: str, config: dict[str, Any]) -> None:
        """Write client configuration to disk.

        Args:
            cli_name: CLI name
            config: Configuration dict
        """
        config_path = self.cli_clients_dir / f"{cli_name}.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")

    def run(self, mode: str = "generate", cli_names: Optional[list[str]] = None) -> int:
        """Run the generator.

        Args:
            mode: Operation mode (generate/check/dry-run)
            cli_names: List of CLI clients to process (defaults to all)

        Returns:
            Exit code (0=success, 1=failure)
        """
        if cli_names is None:
            cli_names = ["claude", "codex", "gemini"]

        try:
            # Load configs
            print("Loading routing configuration...")
            self.load_routing_config()
            self.load_client_configs(cli_names)

            # Validate
            print("Validating routing configuration...")
            errors = self.validate_routing_config()
            if errors:
                print("ERROR: Invalid routing configuration:")
                for error in errors:
                    print(f"  - {error}")
                return 1

            print("Checking prompt coverage...")
            warnings = self.validate_prompt_coverage()
            if warnings:
                print("WARNING: Missing prompt files:")
                for warning in warnings:
                    print(f"  - {warning}")

            # Process configs
            all_changes = {}
            for cli_name in cli_names:
                print(f"\nProcessing {cli_name} client...")
                result = self.generate_client_config(
                    cli_name, dry_run=(mode in ["check", "dry-run"])
                )

                if result["changes"]:
                    print(f"  Changes for {cli_name}:")
                    for change in result["changes"]:
                        print(f"    - {change}")
                    all_changes[cli_name] = result["changes"]
                else:
                    print(f"  No changes for {cli_name}")

                if mode == "generate":
                    self.write_client_config(cli_name, result["config"])
                    print(f"  -> Updated {cli_name}.json")

            # Summary
            if mode == "check":
                if all_changes:
                    print("\nERROR: Configs are out of sync!")
                    print("Run: python scripts/generate_client_configs.py")
                    return 1
                else:
                    print("\n All configs are in sync")
                    return 0

            if mode == "dry-run":
                if all_changes:
                    print("\nDry-run complete. Changes would be made.")
                else:
                    print("\nDry-run complete. No changes needed.")
                return 0

            print("\n Config generation complete")
            return 0

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback

            traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate CLI client configs from agent-routing.yaml"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configs are in sync (for CI)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    parser.add_argument(
        "--cli",
        nargs="+",
        choices=["claude", "codex", "gemini"],
        help="Specific CLI clients to process (default: all)",
    )

    args = parser.parse_args()

    # Determine mode
    if args.check:
        mode = "check"
    elif args.dry_run:
        mode = "dry-run"
    else:
        mode = "generate"

    generator = ConfigGenerator()
    exit_code = generator.run(mode=mode, cli_names=args.cli)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
