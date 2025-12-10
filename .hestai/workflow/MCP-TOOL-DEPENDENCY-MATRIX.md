# MCP Tool Dependency Matrix

**Date:** 2025-12-10
**Source Session:** f29cb14c (MCP Audit)
**Purpose:** Change control checklist for tool additions/removals
**Status:** ✅ ACTIVE (discovered during PR #108 review)

---

## Overview

This matrix documents tool interdependencies to prevent incomplete removals and unexpected cascades. Use this as a checklist before making any tool changes.

---

## Registry Tool Removal Case Study

### What Happened (PR #108)

The `tools/registry.py` module was deleted, but several dependencies remained:

```
tools/registry.py [DELETED]
├── tools/testguard.py
│   └── lines 382, 644: RegistryDB conditional imports
├── tools/critical_engineer.py
│   └── line 292: RegistryTool import
├── tests/test_testguard_token_generation.py
│   └── lines 54, 129: patch("tools.registry.RegistryDB")
├── tests/test_registry.py [ORPHANED]
├── tests/test_registry_json_sync.py [ORPHANED]
├── tests/test_registry_mcp_interface.py [ORPHANED]
├── tests/test_registry_schema.py [ORPHANED]
├── tests/test_specialist_registry_integration.py [ORPHANED]
└── tests/test_registry_provider_interface.py [ORPHANED]

RESULT: CI FAILURE - AttributeError: module 'tools' has no attribute 'registry'
RESOLUTION: 8 files updated/deleted, 2-day fix cycle
```

### Lesson Learned

**Principle:** Incomplete surgical removals cascade and are expensive to debug.

**Transfer:** Always follow the removal checklist below.

---

## Tool Dependency Checklist

### For ANY Tool Addition/Removal/Modification

#### 1. Code Dependencies

```bash
# Before removing/modifying TOOL_NAME:

# 1.1: Find all imports
grep -r "from tools\." --include="*.py" | grep TOOL_NAME
grep -r "import.*TOOL_NAME" --include="*.py"

# 1.2: Find conditional imports
grep -r "RegistryDB\|RegistryTool\|{TOOL_CLASS}" --include="*.py"

# 1.3: Find mock references in tests
grep -r "patch.*tools\." --include="*.py" tests/

# 1.4: Search documentation
grep -r "{TOOL_NAME}" --include="*.md" docs/ .hestai/
```

#### 2. Test Files

```bash
# Find all tests that reference this tool
grep -r "{TOOL_NAME}" tests/ --include="*.py"

# Delete or update test files:
# - DELETE: tests/test_{tool_name}*.py (if tool is deleted)
# - UPDATE: Any test that mocks/patches this tool
```

#### 3. Configuration Files

```bash
# Check DISABLED_TOOLS in .env
grep "DISABLED_TOOLS" .env

# Remove tool name from DISABLED_TOOLS if present
# (only needed if tool is being removed)
```

#### 4. Documentation

```bash
# Check all documentation
grep -r "{TOOL_NAME}" docs/ .hestai/workflow/ .hestai/patterns/

# Update README.md tool inventory
# Update any ADRs that mention this tool
# Update CLAUDE.md development guide if relevant
```

---

## Active Tool Dependency Graph

### Context Steward Tools

```
clockin (MCP Tool)
├── DEPENDS_ON: none (core session management)
├── USED_BY: clockout (verifies session exists)
├── MOCKED_BY: tests/test_clockin*.py
└── CONFIG: .env (no references)

clockout (MCP Tool)
├── DEPENDS_ON: clockin (session must exist)
├── USES: OCTAVE compression (external skill)
├── USED_BY: session lifecycle workflows
├── MOCKED_BY: tests/test_clockout*.py
└── CONFIG: .env (no references)

anchorsubmit (MCP Tool)
├── DEPENDS_ON: clockin (session context)
├── USED_BY: role activation workflows
├── MOCKED_BY: tests/test_anchorsubmit*.py
└── CONFIG: .env (no references)
```

### Document Management Tools

```
contextupdate (MCP Tool)
├── DEPENDS_ON: AI providers (Anthropic/Gemini APIs)
├── USES: document_submit for routing
├── USED_BY: PROJECT-CONTEXT synchronization
├── MOCKED_BY: tests/test_contextupdate*.py
└── CONFIG: API_KEY environment variables

documentsubmit (MCP Tool)
├── DEPENDS_ON: AI providers
├── USES: contextupdate for processing
├── MOCKED_BY: tests/test_documentsubmit*.py
└── CONFIG: API_KEY environment variables

requestdoc (MCP Tool)
├── DEPENDS_ON: AI providers
├── MOCKED_BY: tests/test_requestdoc*.py
└── CONFIG: API_KEY environment variables
```

### CLI Delegation

```
clink (MCP Tool)
├── DEPENDS_ON: External CLI clients (Claude, Gemini, Codex)
├── CONFIGURED_IN: conf/cli_clients/*.json
├── USES: systemprompts/clink/ roles
└── MOCKED_BY: tests/test_clink*.py
```

### Utility Tools

```
challenge (MCP Tool)
├── DEPENDS_ON: none
├── MOCKED_BY: tests/test_challenge*.py
└── CONFIG: .env (no references)

listmodels (MCP Tool)
├── DEPENDS_ON: API provider environment variables
├── MOCKED_BY: tests/test_listmodels*.py
└── CONFIG: OPENROUTER_ALLOWED_MODELS
```

---

## Removal Procedure

### To Remove a Tool Safely:

1. **Identify All Dependencies**
   ```bash
   grep -r "TOOL_NAME" --include="*.py" --include="*.md" --include="*.env" --include="*.json" .
   ```

2. **Create Dependency List**
   - Tools that import it
   - Test files that mock it
   - Config files that reference it
   - Documentation that mentions it

3. **Delete in This Order**
   ```
   1. Delete test files (tests/test_{tool_name}*.py)
   2. Remove imports from tools/*.py
   3. Remove from DISABLED_TOOLS in .env
   4. Remove from documentation
   5. Delete tools/{tool_name}.py
   ```

4. **Verify Removal**
   ```bash
   # Should return ZERO matches
   grep -r "{TOOL_NAME}" --include="*.py" .

   # Run full test suite
   ./code_quality_checks.sh
   ```

5. **Commit** with comprehensive message:
   ```
   fix: Remove {TOOL_NAME} tool and dependencies

   - Deleted tools/{tool_name}.py
   - Removed imports from tools/testguard.py (lines X, Y)
   - Removed imports from tools/critical_engineer.py (line Z)
   - Deleted test files: tests/test_{tool_name}*.py (6 files)
   - Removed from .env DISABLED_TOOLS
   - Updated documentation (CLAUDE.md)
   ```

---

## Known Issues & Patterns

### Issue: Conditional Imports

**Pattern:** Tools may conditionally import other tools

```python
# tools/testguard.py
try:
    from tools.registry import RegistryDB
except ImportError:
    RegistryDB = None
```

**Problem:** Grepping for "registry" might miss conditional imports

**Solution:**
- Search for the exception handler too
- Test that tool starts without the dependency
- Verify token generation works stateless

---

### Issue: Mock Dependencies in Tests

**Pattern:** Tests mock tool modules that may not exist in production

```python
# tests/test_testguard_token_generation.py
with patch("tools.registry.RegistryDB") as mock_registry:
    # ...
```

**Problem:**
- `patch()` imports the module at test time
- If module is deleted, test file raises ModuleNotFoundError
- CI fails before any assertions run

**Solution:**
- Delete test files that depend on deleted tools
- Rewrite tests to validate behavior without mocks (e.g., token format validation)

---

## Dependency Update Workflow

### When Configuration Changes

**Example:** Moving CLI client configuration

```
OLD: conf/cli_clients/claude.json
NEW: conf/cli_clients/claude-mcp.json

IMPACT_CHECK:
├── tools/clink.py → reads conf/cli_clients/
├── tests/test_clink.py → expects config at old path
├── CLAUDE.md → documents location
└── .env → may have path references

FIX:
1. Update path in clink.py
2. Update test fixtures
3. Update documentation
4. Verify tests pass
```

---

## Prevention Strategy

### Code Review Checklist for Tool Changes

Before approving PRs that modify tools:

```
□ Grep results shown for all dependencies
□ No orphaned test files
□ No stale imports in dependent modules
□ No configuration references remain
□ Documentation updated
□ All tests passing (unit + integration)
□ Commit message explains all changes
□ No "cleanup in follow-up PR" text
```

### Quarterly Audit

```bash
# Quarterly check: are there orphaned dependencies?
# Run these to catch drift early:

# Find all test files for non-existent tools
for f in tests/test_*.py; do
  TOOL=$(basename "$f" | sed 's/test_//;s/.py//')
  if [ ! -f "tools/$TOOL.py" ]; then
    echo "ORPHAN: $f references non-existent tools/$TOOL.py"
  fi
done

# Find imports that don't exist
python -m py_compile tests/*.py tools/*.py
```

---

## Configuration Reference Matrix

| Tool | Config File | Config Key | Can Be Disabled |
|------|-------------|-----------|-----------------|
| clockin | .env | N/A | NO (core) |
| clockout | .env | N/A | NO (core) |
| anchorsubmit | .env | N/A | NO (core) |
| contextupdate | .env | API_KEY, OPENAI_API_KEY | NO (essential) |
| documentsubmit | .env | API_KEY | NO (essential) |
| requestdoc | .env | N/A | YES |
| clink | conf/cli_clients/*.json | 3 client configs | YES |
| challenge | .env | N/A | YES |
| listmodels | .env | OPENROUTER_ALLOWED_MODELS | YES |

**Note:** DISABLED_TOOLS in .env should only list optional tools

---

## Recommendations

1. **Document Tool Dependencies on Addition**
   - When adding a new tool, immediately document its dependencies
   - Create a `tools/{tool_name}_DEPENDENCIES.md` file

2. **Pre-Removal Audit Script**
   - Create automated dependency scanner
   - Run before any tool deletion PR

3. **Test Orphan Detection**
   - Add CI check to find orphaned test files
   - Fail if test references non-existent module

4. **Dependency Update Bot**
   - Quarterly check for stale references
   - Flag documentation that mentions deleted tools

---

## Conclusion

**The PR #108 experience revealed that incomplete tool removals are expensive to debug.** This matrix serves as a prevention mechanism for future changes.

Always verify all 4 dependency categories:
- ✅ Code imports
- ✅ Test mocks
- ✅ Configuration
- ✅ Documentation

---

**Matrix Created:** 2025-12-10
**Source:** Session f29cb14c (MCP Audit)
**Next Update:** After next tool change
**Owner:** system-steward
