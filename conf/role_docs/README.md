# Role Documentation Auto-Loading

This directory contains role-specific documentation manifests that enable automatic file injection when invoking agents through the `clink` tool.

## Overview

When you invoke a role via the `clink` tool, the system automatically loads supporting documentation files defined in that role's manifest. This eliminates the need to manually specify knowledge files every time, ensuring agents have consistent access to essential documentation.

## Architecture

### Structural Pattern
```
Role Invocation → Manifest Lookup → Auto-File Injection → Agent Execution
```

This mirrors the Skills auto-loading pattern from Claude Code, but implemented for MCP server role-specific documentation.

### Manifest Format

Each role manifest is a YAML file: `{role-name}.yaml`

```yaml
role: role-name
description: "Brief description of the role"
version: "1.0"

auto_load_files:
  # Always loaded with this role
  mandatory:
    - path: /absolute/path/to/file1.md
      reason: "Why this file is essential for this role"
    - path: /absolute/path/to/file2.md
      reason: "Another essential file"

  # Only loaded when explicitly needed (future enhancement)
  optional:
    - path: /absolute/path/to/advanced-file.md
      reason: "Advanced topics for specific scenarios"
```

### File Categories

**Mandatory Files**: Core knowledge essential for the role's function. Loaded automatically every time.

**Optional Files**: Advanced or context-specific documentation. Currently not auto-loaded but reserved for future enhancement (e.g., flag-based loading).

## Usage

### Automatic Loading (Default)

When you invoke a role, mandatory files are automatically loaded:

```python
mcp__hestai__clink(
    cli_name="gemini",
    role="implementation-lead",
    prompt="Implement feature X with TDD"
)
```

The system automatically loads:
- `/Users/shaunbuswell/.claude/skills/build-execution/SKILL.md`
- `/Users/shaunbuswell/.claude/skills/build-execution/tdd-discipline.md`
- `/Users/shaunbuswell/.claude/skills/build-execution/build-philosophy.md`

### Explicit File Addition

You can still add files explicitly, which will be merged with auto-loaded files:

```python
mcp__hestai__clink(
    cli_name="gemini",
    role="implementation-lead",
    prompt="Implement feature X",
    files=["/path/to/specific-context.md"]  # Added to mandatory files
)
```

### Deduplication

The system automatically deduplicates files, so if you explicitly request a file that's already in the manifest, it will only be loaded once.

### Order Preservation

Files are loaded in this order:
1. Mandatory files from manifest (in order defined)
2. Optional files from manifest (if enabled)
3. Explicitly requested files (in order provided)

## Available Role Manifests

| Role | Mandatory Files | Focus Area |
|------|----------------|------------|
| `implementation-lead` | Build execution, TDD, MIP | Build phase execution with test-first discipline |
| `technical-architect` | Build philosophy, Supabase ops | Architecture decisions and database design |
| `error-architect` | Error triage, CI resolution | Systematic error resolution |
| `test-methodology-guardian` | Test infrastructure, CI pipeline, TDD | Test quality and methodology enforcement |
| `workspace-architect` | Workspace setup, Build philosophy | B1_02 workspace creation and structure |
| `code-review-specialist` | Build philosophy, Anti-patterns | Code quality enforcement |
| `critical-engineer` | Build execution, Verification, Error triage | Production readiness validation |

## Creating New Role Manifests

### Step 1: Create Manifest File

Create `conf/role_docs/{role-name}.yaml`:

```yaml
role: my-new-role
description: "What this role does"
version: "1.0"

auto_load_files:
  mandatory:
    - path: /path/to/essential/doc1.md
      reason: "Core knowledge for this role"
    - path: /path/to/essential/doc2.md
      reason: "Another essential document"

  optional:
    - path: /path/to/advanced/doc.md
      reason: "Advanced topics"
```

### Step 2: Verify Paths

Ensure all file paths are:
- **Absolute paths** (not relative)
- **Existing files** (system will log warnings for missing files)
- **Relevant to the role** (avoid loading unnecessary documentation)

### Step 3: Test

Invoke the role and check logs for auto-loading confirmation:

```
INFO: Auto-loaded 3 files for role 'my-new-role' (mandatory=3, optional=0, explicit=0, total=3)
```

## Guidelines for Manifest Creation

### Minimal Intervention Principle

Only include files that are **essential** for the role's core function. Avoid accumulative knowledge loading.

**Good**: Implementation-lead loads build-execution SKILL.md (directly enables build execution)
**Bad**: Implementation-lead loads all testing docs (not essential for build phase)

### Token Budget Awareness

Each file consumes tokens. Prefer:
- Concise, focused documentation
- 2-4 mandatory files per role
- Reserve optional files for truly advanced topics

### Path Organization

Use consistent path patterns:

- Global skills: `/Users/shaunbuswell/.claude/skills/{skill-name}/`
- Project skills: `/Volumes/HestAI-Projects/eav-monorepo/.claude/skills/{skill-name}/`
- HestAI docs: `/Volumes/HestAI/docs/`

### Reason Documentation

Always provide clear `reason` fields explaining why each file is loaded. This serves as documentation for future maintainers.

## Implementation Details

### Code Location

- **Manifest loading**: `utils/role_manifest.py`
- **Integration point**: `tools/clink.py` (line 189-195)
- **Tests**: `tests/test_role_manifest.py`

### Loading Process

1. `clink.execute()` extracts role from request
2. `load_role_documentation()` checks for `{role}.yaml` manifest
3. If manifest exists, loads mandatory file paths
4. Merges with explicitly requested files
5. Deduplicates while preserving order
6. Passes combined list to agent

### Error Handling

- Missing manifest: No error, uses only explicit files
- Invalid YAML: Logged as warning, fallback to explicit files
- Missing file paths: Logged as warning, file skipped
- Non-dict manifest: Logged as warning, manifest ignored

## Future Enhancements

### Conditional Loading (Planned)

```yaml
auto_load_files:
  conditional:
    errors:
      - path: /path/to/error-docs.md
    testing:
      - path: /path/to/test-docs.md
```

Invoke with flags:
```python
# Future: Not yet implemented
mcp__hestai__clink(
    role="implementation-lead",
    load_flags=["errors", "testing"],  # Load conditional sections
    prompt="..."
)
```

### Dynamic Manifest Updates

Future enhancement to reload manifests without server restart.

## Troubleshooting

### Files Not Loading

**Check logs**: Look for auto-loading confirmation message

```bash
tail -f logs/mcp_server.log | grep "Auto-loaded"
```

**Common issues**:
- Manifest file name doesn't match role name
- File paths are relative instead of absolute
- YAML syntax errors
- Manifest in wrong directory

### Too Many Tokens

If you're hitting token limits:

1. Reduce mandatory files to 2-3 most essential
2. Move less critical files to optional
3. Consider creating more focused skill documents
4. Use explicit file loading only when needed

### Manifest Not Found

If no manifest exists for a role, the system logs:

```
DEBUG: No role manifest found for 'role-name' at conf/role_docs/role-name.yaml
```

This is not an error - the role will work with explicit files only.

## Examples

### Example 1: Implementation Lead Build Execution

```yaml
role: implementation-lead
description: "Build execution specialist with TDD discipline"

auto_load_files:
  mandatory:
    - path: /Users/shaunbuswell/.claude/skills/build-execution/SKILL.md
      reason: "Core build execution protocol and workflow"
    - path: /Users/shaunbuswell/.claude/skills/build-execution/tdd-discipline.md
      reason: "RED→GREEN→REFACTOR discipline enforcement"
    - path: /Users/shaunbuswell/.claude/skills/build-execution/build-philosophy.md
      reason: "Minimal Intervention Principle and system awareness"
```

**Result**: Every implementation-lead invocation automatically has build execution knowledge.

### Example 2: Technical Architect Database Design

```yaml
role: technical-architect
description: "Technical architecture and system design"

auto_load_files:
  mandatory:
    - path: /Users/shaunbuswell/.claude/skills/build-execution/build-philosophy.md
      reason: "Minimal Intervention Principle - essential vs accumulative architecture"
    - path: /Users/shaunbuswell/.claude/skills/supabase-operations/SKILL.md
      reason: "Database architecture patterns and migration protocols"
```

**Result**: Technical architect always has MIP and database knowledge for architecture decisions.

## Testing

Comprehensive test suite at `tests/test_role_manifest.py`:

- Manifest parsing
- File loading and merging
- Deduplication
- Order preservation
- Error handling

Run tests:
```bash
python -m pytest tests/test_role_manifest.py -v
```

## Version History

- **v1.0** (2024-11-22): Initial implementation with mandatory file auto-loading
- Future: Conditional loading, dynamic reloading

## Related Documentation

- **Clink Tool**: See `CLAUDE.md` for clink usage patterns
- **Skills System**: See `/Users/shaunbuswell/.claude/skills/` for available knowledge base
- **Agent Roles**: See `systemprompts/clink/` for role definitions

---

For questions or issues with role manifests, check the implementation at `utils/role_manifest.py` and tests at `tests/test_role_manifest.py`.
