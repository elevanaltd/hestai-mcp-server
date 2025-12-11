# Model Swap Hook Research Report

**Date**: 2025-12-11
**Session**: System Steward Investigation
**Status**: Research Complete - Actionable Findings

---

## Executive Summary

Investigation into tracking `/model` command usage via Claude Code hooks. Key finding: **UserPromptSubmit hooks cannot intercept built-in CLI commands**, but model information **is reliably recorded in session JSONL files**.

---

## What We Attempted

### Initial Approach: UserPromptSubmit Hook

Created `model-swap-hook.sh` to detect `/model` commands:

```bash
# Pattern attempted
if echo "$PROMPT" | grep -q "^/model"; then
  # Log model change
fi
```

**Result**: Hook never triggered for `/model` commands.

### Why It Failed

Built-in slash commands (`/model`, `/help`, `/clear`, etc.) are processed at the **CLI layer** before reaching the hook system:

```
USER INPUT
    │
    ├── /model haiku ──────► CLI LAYER (intercepted here)
    │                            │
    │                            ▼
    │                       Model changed
    │                            │
    └── "hello world" ─────► HOOK LAYER (UserPromptSubmit)
                                 │
                                 ▼
                            AI PROCESSING
```

**Conclusion**: Hooks only receive prompts destined for the AI, not CLI commands.

---

## What IS Possible

### Source of Truth: Session JSONL Files

Location: `~/.claude/projects/{project-hash}/{session-id}.jsonl`

Model information is recorded in **three reliable places**:

#### 1. Command Invocation (User Type)
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "<command-name>/model</command-name>\n<command-message>model</command-message>\n<command-args>haiku</command-args>"
  },
  "timestamp": "2025-12-11T13:39:01.865Z"
}
```

#### 2. Confirmation Message (User Type)
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "<local-command-stdout>Set model to haiku (claude-haiku-4-5-20251001)</local-command-stdout>"
  },
  "timestamp": "2025-12-11T13:39:01.865Z"
}
```

#### 3. Assistant Response Model Field
```json
{
  "type": "assistant",
  "message": {
    "model": "claude-haiku-4-5-20251001",
    "role": "assistant",
    "id": "msg_01QyrcC2atYeTT9gNXstkKbN"
  },
  "timestamp": "2025-12-11T13:39:09.199Z"
}
```

### Extraction Patterns

**Regex for confirmation messages:**
```regex
Set model to.*?\((claude-[^)]+)\)
```

**JSON path for assistant model:**
```
.message.model (where type == "assistant")
```

**Full model identifiers found:**
- `claude-opus-4-5-20251101`
- `claude-haiku-4-5-20251001`
- `claude-sonnet-4-20250514` (presumed)
- `<synthetic>` (system-generated no-op messages)

---

## Hook Events Analysis

### Available Hook Events

| Event | Can Intercept /model? | Notes |
|-------|----------------------|-------|
| `UserPromptSubmit` | **NO** | Only receives AI-bound prompts |
| `SessionStart` | **NO** | Runs before any commands |
| `SessionEnd` | **MAYBE** | Could read JSONL on exit |
| `Stop` | **MAYBE** | Runs after AI response |
| `PreToolUse` | **NO** | Tool-specific only |
| `PostToolUse` | **NO** | Tool-specific only |
| `Notification` | **NO** | Notification events only |

### Potential Approaches

#### Approach A: SessionEnd/Stop Hook (Batch Processing)

```bash
# In SessionEnd hook
JSONL_PATH="$TRANSCRIPT_PATH"
grep "Set model to" "$JSONL_PATH" | extract_models >> model-history.log
```

**Pros**: Reliable, complete session data
**Cons**: Not real-time, only on session end

#### Approach B: Periodic JSONL Scanner (Background Process)

```bash
# Run as cron or background process
while true; do
  for jsonl in ~/.claude/projects/*/*.jsonl; do
    # Extract new model swaps since last check
    tail -n +$LAST_LINE "$jsonl" | grep "Set model to"
  done
  sleep 60
done
```

**Pros**: Near real-time
**Cons**: External to Claude Code, resource overhead

#### Approach C: Custom Command Wrapper

Create `/m` command that wraps `/model`:

```markdown
# ~/.claude/commands/m.md
---
description: Switch model and log the change
---
Please run `/model $ARGUMENTS` for me. I'll track this model change.
```

**Pros**: Hooks can intercept custom commands
**Cons**: Requires user behavior change, doesn't wrap native `/model`

#### Approach D: MCP Server Model Tracker

Extend HestAI MCP server with model tracking:

```typescript
// In hestai-mcp-server
tools: [{
  name: "track_model_usage",
  description: "Extract model usage from session JSONL",
  inputSchema: { sessionPath: "string" }
}]
```

**Pros**: Integrates with existing infrastructure
**Cons**: Requires explicit invocation

---

## Data Available in JSONL

### Per Model Swap Event
- Timestamp (ISO 8601)
- Model short name (from command args)
- Model full identifier (from confirmation)
- Session UUID
- Line number in JSONL

### Per Assistant Message
- Model that generated response
- Token usage (input/output)
- Message ID
- Service tier

### Derivable Metrics
- Time spent on each model
- Message count per model
- Token usage per model
- Model switch frequency
- Session model timeline

---

## Recommendations

### For Real-Time Tracking

**Not currently possible** via hooks. Options:
1. Accept batch processing (SessionEnd hook)
2. Build external monitor (background process)
3. Propose feature request to Anthropic for ModelChange hook event

### For Historical Analysis

**Fully possible** via JSONL parsing:

```python
def analyze_session_models(jsonl_path):
    """Extract complete model usage timeline from session."""
    swaps = []
    with open(jsonl_path) as f:
        for i, line in enumerate(f):
            obj = json.loads(line)
            if 'Set model to' in str(obj.get('message', {}).get('content', '')):
                # Extract model info
                match = re.search(r'\((claude-[^)]+)\)', obj['message']['content'])
                if match:
                    swaps.append({
                        'line': i,
                        'timestamp': obj['timestamp'],
                        'model': match.group(1)
                    })
    return swaps
```

### For MCP Integration

Add to Context Steward tools:
- `model_history` - Extract model swaps from session
- `current_model` - Get active model from latest assistant message
- `model_usage_stats` - Calculate time/tokens per model

---

## Files Created

| File | Location | Purpose |
|------|----------|---------|
| `model-swap-hook.sh` | `.claude/hooks/user_prompt_submit/` | Original attempt (limited utility) |
| `MODEL-SWAP-HOOK.md` | `.claude/hooks/user_prompt_submit/` | Documentation |
| `settings.json` | `.claude/` | Hook configuration (updated) |

---

## Next Steps

1. **Decision**: Choose tracking approach (batch vs real-time vs MCP)
2. **Implementation**: Build chosen solution
3. **Validation**: Test across multiple sessions
4. **Integration**: Connect to Context Steward if applicable

---

## Appendix: Test Session Analysis

Session: `f8ff236c-ac14-468a-9e7d-e7c99d6a96a3.jsonl`

| Time | Action | Model |
|------|--------|-------|
| 13:39:01 | `/model haiku` | claude-haiku-4-5-20251001 |
| 13:39:09 | First response | Haiku |
| 13:44:52 | `/model default` | claude-opus-4-5-20251101 |
| 13:45:13 | First response | Opus |

**Duration on Haiku**: 5m 51s (79 assistant messages)
**Duration on Opus**: Remainder of session

---

**Report Status**: Complete
**Confidence**: High (verified against actual session data)
**Action Required**: Decision on implementation approach
