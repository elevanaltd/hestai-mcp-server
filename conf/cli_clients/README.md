# CLI Clients Configuration

This directory contains configuration files for the HestAI MCP Server's CLI integration tool (`clink`), which enables delegation to external AI CLIs.

## Architecture Overview

```
conf/cli_clients/
├── claude.json              # Claude CLI configuration (48 roles)
├── codex.json               # Codex CLI configuration (34 roles)
├── gemini.json              # Gemini CLI configuration (36 roles)
├── metadata/
│   ├── agent-model-tiers.json   # Source of truth for tier mappings
│   └── fallback_hints.json      # Generated: primary/fallback CLI hints
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

### Metadata Files

**`agent-model-tiers.json`** (Source of Truth)
- Defines three tiers: HIGH, MEDIUM, LOW
- Maps agents to appropriate models per CLI
- Contains exceptions for special cases
- Includes fallback hints and reasoning effort mappings

**`fallback_hints.json`** (Generated)
- Extracted from `agent-model-tiers.json` by the generator script
- Provides primary/fallback CLI routing for specific agents
- **Do not edit directly** - modify `agent-model-tiers.json` instead

## Tier System

| Tier | Claude Model | Gemini Model | Codex Model | Purpose |
|------|-------------|--------------|-------------|---------|
| HIGH | opus | null | null | Constitutional authority, GO/NO-GO decisions |
| MEDIUM | sonnet | gemini-3-pro-preview | gpt-5.2 | Implementation, domain specialists |
| LOW | haiku | gemini-3-pro-preview | gpt-5.2 | Exploration, research, advisory |

**Note**: HIGH-tier agents (holistic-orchestrator, critical-engineer, etc.) are Claude-only by design. Their `gemini: null` and `codex: null` values indicate intentional exclusion, not missing configuration.

## Update Workflow

1. **Edit the source of truth**: Modify `metadata/agent-model-tiers.json`
2. **Run the generator**: `python scripts/generate_client_configs.py`
3. **Verify changes**: `python scripts/generate_client_configs.py --check`
4. **Commit all changes**: Both metadata and generated configs

### Generator Commands

```bash
# Generate/update all configs from tier mapping
python scripts/generate_client_configs.py

# Dry-run (preview changes without writing)
python scripts/generate_client_configs.py --dry-run

# CI validation (fails if configs out of sync)
python scripts/generate_client_configs.py --check

# Process specific CLI only
python scripts/generate_client_configs.py --cli claude codex
```

## Role Coverage by CLI

- **Claude**: Most complete coverage (48 roles) - supports all tiers
- **Codex**: Medium coverage (34 roles) - MEDIUM and LOW tiers only
- **Gemini**: Medium coverage (36 roles) - MEDIUM and LOW tiers only

This asymmetry is intentional: HIGH-tier agents require Claude's constitutional reasoning capabilities.

## Adding a New Agent

1. Add agent to appropriate tier in `metadata/agent-model-tiers.json`:
   ```json
   "tiers": {
     "MEDIUM": {
       "agents": [..., "new-agent-name"]
     }
   }
   ```

2. Create system prompt: `systemprompts/clink/new-agent-name.txt`

3. Run generator: `python scripts/generate_client_configs.py`

4. If agent needs special handling, add to `exceptions` section

## Exception Handling

Some agents require special CLI routing. Define exceptions in `agent-model-tiers.json`:

```json
"exceptions": {
  "system-steward": {
    "claude": "haiku",
    "gemini": null,      // Excluded: sandbox limitations
    "codex": "gpt-5.2",
    "reason": "Requires file system access - avoids Gemini sandbox"
  }
}
```

## Reasoning Effort (Codex-specific)

Codex supports `model_reasoning_effort` levels (low/medium/high/extra-high). Configure in:

```json
"reasoning_effort_mappings": {
  "high": ["code-review-specialist", "critical-engineer"],
  "medium": ["holistic-orchestrator", "technical-architect"],
  "low": []
}
```

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
