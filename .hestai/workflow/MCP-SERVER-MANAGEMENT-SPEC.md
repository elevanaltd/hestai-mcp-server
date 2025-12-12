# MCP Server Management Slash Commands - Design Specification

## Overview

Enable users to list, enable, and disable MCP servers per-project/worktree via simple slash commands.

## Problem Statement

Currently, users must:
1. Manually edit `~/.claude.json`
2. Navigate to the correct project path key
3. Add/remove server names from `disabledMcpServers` array
4. Restart Claude session

This is error-prone and requires understanding the JSON structure.

## Solution

Three slash commands + one Node.js utility script:
- `/mcp-servers list` - Shows all servers and their enabled/disabled status
- `/mcp-servers disable {name}` - Disables a server for current path
- `/mcp-servers enable {name}` - Re-enables a server for current path

## Technical Architecture

### ~/.claude.json Structure

```json
{
  "mcpServers": {
    "hestai": { ... },
    "supabase": { ... },
    "repomix": { ... }
  },
  "projects": {
    "/Volumes/HestAI": {
      "disabledMcpServers": ["supabase", "repomix"]
    },
    "/Volumes/HestAI-Tools/project": {
      "disabledMcpServers": []
    }
  }
}
```

### Key Mechanics

1. **Server enumeration**: Read `mcpServers` keys at root level
2. **Path resolution**: Use current working directory to find/create project entry
3. **Enable/disable**: Add/remove from `disabledMcpServers` array
4. **Atomic writes**: Read → modify → write with backup

### Node.js Script: `mcp-server-manager.mjs`

Location: `~/.claude/bin/mcp-server-manager.mjs`

```javascript
#!/usr/bin/env node
/**
 * MCP Server Manager
 * Manages disabledMcpServers in ~/.claude.json per project path
 */

import { readFileSync, writeFileSync, copyFileSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

const CLAUDE_JSON_PATH = join(homedir(), '.claude.json');

function readClaudeJson() {
  return JSON.parse(readFileSync(CLAUDE_JSON_PATH, 'utf8'));
}

function writeClaudeJson(data) {
  // Backup before write
  const backupPath = CLAUDE_JSON_PATH + '.backup';
  copyFileSync(CLAUDE_JSON_PATH, backupPath);
  writeFileSync(CLAUDE_JSON_PATH, JSON.stringify(data, null, 2));
}

function getProjectEntry(data, path) {
  if (!data.projects) data.projects = {};
  if (!data.projects[path]) {
    data.projects[path] = {
      allowedTools: [],
      mcpServers: {},
      disabledMcpServers: []
    };
  }
  if (!data.projects[path].disabledMcpServers) {
    data.projects[path].disabledMcpServers = [];
  }
  return data.projects[path];
}

function list(workingDir) {
  const data = readClaudeJson();
  const allServers = Object.keys(data.mcpServers || {});
  const project = data.projects?.[workingDir] || {};
  const disabled = project.disabledMcpServers || [];

  console.log('MCP SERVERS');
  console.log('===========');
  console.log(`Path: ${workingDir}`);
  console.log('');

  for (const server of allServers.sort()) {
    const status = disabled.includes(server) ? '[ ] DISABLED' : '[x] ENABLED';
    console.log(`  ${status}  ${server}`);
  }

  console.log('');
  console.log(`Total: ${allServers.length} servers (${allServers.length - disabled.length} enabled)`);
}

function disable(workingDir, serverName) {
  const data = readClaudeJson();

  // Validate server exists
  if (!data.mcpServers?.[serverName]) {
    console.error(`Error: Server "${serverName}" not found in mcpServers`);
    console.log('Available servers:', Object.keys(data.mcpServers || {}).join(', '));
    process.exit(1);
  }

  const project = getProjectEntry(data, workingDir);

  if (project.disabledMcpServers.includes(serverName)) {
    console.log(`Server "${serverName}" is already disabled for ${workingDir}`);
    return;
  }

  project.disabledMcpServers.push(serverName);
  writeClaudeJson(data);

  console.log(`Disabled "${serverName}" for ${workingDir}`);
  console.log('Restart Claude session to apply changes.');
}

function enable(workingDir, serverName) {
  const data = readClaudeJson();

  // Validate server exists
  if (!data.mcpServers?.[serverName]) {
    console.error(`Error: Server "${serverName}" not found in mcpServers`);
    console.log('Available servers:', Object.keys(data.mcpServers || {}).join(', '));
    process.exit(1);
  }

  const project = getProjectEntry(data, workingDir);

  const idx = project.disabledMcpServers.indexOf(serverName);
  if (idx === -1) {
    console.log(`Server "${serverName}" is already enabled for ${workingDir}`);
    return;
  }

  project.disabledMcpServers.splice(idx, 1);
  writeClaudeJson(data);

  console.log(`Enabled "${serverName}" for ${workingDir}`);
  console.log('Restart Claude session to apply changes.');
}

// Main
const [,, command, arg] = process.argv;
const workingDir = process.env.PWD || process.cwd();

switch (command) {
  case 'list':
    list(workingDir);
    break;
  case 'disable':
    if (!arg) {
      console.error('Usage: mcp-server-manager.mjs disable <server-name>');
      process.exit(1);
    }
    disable(workingDir, arg);
    break;
  case 'enable':
    if (!arg) {
      console.error('Usage: mcp-server-manager.mjs enable <server-name>');
      process.exit(1);
    }
    enable(workingDir, arg);
    break;
  default:
    console.log('MCP Server Manager');
    console.log('Usage:');
    console.log('  mcp-server-manager.mjs list           - List all servers');
    console.log('  mcp-server-manager.mjs disable <name> - Disable server');
    console.log('  mcp-server-manager.mjs enable <name>  - Enable server');
    process.exit(command ? 1 : 0);
}
```

### Slash Command: `mcp-servers.md`

Location: `~/.claude/commands/mcp-servers.md`

```markdown
# MCP Server Management

Manage MCP servers for the current project/worktree.

## Usage

```
/mcp-servers [list|disable|enable] [server-name]
```

**Commands:**
- `list` (default) - Show all MCP servers and their status
- `disable <name>` - Disable a server for this path
- `enable <name>` - Re-enable a server for this path

---

## EXECUTION PROTOCOL

When this command is invoked, execute the Node.js script:

### Parse Arguments
```bash
ACTION="${1:-list}"
SERVER="${2:-}"
SCRIPT="$HOME/.claude/bin/mcp-server-manager.mjs"
```

### Execute Command
```bash
node "$SCRIPT" "$ACTION" "$SERVER"
```

### Post-Execution
If disable or enable was executed:
1. Inform user: "Restart Claude session for changes to take effect"
2. Optionally run `/mcp-servers list` to show new state

---

## EXAMPLES

```bash
# List all servers
/mcp-servers
/mcp-servers list

# Disable supabase for current project
/mcp-servers disable supabase

# Re-enable supabase
/mcp-servers enable supabase
```

---

## CONTEXT STEWARD INTEGRATION (Future)

The Context Steward could invoke this script during `/load`:
1. Read project's `.hestai/config.yaml` for MCP preferences
2. Auto-enable/disable servers based on project needs
3. Example config:
   ```yaml
   mcp:
     required: [hestai]
     optional: [supabase, smartsuite]
     disabled: [chrome-devtools, repomix]
   ```

This allows project-specific MCP configuration without manual intervention.
```

## Implementation Checklist

- [ ] Create `~/.claude/bin/` directory if not exists
- [ ] Write `mcp-server-manager.mjs` script
- [ ] Make script executable (`chmod +x`)
- [ ] Write `~/.claude/commands/mcp-servers.md` slash command
- [ ] Test: `/mcp-servers list`
- [ ] Test: `/mcp-servers disable supabase`
- [ ] Test: `/mcp-servers enable supabase`
- [ ] Verify JSON integrity after modifications
- [ ] Document in CLAUDE.md if needed

## Security Considerations

1. **Atomic writes**: Always backup before modifying ~/.claude.json
2. **Validation**: Only allow known server names (from mcpServers keys)
3. **No code injection**: Server names validated against existing keys only
4. **Path isolation**: Each project path has independent settings

## Future Enhancements

1. **Bulk operations**: `/mcp-servers disable-all`, `/mcp-servers enable-all`
2. **Presets**: `/mcp-servers preset minimal` (only hestai)
3. **Context Steward integration**: Auto-configure on `/load`
4. **MCP tool**: Add as MCP tool for programmatic access
