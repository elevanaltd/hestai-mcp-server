#!/usr/bin/env python3
"""
generate_client_configs.py

Generates explicit CLI client configurations (claude.json, gemini.json, codex.json)
by applying model tier mappings from agent-model-tiers.json.

Usage:
    python scripts/generate_client_configs.py
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Constants
BASE_DIR = Path(__file__).resolve().parent.parent
CONF_DIR = BASE_DIR / "conf" / "cli_clients"
TIER_MAPPING_FILE = CONF_DIR / "agent-model-tiers.json"

CLIENT_FILES = {
    "claude": CONF_DIR / "claude.json",
    "gemini": CONF_DIR / "gemini.json",
    "codex": CONF_DIR / "codex.json"
}

def load_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}")
        sys.exit(1)

def save_json(path: Path, data: Dict[str, Any]) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n') # Add trailing newline

def get_agent_tier_map(tier_data: Dict[str, Any]) -> Dict[str, str]:
    """Inverts the tier structure to map agent -> tier_name."""
    agent_map = {}
    for tier_name, tier_info in tier_data["tiers"].items():
        for agent in tier_info["agents"]:
            if agent in agent_map:
                print(f"Warning: Agent '{agent}' defined in multiple tiers. Overwriting with {tier_name}.")
            agent_map[agent] = tier_name
    return agent_map

def get_tier_models(tier_data: Dict[str, Any], client_name: str) -> Dict[str, str]:
    """Extracts model IDs for a specific client across all tiers."""
    models = {}
    for tier_name, tier_info in tier_data["tiers"].items():
        if client_name in tier_info["model_assignments"]:
            models[tier_name] = tier_info["model_assignments"][client_name]
        else:
            print(f"Warning: No model assignment for client '{client_name}' in tier '{tier_name}'")
    return models

def update_client_config(client_name: str, config_path: Path, tier_data: Dict[str, Any], agent_tier_map: Dict[str, str]):
    print(f"Processing {client_name} config...")

    if not config_path.exists():
        print(f"  Skipping {client_name}: Config file not found at {config_path}")
        return

    config = load_json(config_path)
    tier_models = get_tier_models(tier_data, client_name)

    updated_count = 0
    missing_tier_count = 0

    # Ensure 'roles' key exists
    if "roles" not in config:
        print(f"  Error: No 'roles' key in {client_name} config")
        return

    for role_name, role_data in config["roles"].items():
        # Determine tier
        tier = agent_tier_map.get(role_name)

        if not tier:
            # Fallback checks or default handling could go here
            # For now, we warn if it's not a standard system role
            if role_name not in ["default", "planner", "codereviewer"]:
                 # defaulting to LOW_CAPABILITY if unknown is a safety choice,
                 # but for now we leave it alone or warn.
                 pass
            continue

        model_id = tier_models.get(tier)
        if not model_id:
            print(f"  Warning: No model ID found for tier '{tier}' in client '{client_name}'")
            continue

        # Construct role_args
        # We preserve existing args if they are NOT model related, but for strict enforcement
        # we overwrite model args.

        # Simple strategy: clear --model flags, append new one
        new_args = []
        skip_next = False
        current_args = role_data.get("role_args", [])

        for i, arg in enumerate(current_args):
            if skip_next:
                skip_next = False
                continue
            if arg == "--model":
                skip_next = True
                continue
            new_args.append(arg)

        # Add the mandated model
        new_args.extend(["--model", model_id])

        # Special handling for Codex "max" (high tier) to simpler flag if needed
        # But per requirements: "gpt-5.1-codex-max" is the model ID

        role_data["role_args"] = new_args
        updated_count += 1

    # Add metadata
    config["_meta"] = {
        "generated_by": "scripts/generate_client_configs.py",
        "source": "conf/cli_clients/agent-model-tiers.json",
        "tier_mapping_version": tier_data.get("version", "unknown") # Assuming version might be added later
    }

    save_json(config_path, config)
    print(f"  Updated {updated_count} roles in {config_path.name}")

def main():
    if not TIER_MAPPING_FILE.exists():
        print(f"Critical Error: Tier mapping file missing at {TIER_MAPPING_FILE}")
        sys.exit(1)

    tier_data = load_json(TIER_MAPPING_FILE)
    agent_tier_map = get_agent_tier_map(tier_data)

    for client, path in CLIENT_FILES.items():
        update_client_config(client, path, tier_data, agent_tier_map)

    print("\nSuccess: Client configurations regenerated.")

if __name__ == "__main__":
    main()
