# MCP Server Process Cleanup Protocol

**Date:** 2025-12-10
**Source Session:** f29cb14c (MCP Audit)
**Purpose:** Operational runbook for managing stale server processes
**Status:** ✅ ACTIVE (discovered during connection debugging)

---

## Overview

The HestAI MCP Server is a long-running process. Over time, stale instances accumulate due to:
- Restart cycles during development
- Crashed processes that don't clean up
- Multiple developer sessions
- Extended debugging sessions

This protocol prevents socket conflicts and connection failures.

---

## Problem Statement

**What Happened (Session f29cb14c):**

- **Tuesday:** Server started (PID 24534)
- **Monday:** Multiple restarts created accumulation
- **Today:** 5 stale processes running simultaneously:

```
PID 24534  (Tuesday 05:00 AM)   ← STALE
PID 6325   (Monday 23:00)        ← STALE
PID 1637   (Monday 14:30)        ← STALE
PID 805    (Earlier)             ← STALE
PID 79999  (Today 14:36)         ← CURRENT
```

**Impact:**
- Port conflicts (multiple processes trying to use same socket)
- Claude Code client connecting to stale/dead instances
- "Failed to reconnect" errors
- MCP tools unavailable

**Root Cause:** No automatic process reaping during restart cycles

---

## Quick Fix (Immediate)

### Kill All Stale Instances

```bash
# Kill all hestai-mcp-server processes (including stale ones)
pkill -f "hestai-mcp-server|mcp.*server"

# Verify all killed
pgrep -fl hestai-mcp-server
# Should return: (no output)
```

### Restart Fresh

```bash
# Start a clean server instance
cd /Volumes/HestAI-Tools/hestai-mcp-server
./run-server.sh

# Verify startup
tail -f logs/mcp_server.log
# Should show: "MCP server running on..."
```

---

## Prevention (Ongoing)

### Automatic Cleanup During Restarts

**Add to your development workflow:**

```bash
#!/bin/bash
# Script: mcp-restart.sh

echo "Cleaning stale MCP processes..."
pkill -f "hestai-mcp-server|mcp.*server"

echo "Waiting for processes to exit..."
sleep 2

echo "Verifying cleanup..."
if pgrep -f "mcp.*server" > /dev/null; then
  echo "⚠️  WARNING: Some processes still running"
  pgrep -fl "mcp.*server"
  pkill -9 -f "hestai-mcp-server|mcp.*server"
else
  echo "✅ All stale processes cleaned"
fi

echo "Starting fresh server..."
cd /Volumes/HestAI-Tools/hestai-mcp-server
./run-server.sh
```

### Alias for Easy Access

Add to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
alias mcp-clean='pkill -f "hestai-mcp-server|mcp.*server" && sleep 1 && cd /Volumes/HestAI-Tools/hestai-mcp-server && ./run-server.sh'
```

Then use:
```bash
mcp-clean
```

---

## Automated Cleanup (Scheduled)

### Quarterly Cron Job

```bash
# Add to crontab (run quarterly on Monday 2 AM)
# crontab -e

# Kill stale MCP processes (older than 24 hours)
0 2 * * 1 (pkill -f "hestai-mcp-server|mcp.*server" 2>/dev/null; sleep 1; cd /Volumes/HestAI-Tools/hestai-mcp-server && ./run-server.sh > logs/restart-$(date +\%Y\%m\%d).log 2>&1)
```

Or use macOS LaunchAgent:

```bash
# Create: ~/Library/LaunchAgents/com.hestai.mcp.cleanup.plist

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hestai.mcp.cleanup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>pkill -f "hestai-mcp-server|mcp.*server"; sleep 1; cd /Volumes/HestAI-Tools/hestai-mcp-server && ./run-server.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Weekday</key>
            <integer>1</integer>
            <key>Hour</key>
            <integer>2</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardErrorPath</key>
    <string>/tmp/hestai-mcp-cleanup.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/hestai-mcp-cleanup.log</string>
</dict>
</plist>

# Then load it:
launchctl load ~/Library/LaunchAgents/com.hestai.mcp.cleanup.plist
```

---

## Monitoring & Detection

### Detect Accumulation

```bash
# Count how many MCP processes are running
pgrep -fc "hestai-mcp-server"

# Expected: 1 (or 0 if stopped)
# Alert if: > 2 (indicates accumulation)
```

### Add to Your Monitoring

Create a simple health check script:

```bash
#!/bin/bash
# Script: mcp-health-check.sh

MCP_COUNT=$(pgrep -fc "hestai-mcp-server")

if [ "$MCP_COUNT" -gt 2 ]; then
  echo "⚠️  ALERT: $MCP_COUNT MCP server processes detected (expected: 1)"
  echo "Run: pkill -f 'hestai-mcp-server|mcp.*server'"
  exit 1
elif [ "$MCP_COUNT" -eq 0 ]; then
  echo "⚠️  ALERT: No MCP server running"
  exit 1
else
  echo "✅ MCP server healthy ($MCP_COUNT process)"
  exit 0
fi
```

Run before sessions:
```bash
./mcp-health-check.sh || ./mcp-restart.sh
```

---

## Integration with Claude Code Startup

### Auto-Cleanup on Session Start

Add to `.claude/hooks/startup.sh` (if you have startup hooks):

```bash
#!/bin/bash
# Cleanup stale MCP processes on Claude Code startup

STALE_COUNT=$(pgrep -fc "hestai-mcp-server")

if [ "$STALE_COUNT" -gt 1 ]; then
  echo "🧹 Cleaning $STALE_COUNT stale MCP processes..."
  pkill -f "hestai-mcp-server|mcp.*server"
  sleep 2

  # Restart fresh
  cd /Volumes/HestAI-Tools/hestai-mcp-server
  nohup ./run-server.sh > logs/mcp_server.log 2>&1 &
  echo "✅ Fresh MCP server started"
fi
```

---

## Process Lifecycle Management

### Development Workflow Best Practices

```
1. START SESSION
   ├── Run: mcp-health-check.sh
   ├── If stale detected → Run: mcp-restart.sh
   └── Verify: tail -f logs/mcp_server.log shows "Ready"

2. ACTIVE SESSION
   ├── Monitor: pgrep -fl hestai-mcp-server (should show 1 process)
   └── If frozen: Run: mcp-restart.sh

3. END SESSION
   ├── Optional: pkill -f hestai-mcp-server
   └── Or: Leave running for next session
```

---

## Troubleshooting

### Server Won't Stop

```bash
# Force kill if normal kill doesn't work
pkill -9 -f "hestai-mcp-server"

# Or identify specific PID
pgrep -fl hestai-mcp-server
kill -9 <PID>
```

### Port Already in Use

If you see: `Address already in use` error

```bash
# Find what's using the port (assuming default port 8080)
lsof -i :8080

# Kill the process
kill <PID>

# Or use the nuclear option
pkill -9 -f hestai-mcp-server
```

### Socket Errors After Restart

```bash
# Clear any socket/temp files
rm -f ~/.hestai/sessions/active/*

# Restart server
./run-server.sh
```

---

## Monitoring Metrics

### Key Metrics to Track

```
1. Process Count
   - Current: Should always be 0 or 1
   - Alert threshold: > 2

2. Uptime
   - Expected: Days/weeks (until intentional restart)
   - Alert if: Restarting more than weekly

3. Memory Usage
   - Check: pid=$(pgrep -f hestai-mcp-server) && [ -n "$pid" ] && ps -o rss= -p $pid
   - Alert if: > 500MB (indicates memory leak)

4. Log Growth
   - Check: du -sh logs/
   - Rotate weekly to prevent disk fill

5. Connection Failures
   - Check: grep "Failed to reconnect" logs/
   - If > 5/hour: Probably stale processes
```

---

## Log Locations

```
/Volumes/HestAI-Tools/hestai-mcp-server/
├── logs/
│   ├── mcp_server.log        (main server log)
│   ├── mcp_activity.log      (tool calls only)
│   └── restart-YYYYMMDD.log  (restart logs from cron)
├── .env                       (configuration)
└── run-server.sh              (startup script)
```

### Log Inspection

```bash
# Recent startup messages
tail -50 logs/mcp_server.log | grep -E "Server|listening|Ready"

# Check for errors
tail -50 logs/mcp_server.log | grep -i error

# Monitor active tool usage
tail -f logs/mcp_activity.log | grep "TOOL_CALL"
```

---

## Escalation Path

| Situation | Action | Contact |
|-----------|--------|---------|
| Stale processes > 5 | Run cleanup script | None (automated) |
| Server won't restart | Check logs, verify .env | implementation-lead |
| Port conflict | Kill process, restart | holistic-orchestrator |
| Memory leak detected | Restart server, monitor | principal-engineer |
| Frequent crashes | Review logs, debug | critical-engineer |

---

## Recommendations

1. **Implement Auto-Cleanup Hook** - Kill stale processes before Claude Code startup
2. **Add Process Count Alert** - Alert if > 2 processes detected
3. **Quarterly Restart** - Schedule via cron job to refresh process pool
4. **Log Rotation** - Prevent log files from consuming all disk space
5. **Health Check Command** - Make it easy for developers to verify server health

---

## References

- Source Session: f29cb14c (MCP Audit 2025-12-10)
- Related: `.hestai/reports/801-REPORT-MCP-AUDIT-SESSION-F29CB14C.md`
- Related: `.hestai/workflow/MCP-TOOL-DEPENDENCY-MATRIX.md`

---

**Protocol Created:** 2025-12-10
**Owner:** system-steward + operations team
**Last Updated:** 2025-12-10
**Review Frequency:** Quarterly
