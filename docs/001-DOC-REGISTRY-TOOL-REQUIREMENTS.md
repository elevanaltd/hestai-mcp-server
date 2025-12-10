# Registry Management Tool Requirements for HestAI MCP Server

## Executive Summary

We need a new MCP tool to manage approval registries that work with Claude Code hooks. Currently, hooks can block operations and force specialist consultation, but specialists (via hestai agents) cannot modify files to update registries or approve changes. This creates a workflow gap where blocked work cannot proceed even after specialist approval.

## Problem Statement

### Current Workflow Gap
1. **Hook blocks operation** → Content saved to `/tmp/blocked-{type}-{timestamp}`
2. **Claude consults specialist** → `mcp__hestai__testguard "review /tmp/blocked-test-123456"`
3. **Specialist analyzes and approves** → But CANNOT update registry or move files
4. **Work remains blocked** → No mechanism to unblock approved changes

### Root Cause
- HestAI agents (via MCP) can only return text responses
- Cannot modify files or update registries
- No way to "complete the loop" after approval

## Proposed Solution: Registry Management Tool

Add a new tool to hestai-mcp-server that manages approval registries for hook integration.

## Tool Specification

### Tool Name: `registry`

### Core Functions

#### 1. `approve_change`
```python
def approve_change(
    blocked_file: str,      # Path to /tmp/blocked-* file
    content_hash: str,      # SHA256 of blocked content
    approver: str,          # Which specialist approved (testguard, critical-engineer, etc.)
    reason: str,            # Why this was approved
    pattern: Optional[str]  # Optional: Pattern to add to permanent approvals
) -> ApprovalResponse:
    """
    Generate a one-time approval token for blocked content.

    Returns:
    {
        "token": "TESTGUARD-20250104-12345678-abc123",
        "expires": "2025-01-04T12:05:00Z",
        "instruction": "Add '// TESTGUARD-APPROVED: {token}' to your content"
    }
    """
```

#### 2. `reject_change`
```python
def reject_change(
    blocked_file: str,      # Path to /tmp/blocked-* file
    rejector: str,          # Which specialist rejected
    reason: str,            # Why this was rejected
    education: str          # Educational content for the agent
) -> RejectionResponse:
    """
    Record rejection in audit log and return education.

    Returns:
    {
        "decision": "rejected",
        "education": "...",  # Why this is wrong
        "suggestion": "..."   # What to do instead
    }
    """
```

#### 3. `add_pattern`
```python
def add_pattern(
    pattern_type: str,      # "test", "architecture", "security"
    pattern: str,           # Regex pattern to auto-approve
    approver: str,          # Who approved this pattern
    reason: str,            # Why this pattern is acceptable
    example: str            # Example of approved content
) -> PatternResponse:
    """
    Add a permanent approval pattern based on learned good practices.
    """
```

#### 4. `check_approval`
```python
def check_approval(
    content_hash: str       # Hash of content to check
) -> ApprovalStatus:
    """
    Check if content is already approved (token or pattern).
    Used by hooks to validate.
    """
```

## Registry File Structure

Location: `~/.claude/hooks/lib/traced-registry.json`

```json
{
  "version": "1.0",
  "one_time_approvals": {
    "TESTGUARD-20250104-12345678-abc123": {
      "content_hash": "sha256:abcdef123456...",
      "blocked_file": "/tmp/blocked-test-1234567890",
      "expires": "2025-01-04T12:05:00Z",
      "created": "2025-01-04T12:00:00Z",
      "used": false,
      "approved_by": "testguard",
      "reason": "Proper TDD red phase - precise assertion for missing functionality"
    }
  },
  "permanent_patterns": {
    "tdd_red_phase_throw": {
      "pattern": "expect\\(.*\\)\\.rejects\\.toThrow\\(['\"].*['\"]\\)",
      "type": "test",
      "auto_approve": true,
      "added_by": "testguard",
      "added_date": "2025-01-04",
      "reason": "Standard TDD pattern - expecting specific error",
      "usage_count": 0
    }
  },
  "blocked_patterns": {
    "meaningless_red": {
      "pattern": "expect\\(true\\)\\.toBe\\(false\\)",
      "type": "test",
      "reason": "Meaningless placeholder - provides no specification",
      "added_by": "testguard",
      "added_date": "2025-01-04"
    }
  },
  "audit_log": [
    {
      "timestamp": "2025-01-04T12:00:00Z",
      "action": "approved",
      "specialist": "testguard",
      "token": "TESTGUARD-20250104-12345678-abc123",
      "blocked_file": "/tmp/blocked-test-1234567890",
      "reason": "Proper TDD red phase assertion",
      "outcome": "pending"
    }
  ]
}
```

## Integration Workflow

### Stage 1: Hook Blocks Operation
```bash
# Hook detects issue
echo "BLOCKED::TEST_METHODOLOGY_VIOLATION" >&2
echo "SAVED::/tmp/blocked-test-1234567890" >&2
echo "ACTION::mcp__hestai__testguard 'review /tmp/blocked-test-1234567890'" >&2
exit 2
```

### Stage 2: Claude Calls Specialist
```python
# Claude invokes
mcp__hestai__testguard("review /tmp/blocked-test-1234567890")
```

### Stage 3: Specialist Uses Registry Tool
```python
# Inside testguard's response logic
if blocked_file_path in prompt:
    content = read_file(blocked_file_path)
    analysis = analyze_test_methodology(content)

    if analysis.is_valid:
        # Use registry tool to approve
        result = registry.approve_change(
            blocked_file=blocked_file_path,
            content_hash=calculate_hash(content),
            approver="testguard",
            reason=analysis.reason
        )
        return f"APPROVED: {analysis.reason}\n\nAdd this to your code:\n// TESTGUARD-APPROVED: {result.token}"
    else:
        # Use registry tool to reject and educate
        result = registry.reject_change(
            blocked_file=blocked_file_path,
            rejector="testguard",
            reason=analysis.violation,
            education=analysis.education
        )
        return f"REJECTED: {result.education}"
```

### Stage 4: Claude Retries with Token
```javascript
// TESTGUARD-APPROVED: TESTGUARD-20250104-12345678-abc123
expect(serverInit()).rejects.toThrow('Server not configured');
```

### Stage 5: Hook Validates Token
```bash
# Hook checks for approval token
if grep -q "TESTGUARD-APPROVED:" <<< "$content"; then
  token=$(grep -oP 'TESTGUARD-APPROVED:\s*\K[\w-]+' <<< "$content")

  # Validate via registry check
  if validate_token_in_registry "$token" "$content_hash"; then
    mark_token_used "$token"
    echo "✅ Approved by specialist: $token" >&2
    exit 0
  fi
fi
```

## Security Considerations

### Token Security
- **Single-use**: Tokens marked as used after first successful operation
- **Time-limited**: 5-minute expiry window
- **Content-bound**: Token tied to specific content hash
- **Non-transferable**: Cannot be reused for different content

### Registry Integrity
- **Atomic updates**: Use file locking to prevent race conditions
- **Backup on write**: Keep last 10 versions of registry
- **Validation**: Check JSON validity before writing
- **Permissions**: Registry file should be user-readable/writable only

### Audit Requirements
- **Every decision logged**: Approvals, rejections, and usage
- **Rotation**: Keep 30 days of audit logs
- **Pattern metrics**: Track pattern usage for refinement
- **Gaming detection**: Flag suspicious patterns (many rejections followed by approval)

## Implementation Priority

### Phase 1: Core Token System (Week 1)
- [ ] Create `RegistryTool` class in hestai-mcp-server
- [ ] Implement `approve_change` and `reject_change` functions
- [ ] Add registry file creation and validation
- [ ] Update hook to check for tokens
- [ ] Test with testguard integration

### Phase 2: Pattern System (Week 2)
- [ ] Implement `add_pattern` function
- [ ] Add pattern matching to hooks
- [ ] Build initial pattern library from audit logs
- [ ] Add pattern usage tracking

### Phase 3: Audit & Metrics (Week 3)
- [ ] Implement comprehensive audit logging
- [ ] Add metrics dashboard/report tool
- [ ] Pattern effectiveness analysis
- [ ] Gaming detection algorithms

## Success Criteria

1. **Workflow Completion**: Blocked changes can proceed after specialist approval
2. **Security**: No bypass without legitimate specialist consultation
3. **Auditability**: Complete record of all decisions and usage
4. **Learning**: System improves over time through pattern recognition
5. **Performance**: Minimal overhead on file operations (<100ms)

## Example Usage

### For Test Methodology
```bash
# Agent tries to write bad test
Write("test.js", "expect(true).toBe(false)")
# BLOCKED by hook

# Claude consults testguard
mcp__hestai__testguard("review /tmp/blocked-test-123")
# Returns: "REJECTED: Meaningless placeholder..."

# Agent fixes approach
Write("test.js", "expect(server()).rejects.toThrow('Not configured')")
# BLOCKED by hook

# Claude consults testguard
mcp__hestai__testguard("review /tmp/blocked-test-456")
# Returns: "APPROVED: Proper TDD... Add: // TESTGUARD-APPROVED: TESTGUARD-20250104-abc123"

# Agent retries with token
Write("test.js", "// TESTGUARD-APPROVED: TESTGUARD-20250104-abc123\nexpect(server()).rejects.toThrow('Not configured')")
# SUCCESS - token validated, operation proceeds
```

## Questions Needing Answers

1. **Token Format**: Should we include specialist name in token? `TESTGUARD-` prefix or generic `APPROVED-`?
2. **Expiry Time**: 5 minutes reasonable? Should it be configurable?
3. **Pattern Promotion**: After how many uses should a token pattern become permanent?
4. **Registry Location**: `~/.claude/hooks/lib/` or somewhere else?
5. **Multiple Specialists**: How to handle different specialists (testguard, critical-engineer, etc.)?

## Conclusion

This registry tool solves the critical gap in our hook-based quality enforcement system. It maintains the strength of blocking while allowing legitimate work to proceed after specialist approval. The hybrid approach with both one-time tokens and learned patterns provides immediate security with long-term improvement.

The implementation is straightforward - primarily JSON file manipulation with careful attention to atomicity and security. The tool fits naturally into the existing hestai-mcp-server architecture as another SimpleTool implementation.

**Recommended immediate action**: Implement Phase 1 (core token system) to unblock the current workflow gap, then iterate on patterns and audit capabilities based on real usage data.
