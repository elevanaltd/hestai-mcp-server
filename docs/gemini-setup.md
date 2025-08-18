# Gemini CLI Setup

> **Note**: While HestAI MCP Server connects successfully to Gemini CLI, tool invocation is not working
> correctly yet. We'll update this guide once the integration is fully functional.

This guide explains how to configure HestAI MCP Server to work with [Gemini CLI](https://github.com/google-gemini/gemini-cli).

## Prerequisites

- HestAI MCP Server installed and configured
- Gemini CLI installed
- At least one API key configured in your `.env` file

## Configuration

1. Edit `~/.gemini/settings.json` and add:

```json
{
  "mcpServers": {
    "hestai": {
      "command": "/path/to/hestai-mcp-server/hestai-mcp-server"
    }
  }
}
```

2. Replace `/path/to/hestai-mcp-server` with your actual HestAI installation path.

3. If the `hestai-mcp-server` wrapper script doesn't exist, create it:

```bash
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
exec .hestai_venv/bin/python server.py "$@"
```

Then make it executable: `chmod +x hestai-mcp-server`

4. Restart Gemini CLI.

All 15 HestAI tools are now available in your Gemini CLI session.