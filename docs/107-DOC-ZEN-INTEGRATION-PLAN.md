# 107-DOC-ZEN-INTEGRATION-PLAN

Comprehensive Integration Plan: Zen-MCP-Server → HestAI-MCP-Server

**Document Status:** Active Integration Plan - PHASE 0 COMPLETE
**Version:** 1.1 (Updated with Foundation Sync Phase)
**Last Updated:** 2025-10-06
**Owner:** Technical Architecture Team
**Phase 0 Status:** ✅ COMPLETE - See docs/108-DOC-PHASE-0-COMPLETION-REPORT.md

---

## Executive Summary

### Divergence Analysis

- **Common ancestor:** `ad6b216` (fork point)
- **HestAI commits ahead:** 105 commits
- **Zen commits ahead:** 349 commits
- **Assessment:** Significant independent evolution in both codebases

### Key HestAI-Specific Features to Preserve

1. **Custom tools:** `critical_engineer.py`, `testguard.py`, `registry.py`
2. **Schema optimization:** Token reduction via schema consolidation (recent work)
3. **Security features:** Project-aware context isolation, typed SessionContext
4. **Modified `challenge.py`:** Enhanced description with mandatory automatic invocation rules

### Zen Features to Adopt

1. **`clink` tool** - CLI integration (Gemini CLI, Codex CLI, Qwen CLI)
2. **`apilookup` tool** - API documentation lookup
3. **Role deduplication refactor** - Cleaner role management
4. **Codex CLI support** - Native Codex CLI integration

### Integration Benefits

- **Token Preservation:** Delegate tasks to free Gemini CLI (1000 requests/day)
- **Codex Integration:** Leverage existing Codex subscription efficiently
- **API Lookup:** Current documentation without MCP context pollution
- **Maintained Quality:** All HestAI enhancements preserved

---

## Phase-by-Phase Integration Plan

### Phase 0: Preparation & Risk Mitigation

**Timeline:** Day 1
**Purpose:** Create safety infrastructure and baseline documentation

#### Create Integration Branch Structure

```bash
# Create safety branch from current main
git checkout main
git pull origin main
git checkout -b upstream-integration-staging

# Tag current state for easy rollback
git tag pre-upstream-integration-$(date +%Y%m%d)
git push origin pre-upstream-integration-$(date +%Y%m%d)
```

#### Backup Critical Files

```bash
# Create backup directory
mkdir -p .integration-backup

# Backup hestai-specific tools
cp tools/critical_engineer.py .integration-backup/
cp tools/testguard.py .integration-backup/
cp tools/registry.py .integration-backup/
cp tools/challenge.py .integration-backup/

# Backup configuration
cp tools/__init__.py .integration-backup/
cp config.py .integration-backup/
```

#### Document Current State

```bash
# Generate current tool list
python -c "from tools import get_all_tools; print('\n'.join(sorted([t.get_name() for t in get_all_tools()])))" > .integration-backup/current-tools.txt

# Run baseline tests
./code_quality_checks.sh > .integration-backup/pre-integration-test-results.txt
```

#### Success Criteria

- [x] Integration branch created ✅
- [x] Rollback tag created and pushed ✅
- [x] Backup branch created ✅ (per critical-engineer)
- [x] Critical files backed up ✅ (comprehensive)
- [x] Baseline test results documented ✅ (926 tests passing)
- [x] Critical-engineer review completed ✅
- [x] Strategy revised to manual porting ✅

**Phase 0 Status:** ✅ COMPLETE - Commit `11c4ee7`

---

### Phase 0.5: Foundation Sync (NEW - MANDATORY)

**Timeline:** Week 1, Days 1-3
**Purpose:** Align core architecture before feature integration
**Priority:** CRITICAL - MUST complete before any feature porting

⚠️ **CRITICAL-ENGINEER MANDATE:** This phase was added based on architectural drift analysis. With 349 upstream commits vs 105 HestAI commits from common ancestor, attempting feature integration without foundation sync will create unmaintainable "Frankenstein code."

#### Core Architecture Alignment Tasks

**1. Dependency Analysis**
```bash
# Compare dependency files
diff .integration-backup/pyproject.toml /tmp/zen-upstream-analysis/pyproject.toml
diff .integration-backup/requirements.txt /tmp/zen-upstream-analysis/requirements.txt

# Identify version conflicts
# Manual merge of compatible versions
# Test compatibility before proceeding
```

**2. Base Tool Abstraction Review**
```bash
# CRITICAL: Compare base tool implementations
diff .integration-backup/shared/base_tool.py /tmp/zen-upstream-analysis/tools/shared/base_tool.py

# Identify breaking changes:
# - Method signature changes
# - New required methods
# - Removed/deprecated methods
# - Constructor changes

# Impact: ALL tools depend on this base class
```

**3. Server Infrastructure Review**
```bash
# Compare server initialization
diff .integration-backup/server.py /tmp/zen-upstream-analysis/server.py

# Focus areas:
# - Middleware changes
# - Tool registration patterns
# - Session management
# - Error handling
```

**4. Utility Module Sync**
```bash
# Compare shared utilities
diff -r .integration-backup/utils /tmp/zen-upstream-analysis/utils

# Common conflict sources:
# - Logging configuration
# - Session management
# - File processing
# - Provider routing
```

**5. Configuration Schema Merge**
```bash
# CRITICAL: Schema merge, not file replacement
diff .integration-backup/config.py /tmp/zen-upstream-analysis/config.py

# Merge strategy:
# - Keep HestAI schema optimization settings
# - Add new Zen configuration variables
# - Validate no key conflicts
# - Update config validation
```

#### Testing Protocol

```bash
# After each infrastructure change:

# 1. Linting
ruff check . --fix
black .
isort .

# 2. Unit tests
python -m pytest tests/unit/ -v

# 3. HestAI Regression Suite (MANDATORY)
python -m pytest tests/test_critical_engineer.py -v
python -m pytest tests/test_testguard.py -v
python -m pytest tests/test_registry.py -v

# 4. Server startup validation
python server.py --validate-config

# 5. All 18 tools must load
# Verify tool registration
```

#### Success Criteria

- [ ] Dependency compatibility verified (no version conflicts)
- [ ] Base tool abstraction changes analyzed and merged
- [ ] Server infrastructure changes analyzed and merged
- [ ] Utility modules synchronized
- [ ] Configuration schema merged (not replaced)
- [ ] All unit tests passing (926+)
- [ ] HestAI regression suite passing (critical-engineer, testguard, registry)
- [ ] Server starts without config errors
- [ ] All 18 tools load successfully

**Validation:** Run `python communication_simulator_test.py --quick` (6/6 must pass)

**Only after Foundation Sync passes** can Gemini SDK migration proceed.

---

### Phase 0.75: Gemini SDK Migration (NEW - MANDATORY)

**Timeline:** Week 1, Days 4-5
**Purpose:** Migrate Gemini provider from deprecated SDK to modern google-genai SDK
**Priority:** HIGH - Required before feature porting (new tools may depend on it)

⚠️ **CRITICAL-ENGINEER MANDATE:** Baseline stabilization revealed that HestAI's `pyproject.toml` incorrectly declared `google-genai>=1.19.0` while actual code uses deprecated `google.generativeai>=0.8.0`. Upstream Zen has migrated to modern SDK. This phase isolates the high-risk provider migration into a single, testable, rollback-safe step.

#### Provider Migration Tasks

**1. Update Dependencies**
```bash
# Create dedicated branch
git checkout -b sync/02-gemini-sdk-migration upstream-integration-staging

# Update dependency files to use NEW SDK
# pyproject.toml: google-generativeai>=0.8.0 → google-genai>=1.19.0
# requirements.txt: google-generativeai>=0.8.0 → google-genai>=1.19.0
```

**2. Port Gemini Provider**
```bash
# Manually port provider from Zen upstream
cp /tmp/zen-upstream-analysis/providers/gemini.py providers/gemini.py

# Key API changes:
# OLD: import google.generativeai as genai
# NEW: from google import genai
#      from google.genai import types

# Provider file size: 467→558 lines (substantial rewrite)
```

**3. Create Targeted Integration Test**
```bash
# Create test_gemini_v2_provider.py to validate:
# - Text generation with new SDK
# - Streaming support
# - Error handling
# - Image processing (vision capabilities)
# - Thinking mode support
```

#### Testing Protocol

```bash
# After provider migration:

# 1. Linting
ruff check . --fix --exclude .integration-backup
black . --exclude .integration-backup
isort .

# 2. New targeted test
python -m pytest tests/test_gemini_v2_provider.py -v

# 3. Full regression suite
python -m pytest tests/ -v -m "not integration"

# 4. HestAI Regression Suite (MANDATORY)
python -m pytest tests/test_critical_engineer.py -v
python -m pytest tests/test_testguard.py -v
python -m pytest tests/test_registry.py -v

# 5. Quick simulator test
python communication_simulator_test.py --quick
```

#### Success Criteria

- [ ] Dependencies updated to google-genai>=1.19.0
- [ ] Provider file ported from upstream (558 lines)
- [ ] New targeted test created and passing
- [ ] All unit tests passing (926+)
- [ ] HestAI regression suite passing
- [ ] Quick simulator: 6/6 passing
- [ ] No regression in Gemini model functionality

#### Rollback if Needed

```bash
git checkout upstream-integration-staging
git branch -D sync/02-gemini-sdk-migration
```

**Validation:** Provider abstraction interface in `providers/base.py` must remain stable - rest of codebase should not be affected by this internal implementation change.

**Only after Gemini SDK Migration passes** can feature porting begin.

---

### Phase 1: Manual Port - Role Deduplication

**Timeline:** Week 1, Days 1-2
**Purpose:** Clean up role handling before adding new CLI integrations

#### Commands

```bash
git checkout -b phase1-role-deduplication upstream-integration-staging

# Cherry-pick role deduplication refactor
git cherry-pick c42e9e9

# Resolve any conflicts (likely in tool registration)
# Review changes carefully
git diff HEAD~1
```

#### Testing

```bash
# Verify linting
ruff check . --fix
black .
isort .

# Run unit tests
python -m pytest tests/ -v -m "not integration"

# Run quick simulator test
python communication_simulator_test.py --quick --verbose

# Specifically test role-related functionality
python communication_simulator_test.py --individual consensus_workflow_accurate --verbose
```

#### Success Criteria

- [ ] All linting passes
- [ ] Unit tests pass
- [ ] Quick simulator tests pass (6/6)
- [ ] No regression in role assignment functionality

#### Rollback if Needed

```bash
git checkout upstream-integration-staging
git branch -D phase1-role-deduplication
```

---

### Phase 2: API Lookup Tool

**Timeline:** Week 1, Days 3-4
**Purpose:** Add token-efficient API documentation lookup capability

#### Commands

```bash
git checkout -b phase2-apilookup phase1-role-deduplication

# Cherry-pick apilookup tool
git cherry-pick 5bea595

# If there are follow-up fixes, cherry-pick them too
git cherry-pick 1918679  # docs fix
git cherry-pick 97ba7e4  # prompt improvement for apilookup
```

#### Post-Integration Steps

```bash
# Verify tool is registered
grep -r "apilookup" tools/__init__.py

# Check for any missing dependencies
grep -r "import" tools/apilookup.py
```

#### Testing

```bash
# Linting
./code_quality_checks.sh

# Unit tests (apilookup should be simple, no complex tests needed)
python -m pytest tests/ -v -k "apilookup or lookup"

# Manual test via simulator
cat > test_apilookup_manual.py << 'EOF'
import asyncio
from tools.apilookup import LookupTool

async def test_lookup():
    tool = LookupTool()
    result = await tool.run({
        "prompt": "Latest React 19 features",
        "model": "google/gemini-2.5-flash"
    })
    print(f"Result: {result}")

asyncio.run(test_lookup())
EOF

python test_apilookup_manual.py
```

#### Success Criteria

- [ ] `apilookup` tool registered and available
- [ ] Tool description appears in tool list
- [ ] Manual test successfully delegates to web search
- [ ] No token leakage (verify it uses sub-process pattern)

---

### Phase 3: CLI Integration Foundation

**Timeline:** Week 2, Days 1-3
**Purpose:** Add `clink` infrastructure for CLI delegation

#### Commands

```bash
git checkout -b phase3-clink-foundation phase2-apilookup

# Cherry-pick main clink implementation
git cherry-pick a2ccb48  # feat!: Huge update - Link another CLI
```

#### Critical Files to Review

This commit will add:
- `tools/clink.py` - Main CLI bridge tool
- `clink/` directory - CLI agent infrastructure
- Configuration updates for CLI clients

#### Conflict Resolution Strategy

```bash
# If conflicts in tools/__init__.py
# 1. Accept upstream changes for clink
# 2. Ensure critical_engineer, testguard, registry remain registered
# 3. Merge both sets of tools

# If conflicts in config.py
# 1. Keep hestai's schema optimization settings
# 2. Add zen's CLI configuration variables
# 3. Merge both configurations
```

#### Post-Integration

```bash
# Verify clink infrastructure exists
ls -la clink/

# Check tool registration
python -c "from tools import get_all_tools; [print(t.get_name()) for t in get_all_tools() if 'clink' in t.get_name()]"
```

#### Testing

```bash
./code_quality_checks.sh

# Check clink tool is available
python communication_simulator_test.py --individual basic_conversation --verbose

# Verify clink doesn't break existing tools
python communication_simulator_test.py --quick
```

#### Success Criteria

- [ ] `clink/` directory structure in place
- [ ] `clink` tool registered
- [ ] No regression in existing tools
- [ ] HestAI-specific tools still present (critical_engineer, testguard, registry)

---

### Phase 4: Codex CLI Integration

**Timeline:** Week 2, Days 4-5
**Purpose:** Enable Codex CLI delegation

#### Commands

```bash
git checkout -b phase4-codex-cli phase3-clink-foundation

# Cherry-pick Codex CLI support
git cherry-pick 561e4aa  # feat: support for codex as external CLI

# Cherry-pick Codex web-search support
git cherry-pick 97ba7e4  # feat: codex supports web-search
git cherry-pick ba348e3  # docs: instructions for enabling web-search
```

#### Configuration Required

```bash
# Update .env.example to document Codex CLI support
# Add instructions for enabling Codex web-search
```

#### Testing

```bash
./code_quality_checks.sh

# If you have Codex CLI installed, test delegation
# Create test script
cat > test_codex_delegation.py << 'EOF'
import asyncio
from tools.clink import CLinkTool

async def test_codex():
    tool = CLinkTool()
    result = await tool.run({
        "prompt": "Review this code for security issues: print('hello')",
        "cli_name": "codex",
        "role": "code-reviewer",
        "model": "anthropic/claude-sonnet-4"
    })
    print(f"Codex delegation result: {result}")

if __name__ == "__main__":
    asyncio.run(test_codex())
EOF

# Only if Codex CLI is configured
python test_codex_delegation.py
```

#### Success Criteria

- [ ] Codex CLI configuration documented
- [ ] `clink` tool can delegate to Codex
- [ ] Web-search delegation works (if Codex configured)
- [ ] No regression in other CLI support (Gemini, Qwen)

---

### Phase 5: Preserve HestAI Enhancements

**Timeline:** Week 3, Days 1-2
**Purpose:** Ensure hestai-specific improvements are retained

#### Critical Review

```bash
git checkout phase4-codex-cli

# Compare challenge.py - hestai's version has better description
diff .integration-backup/challenge.py tools/challenge.py

# If upstream overwrote hestai's improvements, restore them
cp .integration-backup/challenge.py tools/challenge.py
git add tools/challenge.py
git commit -m "fix: preserve HestAI's enhanced challenge tool description"
```

#### Verify HestAI Tools Still Work

```bash
# Test critical-engineer
python -c "from tools.critical_engineer import CriticalEngineerTool; print(CriticalEngineerTool().get_name())"

# Test testguard
python -c "from tools.testguard import TestGuardTool; print(TestGuardTool().get_name())"

# Test registry
python -c "from tools.registry import RegistryTool; print(RegistryTool().get_name())"
```

#### Testing

```bash
# Full test suite
./code_quality_checks.sh

# Test HestAI-specific workflows
python communication_simulator_test.py --individual cross_tool_continuation --verbose

# Verify all tools are registered
python -c "from tools import get_all_tools; tools = sorted([t.get_name() for t in get_all_tools()]); print('\n'.join(tools))" > current-tools-integrated.txt

# Compare with backup
diff .integration-backup/current-tools.txt current-tools-integrated.txt
```

#### Expected New Tools

```
+ apilookup
+ clink
(All other tools should remain)
```

#### Success Criteria

- [ ] critical-engineer, testguard, registry still functional
- [ ] challenge.py has HestAI's enhanced description
- [ ] Schema optimization features preserved
- [ ] All tools registered correctly

---

### Phase 6: Integration Testing & Validation

**Timeline:** Week 3, Days 3-5
**Purpose:** Comprehensive validation of all features

#### Comprehensive Test Suite

```bash
# 1. Code quality checks
./code_quality_checks.sh

# 2. Unit tests
python -m pytest tests/ -v

# 3. Integration tests
./run_integration_tests.sh

# 4. Quick simulator tests
python communication_simulator_test.py --quick --verbose

# 5. Full simulator test suite
./run_integration_tests.sh --with-simulator

# 6. Individual critical tests
python communication_simulator_test.py --individual cross_tool_continuation --verbose
python communication_simulator_test.py --individual consensus_workflow_accurate --verbose
python communication_simulator_test.py --individual codereview_validation --verbose
```

#### Functional Validation

```bash
# Test new features
# 1. Test apilookup
echo "Testing apilookup..."
# Use via MCP or create manual test

# 2. Test clink (if Gemini CLI configured)
echo "Testing clink with Gemini..."
# Manual test or simulator

# 3. Test clink with Codex
echo "Testing clink with Codex..."
# Manual test or simulator

# Test HestAI features still work
# 4. Test critical-engineer
echo "Testing critical-engineer..."
# Manual architectural validation test

# 5. Test testguard
echo "Testing testguard..."
# Manual test methodology validation
```

#### Performance Validation

```bash
# Verify token optimization still works
grep -r "USE_SCHEMA_REFS" tests/
python -m pytest tests/ -v -k "schema"

# Check MCP response sizes
# Run sample tools and verify token counts haven't exploded
```

#### Success Criteria

- [ ] All code quality checks pass (100%)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Quick simulator tests: 6/6 pass
- [ ] Full simulator suite passes
- [ ] No performance regression (token counts similar to baseline)
- [ ] New tools (apilookup, clink) functional
- [ ] HestAI tools (critical-engineer, testguard, registry) functional

---

### Phase 7: Documentation & Finalization

**Timeline:** Week 4, Days 1-2
**Purpose:** Update documentation and create migration notes

#### Update Documentation

```bash
# Update CLAUDE.md
cat >> CLAUDE.md << 'EOF'

### New Tools Added from Zen-MCP-Server

#### API Lookup Tool

The `apilookup` tool provides token-efficient API documentation lookup by delegating to web search in a subprocess.

**Usage:**
```python
{
  "tool": "apilookup",
  "prompt": "Latest React 19 features and breaking changes"
}
```

#### CLI Integration (clink)

The `clink` tool enables delegation to external AI CLIs (Gemini CLI, Codex CLI, Qwen CLI) to preserve Claude Code quota.

**Usage:**
```python
{
  "tool": "clink",
  "prompt": "Review this code for bugs",
  "cli_name": "codex",
  "role": "code-reviewer"
}
```

**Benefits:**
- Preserve Claude Code weekly quota by delegating to free CLIs
- Gemini CLI: 1000 free requests/day
- Codex CLI: Use existing Codex subscription
- Maintain shared context across CLI delegations

EOF

# Update README.md
# Document new capabilities

# Create migration notes
cat > docs/UPSTREAM_INTEGRATION_NOTES.md << 'EOF'
# Upstream Integration: Zen-MCP-Server v7.4.0

## Integration Date
[Date]

## Features Adopted
1. **apilookup tool** - Token-efficient API documentation lookup
2. **clink tool** - CLI integration for Gemini/Codex/Qwen delegation
3. **Role deduplication refactor** - Cleaner role management
4. **Codex CLI support** - Native Codex CLI integration

## HestAI Features Preserved
1. **critical-engineer tool** - Architectural validation
2. **testguard tool** - Test methodology enforcement
3. **registry tool** - Approval workflow system
4. **Schema optimization** - Token reduction via schema consolidation
5. **Enhanced challenge.py** - Improved automatic invocation rules

## Testing Results
[Paste test results here]

## Known Issues
[Document any known issues or limitations]

## Rollback Procedure
```bash
git checkout main
git reset --hard pre-upstream-integration-[DATE]
git push origin main --force
```
EOF
```

#### Success Criteria

- [ ] CLAUDE.md updated with new tools
- [ ] README.md updated
- [ ] Migration notes documented
- [ ] All new features explained
- [ ] Rollback procedure documented

---

### Phase 8: Merge & Deploy

**Timeline:** Week 4, Days 3-4
**Purpose:** Finalize integration and merge to main

#### Pre-Merge Checklist

```bash
# Ensure all tests pass one final time
./code_quality_checks.sh
./run_integration_tests.sh
python communication_simulator_test.py --quick

# Review all changes
git log --oneline upstream-integration-staging..phase4-codex-cli

# Create comprehensive PR description
```

#### Merge Strategy

```bash
# Squash or preserve commit history?
# Recommendation: Squash into logical commits

git checkout upstream-integration-staging
git merge --squash phase4-codex-cli

# Create meaningful commits
git commit -m "feat: integrate apilookup tool from zen-mcp-server v7.2.0

- Add token-efficient API documentation lookup
- Uses subprocess pattern to avoid MCP context pollution
- Supports latest API/SDK version research
- Related commits: 5bea595, 1918679, 97ba7e4"

git commit -m "feat: integrate clink CLI delegation from zen-mcp-server v7.0.0

- Add clink tool for external CLI integration
- Support Gemini CLI, Codex CLI, Qwen CLI delegation
- Enables token preservation via free CLI usage
- Maintains shared context across CLI calls
- Related commits: a2ccb48, 561e4aa, c42e9e9"

git commit -m "fix: preserve HestAI enhancements post-integration

- Retain enhanced challenge.py description
- Ensure critical-engineer, testguard, registry tools functional
- Preserve schema optimization features
- Maintain project-aware context isolation"
```

#### Create Pull Request

```bash
# Push integration branch
git push origin upstream-integration-staging

# Create PR via gh CLI
gh pr create \
  --title "feat: Integrate Zen-MCP-Server v7.4.0 features (apilookup, clink, Codex CLI)" \
  --body "$(cat << 'EOF'
## Overview
Integrates valuable features from upstream zen-mcp-server (v7.0.0 - v7.4.0) while preserving all HestAI-specific enhancements.

## New Features Added
- ✅ **apilookup tool**: Token-efficient API documentation lookup via subprocess
- ✅ **clink tool**: CLI integration for Gemini/Codex/Qwen delegation
- ✅ **Codex CLI support**: Native integration with Codex subscription
- ✅ **Role deduplication**: Cleaner role management architecture

## HestAI Features Preserved
- ✅ critical-engineer tool
- ✅ testguard tool
- ✅ registry tool
- ✅ Schema optimization (token reduction)
- ✅ Enhanced challenge.py
- ✅ Project-aware context isolation

## Testing
- [x] Code quality checks: PASS
- [x] Unit tests: PASS
- [x] Integration tests: PASS
- [x] Quick simulator tests: 6/6 PASS
- [x] Full simulator suite: PASS
- [x] No performance regression

## Benefits
- **Token Preservation**: Delegate to free Gemini CLI (1000 req/day)
- **Codex Integration**: Use existing Codex subscription efficiently
- **API Lookup**: Current documentation without context pollution
- **Maintained Quality**: All HestAI enhancements preserved

## Rollback Plan
Tagged as `pre-upstream-integration-[DATE]` for easy rollback if needed.

## Related Issues
Closes #XX (if applicable)
EOF
)"

# Request reviews
gh pr edit --add-reviewer @relevant-reviewer
```

#### Post-Merge

```bash
# Merge to main
gh pr merge --squash --delete-branch

# Tag the release
git checkout main
git pull origin main
git tag v7.4.0-hestai.1
git push origin v7.4.0-hestai.1

# Update CHANGELOG.md
```

---

## Testing Strategy Matrix

| Phase | Tests Required | Success Criteria |
|-------|----------------|------------------|
| **Phase 1: Role Dedup** | Quick sim (6 tests), Unit tests | All pass, no role regression |
| **Phase 2: apilookup** | Linting, Manual test | Tool registered, web delegation works |
| **Phase 3: clink Foundation** | Quick sim, Full unit tests | clink tool available, no tool breakage |
| **Phase 4: Codex CLI** | Codex delegation test (if available) | Codex integration functional |
| **Phase 5: HestAI Preserve** | Cross-tool continuation, Tool registration | All HestAI tools functional |
| **Phase 6: Integration** | **ALL TESTS** | 100% pass rate across all test suites |
| **Phase 7: Documentation** | Documentation review | Docs complete and accurate |
| **Phase 8: Merge** | Final test run | Ready for production |

---

## Rollback Procedures

### Immediate Rollback (any phase)

```bash
# Return to pre-integration state
git checkout main
git reset --hard pre-upstream-integration-$(date +%Y%m%d)

# If already pushed
git push origin main --force

# Verify rollback
./code_quality_checks.sh
python communication_simulator_test.py --quick
```

### Selective Rollback (specific phase)

```bash
# Return to previous phase
git checkout upstream-integration-staging
git branch -D phase4-codex-cli  # or whichever phase failed
git checkout phase3-clink-foundation  # previous successful phase
```

### File-Level Rollback

```bash
# Restore specific hestai file
cp .integration-backup/critical_engineer.py tools/
git add tools/critical_engineer.py
git commit -m "fix: restore HestAI critical-engineer implementation"
```

---

## Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Tool registration conflicts** | MEDIUM | HIGH | Careful `tools/__init__.py` merge, extensive testing |
| **Schema optimization breakage** | LOW | HIGH | Preserve schema tests, verify token counts |
| **HestAI tool breakage** | LOW | CRITICAL | Backup files, test after each phase |
| **Configuration conflicts** | MEDIUM | MEDIUM | Manual config.py merge, verify all settings |
| **Dependency incompatibilities** | LOW | MEDIUM | Test after each cherry-pick |
| **MCP token increase** | MEDIUM | HIGH | Monitor token usage, verify schema refs still work |

---

## Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| **Week 1** | Phases 1-2 | Role dedup + apilookup integrated |
| **Week 2** | Phases 3-4 | clink + Codex CLI integrated |
| **Week 3** | Phases 5-6 | HestAI preserved + testing complete |
| **Week 4** | Phases 7-8 | Documentation + merge to main |

**Total Duration:** ~4 weeks (conservative estimate)
**Fast Track:** ~2 weeks (if no major conflicts)

---

## Upstream Commit Reference

### Key Commits to Cherry-Pick

| Commit | Description | Phase |
|--------|-------------|-------|
| `c42e9e9` | Role deduplication refactor | Phase 1 |
| `5bea595` | apilookup tool | Phase 2 |
| `1918679` | apilookup docs fix | Phase 2 |
| `97ba7e4` | apilookup prompt improvement | Phase 2 |
| `a2ccb48` | clink tool (CLI integration) | Phase 3 |
| `561e4aa` | Codex CLI support | Phase 4 |
| `ba348e3` | Codex web-search docs | Phase 4 |

---

## Next Steps

**Ready to begin integration?** Choose your approach:

1. **Start Phase 0 now** - Create branches, backups, and document baseline
2. **Begin Phase 1** - Execute role deduplication integration immediately
3. **Generate detailed cherry-pick commands** - Create a ready-to-execute script for all phases
4. **Review specific conflicts** - Deep-dive into anticipated merge conflicts before starting
5. **Custom approach** - Tailor the plan based on specific requirements

This plan provides a **systematic, tested, rollback-safe** path to integrate all valuable zen-mcp-server features while preserving every HestAI enhancement. Each phase is independently testable with clear success criteria.
