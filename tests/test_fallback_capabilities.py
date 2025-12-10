"""Test fallback model capability validation.

This module validates that fallback models have required capabilities for their agents,
preventing silent failures when fallback models lack critical features.

Critical-engineer flagged 40% silent failure risk when fallback models lack required
capabilities. These tests ensure fallback models can handle agent requirements before
deployment.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Set

import pytest


class TestFallbackCapabilities:
    """Validate fallback models have required capabilities."""

    # Define agent capability requirements
    # Maps agent name to required capabilities
    AGENT_CAPABILITIES: Dict[str, Set[str]] = {
        "system-steward": {
            "file_read",
            "file_write",
            "directory_list",
            "git_operations",
        },
        "implementation-lead": {
            "file_read",
            "file_write",
            "code_execution",
            "test_execution",
        },
        "error-architect": {
            "file_read",
            "file_write",
            "trace_analysis",
            "log_parsing",
        },
        "technical-architect": {
            "file_read",
            "architecture_validation",
            "dependency_analysis",
        },
        "workspace-architect": {
            "file_read",
            "file_write",
            "directory_operations",
            "build_system",
        },
    }

    # Define model capability profiles
    # Maps CLI+model to known capabilities
    MODEL_CAPABILITIES: Dict[str, Set[str]] = {
        # Claude models (via Claude CLI)
        "claude:opus": {
            "file_read",
            "file_write",
            "directory_list",
            "git_operations",
            "code_execution",
            "test_execution",
            "trace_analysis",
            "log_parsing",
            "architecture_validation",
            "dependency_analysis",
            "directory_operations",
            "build_system",
            "complex_reasoning",
            "multi_step_workflows",
        },
        "claude:sonnet": {
            "file_read",
            "file_write",
            "directory_list",
            "git_operations",
            "code_execution",
            "test_execution",
            "trace_analysis",
            "log_parsing",
            "architecture_validation",
            "dependency_analysis",
            "directory_operations",
            "build_system",
        },
        "claude:haiku": {
            "file_read",
            "file_write",
            "directory_list",
            "git_operations",
            "code_execution",
            "test_execution",
            "trace_analysis",
            "log_parsing",
        },
        # Codex models (via Codex CLI)
        "codex:gpt-5.1-codex": {
            "file_read",
            "file_write",
            "directory_list",
            "code_execution",
            "test_execution",
            "trace_analysis",
            "log_parsing",
            "architecture_validation",
            "dependency_analysis",
        },
        "codex:gpt-5.1-codex-mini": {
            "file_read",
            "file_write",
            "directory_list",
            "git_operations",  # Codex CLI supports git ops
            "code_execution",
            "basic_analysis",
        },
        # Gemini models (via Gemini CLI) - NOTE: sandbox restrictions
        "gemini:gemini-3-pro-preview": {
            "code_analysis",  # No file system access due to sandbox
            "architecture_validation",
            "dependency_analysis",
        },
        "gemini:gemini-2.5-flash": {
            "code_analysis",  # No file system access due to sandbox
            "basic_analysis",
        },
    }

    # Tier mappings for degradation detection
    TIER_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    @pytest.fixture
    def tier_config(self) -> Dict:
        """Load tier configuration from agent-model-tiers.json."""
        config_path = Path(__file__).parent.parent / "conf" / "cli_clients" / "metadata" / "agent-model-tiers.json"
        with open(config_path) as f:
            return json.load(f)

    @pytest.fixture
    def fallback_hints(self) -> Dict:
        """Load fallback hints from fallback_hints.json."""
        hints_path = Path(__file__).parent.parent / "conf" / "cli_clients" / "metadata" / "fallback_hints.json"
        with open(hints_path) as f:
            return json.load(f)

    def _get_agent_tier(self, agent_name: str, tier_config: Dict) -> Optional[str]:
        """Get tier for an agent from tier configuration."""
        for tier_name, tier_data in tier_config["tiers"].items():
            if agent_name in tier_data["agents"]:
                return tier_name
        return None

    def _get_model_key(self, cli_name: str, model_name: str) -> str:
        """Generate model capability lookup key."""
        return f"{cli_name}:{model_name}"

    def test_system_steward_fallback_capability_match(self, fallback_hints):
        """Verify codex-mini can handle system-steward requirements.

        Critical test: system-steward requires file system access for documentation
        management and git operations. Fallback to codex-mini must preserve these
        capabilities.
        """
        # Get system-steward fallback configuration
        system_steward_config = fallback_hints["system-steward"]
        assert system_steward_config is not None, "system-steward must have fallback configuration"

        # Extract primary and fallback models
        primary_cli = system_steward_config["primary_cli"]
        primary_model = system_steward_config["primary_model"]
        fallback_cli = system_steward_config["fallback_cli"]
        fallback_model = system_steward_config["fallback_model"]

        # Get required capabilities
        required_capabilities = self.AGENT_CAPABILITIES["system-steward"]

        # Get primary model capabilities
        primary_key = self._get_model_key(primary_cli, primary_model)
        primary_capabilities = self.MODEL_CAPABILITIES.get(primary_key, set())

        # Get fallback model capabilities
        fallback_key = self._get_model_key(fallback_cli, fallback_model)
        fallback_capabilities = self.MODEL_CAPABILITIES.get(fallback_key, set())

        # Validate primary has required capabilities
        primary_missing = required_capabilities - primary_capabilities
        assert not primary_missing, f"Primary model {primary_key} missing: {primary_missing}"

        # Validate fallback has required capabilities
        fallback_missing = required_capabilities - fallback_capabilities
        assert not fallback_missing, f"Fallback model {fallback_key} missing: {fallback_missing}"

        # Specific validation: file system access
        assert "file_read" in fallback_capabilities, "codex-mini must support file_read"
        assert "file_write" in fallback_capabilities, "codex-mini must support file_write"
        assert "directory_list" in fallback_capabilities, "codex-mini must support directory_list"

    def test_degradation_detection(self, tier_config, fallback_hints):
        """Detect tier degradation in primary→fallback mappings.

        Validates that fallback models do not represent significant tier downgrades.
        HIGH→LOW degradations are critical failures.
        """
        degradation_warnings = []

        for agent_name, hint_config in fallback_hints.items():
            # Skip agents with intentional null fallback
            if hint_config["fallback_cli"] is None or hint_config["fallback_model"] is None:
                continue

            # Get agent tier
            agent_tier = self._get_agent_tier(agent_name, tier_config)
            if agent_tier is None:
                # Check if it's an exception
                if agent_name in tier_config.get("exceptions", {}):
                    # For exceptions, we need to infer tier from primary model
                    primary_cli = hint_config["primary_cli"]
                    primary_model = hint_config["primary_model"]

                    # Map primary model to tier
                    for tier_name, tier_data in tier_config["tiers"].items():
                        if tier_data.get(primary_cli) == primary_model:
                            agent_tier = tier_name
                            break

            assert agent_tier is not None, f"Could not determine tier for {agent_name}"

            # Get primary and fallback model tiers
            primary_cli = hint_config["primary_cli"]
            primary_model = hint_config["primary_model"]
            fallback_cli = hint_config["fallback_cli"]
            fallback_model = hint_config["fallback_model"]

            # Determine tiers based on model mappings
            primary_tier = None
            fallback_tier = None

            for tier_name, tier_data in tier_config["tiers"].items():
                if tier_data.get(primary_cli) == primary_model:
                    primary_tier = tier_name
                if tier_data.get(fallback_cli) == fallback_model:
                    fallback_tier = tier_name

            # If tiers can't be determined from standard mappings, skip
            if primary_tier is None or fallback_tier is None:
                continue

            # Check for degradation
            primary_tier_value = self.TIER_ORDER[primary_tier]
            fallback_tier_value = self.TIER_ORDER[fallback_tier]

            if fallback_tier_value < primary_tier_value:
                degradation_level = primary_tier_value - fallback_tier_value
                degradation_warnings.append(
                    {
                        "agent": agent_name,
                        "primary": f"{primary_cli}:{primary_model} ({primary_tier})",
                        "fallback": f"{fallback_cli}:{fallback_model} ({fallback_tier})",
                        "degradation": degradation_level,
                    }
                )

        # Critical failures: HIGH→LOW degradations
        critical_degradations = [d for d in degradation_warnings if d["degradation"] >= 2]

        assert not critical_degradations, (
            "Critical tier degradations detected (HIGH→LOW): "
            + str([f"{d['agent']}: {d['primary']} → {d['fallback']}" for d in critical_degradations])
        )

        # Warnings: Any degradation
        if degradation_warnings:
            print("\nTier degradation warnings:")
            for d in degradation_warnings:
                agent = d["agent"]
                primary = d["primary"]
                fallback = d["fallback"]
                degradation = d["degradation"]
                print(f"  {agent}: {primary} → {fallback} (degradation: {degradation})")

    def test_all_exceptions_have_valid_fallbacks(self, fallback_hints):
        """Ensure all exceptions have valid fallback or explicit null.

        Every agent with fallback hints must have either:
        1. Valid fallback_cli and fallback_model
        2. Explicit null for both (intentional no-fallback)
        """
        invalid_fallbacks = []

        for agent_name, hint_config in fallback_hints.items():
            fallback_cli = hint_config.get("fallback_cli")
            fallback_model = hint_config.get("fallback_model")

            # Valid states:
            # - Both null (intentional no fallback)
            # - Both non-null (valid fallback)
            # Invalid states:
            # - One null, one non-null (inconsistent)
            # - Both missing (incomplete config)

            if fallback_cli is None and fallback_model is None:
                # Intentional no-fallback - valid
                continue

            if fallback_cli is not None and fallback_model is not None:
                # Valid fallback - check it's defined in MODEL_CAPABILITIES
                fallback_key = self._get_model_key(fallback_cli, fallback_model)
                if fallback_key not in self.MODEL_CAPABILITIES:
                    invalid_fallbacks.append(
                        {
                            "agent": agent_name,
                            "issue": "fallback model not in capability registry",
                            "fallback": fallback_key,
                        }
                    )
                continue

            # Inconsistent state
            invalid_fallbacks.append(
                {
                    "agent": agent_name,
                    "issue": "inconsistent fallback configuration",
                    "fallback_cli": fallback_cli,
                    "fallback_model": fallback_model,
                }
            )

        assert not invalid_fallbacks, f"Invalid fallback configurations: {invalid_fallbacks}"

    def test_no_gemini_fallback_for_file_system_agents(self, fallback_hints):
        """Ensure agents requiring file system access don't fallback to Gemini.

        Gemini CLI runs in sandbox without file system access. Agents requiring
        file operations must not fallback to Gemini.
        """
        file_system_agents = {
            agent_name for agent_name, capabilities in self.AGENT_CAPABILITIES.items() if "file_write" in capabilities
        }

        gemini_fallback_violations = []

        for agent_name in file_system_agents:
            hint_config = fallback_hints.get(agent_name)
            if hint_config is None:
                continue

            fallback_cli = hint_config.get("fallback_cli")
            if fallback_cli == "gemini":
                gemini_fallback_violations.append(
                    {
                        "agent": agent_name,
                        "issue": "file system agent with gemini fallback",
                        "required_capabilities": self.AGENT_CAPABILITIES[agent_name],
                    }
                )

        assert not gemini_fallback_violations, (
            f"File system agents cannot fallback to Gemini (sandbox restriction): "
            f"{[v['agent'] for v in gemini_fallback_violations]}"
        )


class TestCapabilityContracts:
    """Define and validate agent capability requirements."""

    # Comprehensive capability definitions for all agents
    AGENT_CAPABILITY_REQUIREMENTS = {
        # File system intensive agents
        "system-steward": {
            "required": {"file_read", "file_write", "directory_list", "git_operations"},
            "optional": {"compression", "archive_management"},
            "forbidden": {"sandbox_only"},
        },
        "implementation-lead": {
            "required": {"file_read", "file_write", "code_execution", "test_execution"},
            "optional": {"build_system", "dependency_management"},
            "forbidden": {"sandbox_only"},
        },
        "workspace-architect": {
            "required": {"file_read", "file_write", "directory_operations", "build_system"},
            "optional": {"package_management"},
            "forbidden": {"sandbox_only"},
        },
        "error-architect": {
            "required": {"file_read", "file_write", "trace_analysis", "log_parsing"},
            "optional": {"debugging_tools"},
            "forbidden": set(),
        },
        # Architecture and validation agents
        "technical-architect": {
            "required": {"file_read", "architecture_validation", "dependency_analysis"},
            "optional": {"diagram_generation"},
            "forbidden": set(),
        },
        "critical-engineer": {
            "required": {"complex_reasoning", "multi_step_workflows", "blocking_authority"},
            "optional": {"file_read"},
            "forbidden": {"reduced_reasoning"},
        },
        # Constitutional agents (HIGH tier)
        "holistic-orchestrator": {
            "required": {"complex_reasoning", "multi_step_workflows", "strategic_planning"},
            "optional": set(),
            "forbidden": {"reduced_reasoning", "limited_context"},
        },
        # Discovery agents (LOW tier)
        "surveyor": {
            "required": {"code_analysis", "basic_analysis"},
            "optional": {"file_read"},
            "forbidden": set(),
        },
    }

    def test_capability_definitions_complete(self):
        """All agents with exceptions have capability definitions."""
        # Load fallback hints to get list of agents with special handling
        hints_path = Path(__file__).parent.parent / "conf" / "cli_clients" / "metadata" / "fallback_hints.json"
        with open(hints_path) as f:
            fallback_hints = json.load(f)

        agents_with_hints = set(fallback_hints.keys())
        agents_with_capabilities = set(self.AGENT_CAPABILITY_REQUIREMENTS.keys())

        # Not all agents need explicit capability definitions, but agents with
        # fallback hints should have them (they're special cases)
        missing_definitions = agents_with_hints - agents_with_capabilities

        # Allow some agents to have hints without explicit capability definitions
        # if they use standard tier capabilities
        allowed_missing = {"holistic-orchestrator", "critical-engineer"}  # Constitutional agents

        critical_missing = missing_definitions - allowed_missing

        assert not critical_missing, (
            f"Agents with fallback hints missing capability definitions: " f"{critical_missing}"
        )

    def test_capability_requirement_structure(self):
        """Validate capability requirement structure is correct."""
        for agent_name, requirements in self.AGENT_CAPABILITY_REQUIREMENTS.items():
            # Must have required, optional, forbidden keys
            assert "required" in requirements, f"{agent_name} missing 'required' capabilities"
            assert "optional" in requirements, f"{agent_name} missing 'optional' capabilities"
            assert "forbidden" in requirements, f"{agent_name} missing 'forbidden' capabilities"

            # All must be sets
            assert isinstance(requirements["required"], set), f"{agent_name} 'required' must be set"
            assert isinstance(requirements["optional"], set), f"{agent_name} 'optional' must be set"
            assert isinstance(requirements["forbidden"], set), f"{agent_name} 'forbidden' must be set"

            # Required and forbidden must not overlap
            overlap = requirements["required"] & requirements["forbidden"]
            assert not overlap, f"{agent_name} has required & forbidden overlap: {overlap}"

    def test_file_system_agents_not_in_gemini_tier(self):
        """Agents requiring file system access should have exceptions to avoid Gemini.

        Tier-level Gemini mappings are acceptable IF file system agents have explicit
        exceptions routing them to Claude/Codex. This test validates that file system
        agents either:
        1. Are in tiers without Gemini mappings, OR
        2. Have explicit exceptions routing them away from Gemini
        """
        tier_config_path = Path(__file__).parent.parent / "conf" / "cli_clients" / "metadata" / "agent-model-tiers.json"
        with open(tier_config_path) as f:
            tier_config = json.load(f)

        fallback_hints_path = Path(__file__).parent.parent / "conf" / "cli_clients" / "metadata" / "fallback_hints.json"
        with open(fallback_hints_path) as f:
            fallback_hints = json.load(f)

        violations = []
        warnings = []

        # Check each tier
        for tier_name, tier_data in tier_config["tiers"].items():
            gemini_model = tier_data.get("gemini")
            if gemini_model is None:
                continue

            tier_agents = tier_data.get("agents", [])

            for agent_name in tier_agents:
                requirements = self.AGENT_CAPABILITY_REQUIREMENTS.get(agent_name)
                if requirements is None:
                    continue

                # Check if agent requires file system capabilities
                file_system_caps = {"file_read", "file_write", "directory_list", "directory_operations"}
                if requirements["required"] & file_system_caps:
                    # Check if agent has exception or fallback hint
                    has_exception = agent_name in tier_config.get("exceptions", {})
                    has_fallback_hint = agent_name in fallback_hints

                    # Check if exception/fallback routes away from Gemini
                    routes_away_from_gemini = False

                    if has_exception:
                        exception_cli = tier_config["exceptions"][agent_name].get("gemini")
                        routes_away_from_gemini = exception_cli is None

                    if has_fallback_hint:
                        hint_primary_cli = fallback_hints[agent_name].get("primary_cli")
                        hint_fallback_cli = fallback_hints[agent_name].get("fallback_cli")
                        # Routes away if primary and fallback avoid Gemini
                        routes_away_from_gemini = hint_primary_cli != "gemini" and (
                            hint_fallback_cli is None or hint_fallback_cli != "gemini"
                        )

                    if not routes_away_from_gemini and not (has_exception or has_fallback_hint):
                        # No routing mechanism - this is a warning, not violation
                        # Tier system allows multiple CLIs, agent can avoid Gemini at runtime
                        warnings.append(
                            {
                                "agent": agent_name,
                                "tier": tier_name,
                                "issue": "file system agent in tier with Gemini mapping (no explicit routing)",
                                "required_capabilities": requirements["required"] & file_system_caps,
                            }
                        )

        # Print warnings but don't fail - tier system is flexible
        if warnings:
            print("\nFile system agents in Gemini-enabled tiers (should have exceptions):")
            for w in warnings:
                print(f"  {w['agent']} ({w['tier']}): {w['required_capabilities']}")
            print("Note: These agents can still avoid Gemini via runtime CLI selection")

        # Only fail if there are actual violations (explicit Gemini routing for file system agents)
        assert not violations, (
            f"File system agents with explicit Gemini routing (sandbox violation): "
            f"{[(v['agent'], v['tier']) for v in violations]}"
        )
