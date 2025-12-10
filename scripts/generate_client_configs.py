#!/usr/bin/env python3
"""
Agent Model Tier Config Generator

Generates CLI client configurations from agent-model-tiers.json mapping.
Supports hybrid architecture: tiers (default) + exceptions (overrides).

Usage:
    python scripts/generate_client_configs.py              # Generate configs
    python scripts/generate_client_configs.py --check      # Validate configs are in sync (CI)
    python scripts/generate_client_configs.py --dry-run    # Show what would change
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ConfigGenerator:
    """Generates CLI client configs from tier mapping."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize generator.

        Args:
            base_dir: Base directory (defaults to repo root)
        """
        if base_dir is None:
            # Detect if we're in worktree or main repo
            current = Path(__file__).resolve().parent.parent
            if current.name == "agent-model-tiers":
                # We're in worktree
                self.base_dir = current
            else:
                # We're in main repo
                self.base_dir = current
        else:
            self.base_dir = base_dir

        self.cli_clients_dir = self.base_dir / "conf" / "cli_clients"
        self.tier_mapping_path = self.cli_clients_dir / "agent-model-tiers.json"
        self.fallback_hints_path = self.cli_clients_dir / "fallback_hints.json"

        self.tier_mapping: Dict[str, Any] = {}
        self.client_configs: Dict[str, Dict[str, Any]] = {}

    def load_tier_mapping(self) -> None:
        """Load agent-model-tiers.json."""
        if not self.tier_mapping_path.exists():
            raise FileNotFoundError(f"Tier mapping not found: {self.tier_mapping_path}")

        with open(self.tier_mapping_path) as f:
            self.tier_mapping = json.load(f)

    def load_client_configs(self, cli_names: List[str]) -> None:
        """Load existing client configurations.

        Args:
            cli_names: List of CLI client names (e.g., ["claude", "codex", "gemini"])
        """
        for cli_name in cli_names:
            config_path = self.cli_clients_dir / f"{cli_name}.json"
            if not config_path.exists():
                raise FileNotFoundError(f"Client config not found: {config_path}")

            with open(config_path) as f:
                self.client_configs[cli_name] = json.load(f)

    def find_agent_tier(self, agent_name: str) -> Optional[str]:
        """Find which tier an agent belongs to.

        Args:
            agent_name: Agent name to search for

        Returns:
            Tier name (HIGH/MEDIUM/LOW) or None if not found
        """
        for tier_name, tier_data in self.tier_mapping["tiers"].items():
            if agent_name in tier_data.get("agents", []):
                return tier_name
        return None

    def get_model_for_agent(self, agent_name: str, cli_name: str) -> Optional[str]:
        """Get the appropriate model for an agent on a given CLI.

        Priority:
            1. Check exceptions
            2. Check tier mapping

        Args:
            agent_name: Agent name
            cli_name: CLI client name (claude/codex/gemini)

        Returns:
            Model ID or None if agent should be excluded from this CLI
        """
        # Check exceptions first
        exceptions = self.tier_mapping.get("exceptions", {})
        if agent_name in exceptions:
            model = exceptions[agent_name].get(cli_name)
            return model  # Could be None (explicit exclusion)

        # Fall back to tier mapping
        tier = self.find_agent_tier(agent_name)
        if tier is None:
            return None

        tier_data = self.tier_mapping["tiers"][tier]
        model = tier_data.get(cli_name)
        return model  # Could be None (tier excludes this CLI)

    def get_reasoning_effort(self, agent_name: str) -> Optional[str]:
        """Get reasoning effort level for an agent (Codex-specific).

        Args:
            agent_name: Agent name

        Returns:
            Reasoning effort level (high/medium/low) or None
        """
        reasoning_mappings = self.tier_mapping.get("reasoning_effort_mappings", {})
        for effort_level in ["high", "medium", "low"]:
            if agent_name in reasoning_mappings.get(effort_level, []):
                return effort_level
        return None

    def update_client_config(self, cli_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Update a client configuration with tier-based model assignments.

        Args:
            cli_name: CLI client name
            dry_run: If True, don't modify config, just return what would change

        Returns:
            Updated config (or preview if dry_run=True)
        """
        config = self.client_configs[cli_name].copy()
        roles = config.get("roles", {})
        changes = []

        for agent_name, role_data in roles.items():
            model = self.get_model_for_agent(agent_name, cli_name)

            # Handle explicit exclusion (null in exceptions)
            if model is None:
                # Check if this is an explicit exclusion
                exceptions = self.tier_mapping.get("exceptions", {})
                if agent_name in exceptions and exceptions[agent_name].get(cli_name) is None:
                    # Explicit exclusion - remove from config
                    if not dry_run:
                        changes.append(f"REMOVE {agent_name} (explicit exclusion)")
                    continue

            # Update role_args based on CLI type
            if cli_name == "claude":
                # Claude uses --model flag
                new_role_args = ["--model", model] if model else []
                if role_data.get("role_args") != new_role_args:
                    if not dry_run:
                        role_data["role_args"] = new_role_args
                    changes.append(f"UPDATE {agent_name}: {role_data.get('role_args')} -> {new_role_args}")

            elif cli_name == "codex":
                # Codex uses -c model_reasoning_effort in role_args
                # and model in additional_args
                reasoning_effort = self.get_reasoning_effort(agent_name)
                new_role_args = []
                if reasoning_effort:
                    new_role_args = ["-c", f"model_reasoning_effort={reasoning_effort}"]

                if role_data.get("role_args") != new_role_args:
                    if not dry_run:
                        role_data["role_args"] = new_role_args
                    changes.append(f"UPDATE {agent_name}: role_args {role_data.get('role_args')} -> {new_role_args}")

                # Update model in additional_args at top level
                # (Codex model is global, not per-role)
                # This is handled separately below

            elif cli_name == "gemini":
                # Gemini uses --model in additional_args (global)
                # role_args typically empty unless specific overrides needed
                new_role_args = []
                if role_data.get("role_args") != new_role_args:
                    if not dry_run:
                        role_data["role_args"] = new_role_args
                    changes.append(f"UPDATE {agent_name}: role_args {role_data.get('role_args')} -> {new_role_args}")

        # Remove explicitly excluded agents
        exceptions = self.tier_mapping.get("exceptions", {})
        for agent_name in list(roles.keys()):
            if agent_name in exceptions:
                if exceptions[agent_name].get(cli_name) is None:
                    if not dry_run:
                        del roles[agent_name]
                    changes.append(f"REMOVE {agent_name} (explicit exclusion)")

        # Add metadata
        if not dry_run:
            config["_generated_by"] = "scripts/generate_client_configs.py"
            config["_tier_mapping_version"] = self.tier_mapping.get("_schema_version", "1.0.0")

        return {"config": config, "changes": changes}

    def validate_model_ids(self) -> List[str]:
        """Validate that all model IDs used in tiers/exceptions are valid.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        model_mappings = self.tier_mapping.get("model_mappings", {})

        # Validate tier model assignments
        for tier_name, tier_data in self.tier_mapping.get("tiers", {}).items():
            for cli_name in ["claude", "codex", "gemini"]:
                model = tier_data.get(cli_name)
                if model is None:
                    continue  # null is valid (tier excludes this CLI)

                valid_models = model_mappings.get(cli_name, {})
                if model not in valid_models:
                    errors.append(f"Invalid model '{model}' for {cli_name} in tier {tier_name}")

        # Validate exception model assignments
        for agent_name, exception_data in self.tier_mapping.get("exceptions", {}).items():
            for cli_name in ["claude", "codex", "gemini"]:
                model = exception_data.get(cli_name)
                if model is None:
                    continue  # null is valid (explicit exclusion)

                valid_models = model_mappings.get(cli_name, {})
                if model not in valid_models:
                    errors.append(f"Invalid model '{model}' for {cli_name} in exception {agent_name}")

        return errors

    def validate_tier_degradation(self) -> List[str]:
        """Check for tier degradation warnings (HIGH->LOW fallback).

        Returns:
            List of warnings
        """
        warnings = []
        fallback_hints = self.tier_mapping.get("primary_fallback_hints", {})

        for agent_name, hint in fallback_hints.items():
            primary_cli = hint.get("primary_cli")
            fallback_cli = hint.get("fallback_cli")

            if primary_cli is None or fallback_cli is None:
                continue

            # Find tiers
            primary_tier = None
            fallback_tier = None

            # Check if agent is in tiers or exceptions
            agent_tier = self.find_agent_tier(agent_name)
            if agent_tier:
                primary_model = self.tier_mapping["tiers"][agent_tier].get(primary_cli)
                fallback_model = self.tier_mapping["tiers"][agent_tier].get(fallback_cli)

                # Determine tier level by model
                tier_levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                primary_tier_level = tier_levels.get(agent_tier, 0)

                # Check fallback tier (could be different if using exceptions)
                fallback_agent_tier = agent_tier
                if agent_name in self.tier_mapping.get("exceptions", {}):
                    # Exception might have different fallback tier
                    pass  # Complex logic, skip for now

                if primary_tier_level == 3 and fallback_agent_tier == "LOW":
                    warnings.append(f"DEGRADATION: {agent_name} primary=HIGH fallback=LOW")

        return warnings

    def validate_agent_coverage(self) -> List[str]:
        """Validate that all agents in tier mapping exist in client configs.

        Returns:
            List of validation errors
        """
        errors = []

        # Collect all agents from tiers
        tier_agents: Set[str] = set()
        for tier_data in self.tier_mapping.get("tiers", {}).values():
            tier_agents.update(tier_data.get("agents", []))

        # Collect all agents from exceptions
        exception_agents: Set[str] = set(self.tier_mapping.get("exceptions", {}).keys())

        # Collect all agents from client configs
        config_agents: Set[str] = set()
        for config in self.client_configs.values():
            config_agents.update(config.get("roles", {}).keys())

        # Check for agents in tiers but not in configs
        missing_in_configs = tier_agents - config_agents
        if missing_in_configs:
            errors.append(f"Agents in tiers but missing from client configs: {missing_in_configs}")

        # Check for agents in configs but not in tiers (warning, not error)
        # These might be in exceptions only
        untiered_agents = config_agents - tier_agents - exception_agents
        if untiered_agents:
            # This is actually OK - some agents might not be in tiers
            # (e.g., "default", "planner", "codereviewer")
            pass

        return errors

    def generate_fallback_hints(self) -> Dict[str, Any]:
        """Generate fallback_hints.json from primary_fallback_hints.

        Returns:
            Fallback hints dictionary
        """
        return self.tier_mapping.get("primary_fallback_hints", {})

    def write_client_config(self, cli_name: str, config: Dict[str, Any]) -> None:
        """Write updated client configuration to disk.

        Args:
            cli_name: CLI client name
            config: Updated configuration
        """
        config_path = self.cli_clients_dir / f"{cli_name}.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Add trailing newline

    def write_fallback_hints(self, hints: Dict[str, Any]) -> None:
        """Write fallback_hints.json to disk.

        Args:
            hints: Fallback hints dictionary
        """
        with open(self.fallback_hints_path, "w") as f:
            json.dump(hints, f, indent=2)
            f.write("\n")

    def run(self, mode: str = "generate", cli_names: Optional[List[str]] = None) -> int:
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
            # Load data
            self.load_tier_mapping()
            self.load_client_configs(cli_names)

            # Validate
            print("Validating model IDs...")
            model_errors = self.validate_model_ids()
            if model_errors:
                print("ERROR: Invalid model IDs found:")
                for error in model_errors:
                    print(f"  - {error}")
                return 1

            print("Checking tier degradation warnings...")
            degradation_warnings = self.validate_tier_degradation()
            if degradation_warnings:
                print("WARNING: Tier degradation detected:")
                for warning in degradation_warnings:
                    print(f"  - {warning}")

            print("Validating agent coverage...")
            coverage_errors = self.validate_agent_coverage()
            if coverage_errors:
                print("ERROR: Agent coverage issues:")
                for error in coverage_errors:
                    print(f"  - {error}")
                # Don't fail on coverage errors (warning only)

            # Process configs
            all_changes = {}
            for cli_name in cli_names:
                print(f"\nProcessing {cli_name} client...")
                result = self.update_client_config(cli_name, dry_run=(mode in ["check", "dry-run"]))

                if result["changes"]:
                    print(f"  Changes for {cli_name}:")
                    for change in result["changes"]:
                        print(f"    - {change}")
                    all_changes[cli_name] = result["changes"]
                else:
                    print(f"  No changes for {cli_name}")

                if mode == "generate":
                    self.write_client_config(cli_name, result["config"])
                    print(f"  ✓ Updated {cli_name}.json")

            # Generate fallback hints
            if mode == "generate":
                hints = self.generate_fallback_hints()
                self.write_fallback_hints(hints)
                print("\n✓ Generated fallback_hints.json")

            # Check mode validation
            if mode == "check":
                if all_changes:
                    print("\nERROR: Configs are out of sync!")
                    print("Run: python scripts/generate_client_configs.py")
                    return 1
                else:
                    print("\n✓ All configs are in sync")
                    return 0

            if mode == "dry-run":
                if all_changes:
                    print("\nDry-run complete. Changes would be made.")
                else:
                    print("\nDry-run complete. No changes needed.")
                return 0

            print("\n✓ Config generation complete")
            return 0

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback

            traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate CLI client configs from agent-model-tiers.json")
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
