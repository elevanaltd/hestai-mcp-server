# CLI Clients Configuration

This directory contains configuration files for the HestAI MCP Server's CLI integration tool (`clink`), which enables delegation to external AI CLIs.

## Architecture Overview

```
conf/
├── agent-routing.yaml           # Source of truth for per-agent routing
└── cli_clients/
    ├── claude.json              # Claude CLI configuration (generated)
    ├── codex.json               # Codex CLI configuration (generated)
    ├── gemini.json              # Gemini CLI configuration (generated)
    ├── metadata/
    │   ├── agent-model-tiers.json   # Legacy tier mappings (deprecated)
    │   └── fallback_hints.json      # Legacy fallback hints (deprecated)
    └── README.md                    # This file
```

## File Purposes

### Client Configuration Files (`{cli_name}.json`)

Each client file defines:
- **`name`**: CLI identifier (matches filename)
- **`command`**: Executable command
- **`additional_args`**: Global CLI arguments (model selection, permissions)
- **`env`**: Environment variable overrides
- **`roles`**: Agent-to-prompt mappings with per-role arguments

### Source of Truth: `conf/agent-routing.yaml`

The **agent-routing.yaml** file (in the parent `conf/` directory) is the single source of truth for agent routing configuration. Each agent is configured individually with:

- **CLI-specific models**: `claude`, `codex`, `gemini` - which model to use on each CLI
- **Primary CLI**: `primary` - preferred CLI for this agent
- **Reasoning effort**: `reasoning_effort` - Codex-specific (high/medium/low)
- **Prompt overrides**: `prompt_override` - CLI-specific prompt file mapping
- **Notes**: `notes` - Documentation about agent capabilities

Example agent configuration:
```yaml
critical-engineer:
  claude: opus
  codex: gpt-5.1-codex      # Now available on Codex!
  gemini: gemini-3-pro-preview
  primary: claude
  reasoning_effort: high
  notes: "GO/NO-GO authority - prefers Claude Opus, but works on all CLIs"
```

### Metadata Files (Legacy - Deprecated)

**`metadata/agent-model-tiers.json`** - Legacy tier-based mapping (kept for reference)
**`metadata/fallback_hints.json`** - Legacy fallback hints (kept for reference)

These files are deprecated. Use `conf/agent-routing.yaml` instead.

## Per-Agent Configuration

Every agent can now be configured individually. Use `null` to exclude an agent from a specific CLI:

```yaml
holistic-orchestrator:
  claude: opus
  codex: null     # Excluded from Codex
  gemini: null    # Excluded from Gemini
  primary: claude
  notes: "Constitutional authority - Claude only"
```

## Update Workflow

1. **Edit the source of truth**: Modify `conf/agent-routing.yaml`
2. **Run the generator**: `python scripts/generate_client_configs.py`
3. **Verify changes**: `python scripts/generate_client_configs.py --check`
4. **Commit all changes**: Both YAML and generated JSON configs

### Generator Commands

```bash
# Generate/update all configs from agent-routing.yaml
python scripts/generate_client_configs.py

# Dry-run (preview changes without writing)
python scripts/generate_client_configs.py --dry-run

# CI validation (fails if configs out of sync)
python scripts/generate_client_configs.py --check

# Process specific CLI only
python scripts/generate_client_configs.py --cli claude codex
```

## Agent Availability

With the new per-agent routing system, most agents are available on all CLIs:

- **Claude**: Full coverage with per-agent model selection (opus/sonnet/haiku)
- **Codex**: Full coverage including previously excluded agents (with reasoning_effort)
- **Gemini**: Full coverage for all non-excluded agents

Only agents with explicit `null` values (like `holistic-orchestrator`) are excluded from specific CLIs.

## Adding a New Agent

1. Add agent configuration to `conf/agent-routing.yaml`:
   ```yaml
   new-agent-name:
     claude: sonnet
     codex: gpt-5.1-codex
     gemini: gemini-3-pro-preview
     primary: claude
     notes: "Description of agent purpose"
   ```

2. Create system prompt: `systemprompts/clink/new-agent-name.txt`

3. Run generator: `python scripts/generate_client_configs.py`

4. If agent needs CLI-specific prompts, add `prompt_override`:
   ```yaml
   new-agent-name:
     ...
     prompt_override:
       codex: custom_codex_prompt.txt
   ```

## Reasoning Effort (Codex-specific)

Codex supports `model_reasoning_effort` levels (high/medium/low). Configure per-agent in `agent-routing.yaml`:

```yaml
code-review-specialist:
  claude: sonnet
  codex: gpt-5.1-codex
  gemini: gemini-3-pro-preview
  primary: codex
  reasoning_effort: high  # Codex will use high reasoning effort
```

Available levels: `high`, `medium`, `low`

## Troubleshooting

**"Role not found" errors**
- Verify role exists in appropriate `{cli_name}.json`
- Check if agent is excluded by tier (`null` model value)
- Ensure system prompt exists at `prompt_path`

**Codex "Not inside trusted directory"**
- `codex.json` includes `--skip-git-repo-check` flag
- If issue persists, restart MCP session after config changes

**Gemini sandbox limitations**
- Some agents (e.g., system-steward) are excluded from Gemini
- Check `exceptions` section for `"gemini": null` entries
