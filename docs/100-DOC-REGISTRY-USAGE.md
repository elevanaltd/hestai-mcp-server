# Registry Tool Usage Guide

## Overview

The RegistryTool is an infrastructure component for managing specialist approvals of blocked changes in the HestAI MCP Server. It provides a persistent registry where hooks can record blocked operations and specialists can approve or reject them with single-use tokens.

## Architecture

### Core Components

1. **SQLite Database** - Persistent storage at `~/.claude/hooks/registry.db`
2. **WAL Mode** - Write-Ahead Logging for concurrent access
3. **Atomic Transactions** - Prevents race conditions on token validation
4. **Migration Support** - Schema versioning for future updates
5. **Backup Mechanism** - Automatic daily backups

### Database Schema

```sql
CREATE TABLE blocked_changes (
    uuid TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    file_path TEXT NOT NULL,
    specialist_type TEXT NOT NULL,
    blocked_content TEXT,
    status TEXT DEFAULT 'blocked',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by TEXT,
    rejection_reason TEXT,
    education TEXT,
    token TEXT UNIQUE,
    token_used INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Examples

### 1. Hook Blocking a Change

When a hook detects a problematic change:

```python
from tools.registry import RegistryTool

# Hook detects issue
tool = RegistryTool()
result = tool.create_blocked_entry(
    description="Test without failing assertion",
    file_path="/path/to/test.py",
    specialist_type="testguard",
    blocked_content="expect(true).toBe(false)"
)

print(f"Blocked with UUID: {result['uuid']}")
# Hook can now wait for approval or rejection
```

### 2. Specialist Review

Specialists can list and review pending approvals:

```python
# List all pending approvals
pending = tool.list_pending()
for entry in pending:
    print(f"UUID: {entry['uuid']}")
    print(f"Description: {entry['description']}")
    print(f"File: {entry['file_path']}")
    print(f"Specialist needed: {entry['specialist_type']}")
```

### 3. Approval Flow

When a specialist approves a change:

```python
# Approve with reason
approval = tool.approve_entry(
    uuid=entry_uuid,
    specialist="testguard",
    reason="Valid TDD red phase - test should fail first"
)

print(f"Token: {approval['token']}")
print(f"Instruction: {approval['instruction']}")
# Output: Add '// TESTGUARD-APPROVED: TESTGUARD-20250904-e6bfdb58' to your code
```

### 4. Token Validation

Hooks validate tokens before allowing changes:

```python
# Validate token (single-use)
validation = tool.validate_token(
    token=approval_token,
    uuid=entry_uuid
)

if validation['valid']:
    # Allow the change to proceed
    print(f"Approved by: {validation['specialist']}")
else:
    # Block the change
    print(f"Invalid token: {validation['error']}")
```

### 5. Rejection Flow

When a specialist rejects a change:

```python
rejection = tool.reject_entry(
    uuid=entry_uuid,
    specialist="testguard",
    reason="Meaningless test provides no specification",
    education="Tests should describe expected behavior and fail when not implemented"
)

# User receives educational feedback
print(rejection['education'])
```

## Integration with MCP Server

The RegistryTool is available as an MCP tool and can be invoked through the execute method:

```python
# Via MCP execute interface
result = await tool.execute(
    action="create_blocked",
    description="...",
    file_path="...",
    specialist_type="...",
    blocked_content="..."
)
```

### Available Actions

- `create_blocked` - Create a new blocked entry
- `approve` - Approve a blocked entry and generate token
- `reject` - Reject a blocked entry with education
- `validate` - Validate an approval token
- `list_pending` - List all pending approvals
- `cleanup` - Clean up old entries (>90 days)

## Security Features

### Single-Use Tokens

Tokens are atomically marked as used during validation:

```sql
BEGIN EXCLUSIVE;
-- Check if token is valid and unused
-- Mark token as used
-- Commit or rollback
```

### Token Format

Tokens follow the pattern: `SPECIALIST-DATE-UUID_PREFIX`

Example: `TESTGUARD-20250904-e6bfdb58`

### Concurrency Safety

- WAL mode enables concurrent reads
- 5-second busy timeout for lock handling
- Atomic transactions for token validation

## Hook Integration Pattern

### Recommended Hook Flow

```bash
#!/bin/bash
# Example hook implementation

# 1. Detect issue
if detect_problem; then
    # 2. Create registry entry
    UUID=$(create_registry_entry)

    # 3. Block and inform user
    echo "BLOCKED: Specialist approval required"
    echo "UUID: $UUID"
    echo "Run: specialist-tool approve $UUID"

    # 4. Wait for approval (or implement async check)
    exit 1
fi

# 5. If token provided, validate
if [[ -n "$APPROVAL_TOKEN" ]]; then
    if validate_token "$APPROVAL_TOKEN" "$UUID"; then
        echo "Approved - proceeding with change"
        exit 0
    fi
fi
```

## Maintenance

### Automatic Backups

Backups are created daily at:
- Location: `~/.claude/hooks/registry.db.bak`
- Frequency: Every 24 hours on first access

### Cleanup

Old entries (>90 days) are automatically cleaned:

```python
deleted_count = tool.db.cleanup_old_entries(days=90)
```

## Testing

Run the test suite:

```bash
python -m pytest tests/test_registry.py -v
```

All tests should pass:
- Database initialization
- CRUD operations
- Token validation
- Atomic operations
- Concurrency handling

## Next Steps

1. **Hook Updates**: Update existing hooks to use the registry
2. **Server Integration**: Add RegistryTool to server.py imports
3. **Specialist Tools**: Create specialist interfaces for review
4. **Monitoring**: Add logging and metrics for approval workflows
5. **Documentation**: Update hook documentation with registry patterns

## Support

For issues or questions:
- Check logs at: `logs/mcp_server.log`
- Database location: `~/.claude/hooks/registry.db`
- Test with: `python -m pytest tests/test_registry.py`
