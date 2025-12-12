#!/usr/bin/env python3
"""
Generate CLI client configurations from agent-routing.yaml.

Minimal Implementation Principle (MIP) compliant:
- Only generates what's needed from YAML spec
- No feature creep beyond YAML requirements
- Essential code only

Usage:
    python scripts/generate_client_configs.py
"""

import json
from pathlib import Path

import yaml


def get_prompt_path(agent_name: str, agent_config: dict, cli_name: str) -> str:
    """Get prompt path with override support."""
    prompt_override = agent_config.get("prompt_override", {})
    if cli_name in prompt_override:
        return f"systemprompts/clink/{prompt_override[cli_name]}"
    return f"systemprompts/clink/{agent_name}.txt"


def load_yaml(yaml_path: str) -> dict:
    """Load YAML configuration file."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with open(path) as f:
        return yaml.safe_load(f)


def generate_claude(config: dict) -> dict:
    """Generate Claude CLI configuration from YAML."""
    result = {
        "name": "claude",
        "command": "claude",
        "additional_args": ["--permission-mode", "bypassPermissions"],
        "env": {},
        "roles": {},
        "_generated_by": "scripts/generate_client_configs.py",
        "_tier_mapping_version": "1.0.0",
    }

    for agent_name, agent_config in config["agents"].items():
        claude_model = agent_config.get("claude")

        if claude_model is None:
            continue

        result["roles"][agent_name] = {
            "prompt_path": get_prompt_path(agent_name, agent_config, "claude"),
            "role_args": ["--model", claude_model],
        }

    return result


def generate_codex(config: dict) -> dict:
    """Generate Codex CLI configuration from YAML."""
    result = {
        "name": "codex",
        "command": "codex",
        "timeout_seconds": 900,
        "additional_args": [
            "--model",
            "gpt-5.1-codex",
            "--json",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
        ],
        "env": {},
        "roles": {},
        "_generated_by": "scripts/generate_client_configs.py",
        "_tier_mapping_version": "1.0.0",
    }

    for agent_name, agent_config in config["agents"].items():
        codex_model = agent_config.get("codex")

        if codex_model is None:
            continue

        role_args = []
        reasoning_effort = agent_config.get("reasoning_effort")
        if reasoning_effort:
            role_args = ["-c", f"model_reasoning_effort={reasoning_effort}"]

        result["roles"][agent_name] = {
            "prompt_path": get_prompt_path(agent_name, agent_config, "codex"),
            "role_args": role_args,
        }

    return result


def generate_gemini(config: dict) -> dict:
    """Generate Gemini CLI configuration from YAML."""
    result = {
        "name": "gemini",
        "command": "gemini",
        "additional_args": [],
        "env": {},
        "roles": {},
        "_generated_by": "scripts/generate_client_configs.py",
        "_tier_mapping_version": "1.0.0",
    }

    for agent_name, agent_config in config["agents"].items():
        gemini_model = agent_config.get("gemini")

        if gemini_model is None:
            continue

        result["roles"][agent_name] = {
            "prompt_path": get_prompt_path(agent_name, agent_config, "gemini"),
            "role_args": ["--model", gemini_model],
        }

    return result


def main():
    """Generate all CLI client configurations from agent-routing.yaml."""
    # Locate files
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    yaml_path = repo_root / "conf" / "agent-routing.yaml"
    output_dir = repo_root / "conf" / "cli_clients"

    # Load YAML
    print(f"Loading {yaml_path}")
    config = load_yaml(str(yaml_path))

    # Generate configs
    print("Generating Claude config...")
    claude_config = generate_claude(config)

    print("Generating Codex config...")
    codex_config = generate_codex(config)

    print("Generating Gemini config...")
    gemini_config = generate_gemini(config)

    # Write configs
    print("Writing configurations...")
    configs = {
        "claude.json": claude_config,
        "codex.json": codex_config,
        "gemini.json": gemini_config,
    }

    for filename, cfg in configs.items():
        output_path = output_dir / filename
        with open(output_path, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"  ✓ {output_path}")

    print("\nGeneration complete!")
    print(f"  Claude: {len(claude_config['roles'])} roles")
    print(f"  Codex: {len(codex_config['roles'])} roles")
    print(f"  Gemini: {len(gemini_config['roles'])} roles")


if __name__ == "__main__":
    main()
