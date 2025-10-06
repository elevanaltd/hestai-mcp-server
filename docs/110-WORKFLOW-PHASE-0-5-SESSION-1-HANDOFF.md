# 110-DOC-PHASE-0.5-SESSION-1-HANDOFF

**Session Type:** Zen-MCP-Server Integration - Phase 0.5 Foundation Sync
**Session Date:** 2025-10-06
**Current Phase:** Phase 0.5 - Foundation Sync (IN PROGRESS)
**Branch:** `sync/01-base-tool-shim`

---

## Session 1 Summary

### Completed Work

#### 1. Baseline Stabilization ✅
**Problem Found:** HestAI's `pyproject.toml` incorrectly declared `google-genai>=1.19.0` while actual code uses deprecated `google.generativeai>=0.8.0` (package mismatch bug).

**Solution:**
- Fixed `pyproject.toml` to align with reality: `google-genai` → `google-generativeai`
- Committed fix: `8b1e155` - "fix(deps): align dependency files to reflect current Gemini provider implementation"
- Merged to `upstream-integration-staging`

**Validation:**
- Dependencies installed successfully
- All 926+ tests passing with corrected dependencies

#### 2. Integration Plan Updated ✅
**New Phase Inserted:** Phase 0.75 - Gemini SDK Migration

**Rationale:** Per critical-engineer mandate, isolate high-risk provider migration (467→558 lines, NEW SDK API changes) into separate phase AFTER Foundation Sync but BEFORE feature porting.

**Committed:** `d6a8ab8` - "docs: insert Phase 0.75 (Gemini SDK Migration) per critical-engineer mandate"

#### 3. Base Tool Analysis & Validation ✅
**Diff Analysis:**
- Generated 903-line diff between HestAI and Zen upstream `base_tool.py`
- Identified potential breaking change: `get_websearch_instruction` signature change
  - OLD: `get_websearch_instruction(self, use_websearch: bool, tool_specific: Optional[str] = None)`
  - NEW: `get_websearch_instruction(self, tool_specific: Optional[str] = None)` (removed `use_websearch`)

**Validation Test (Critical Finding):**
- Added temporary `RuntimeError` to method per critical-engineer protocol
- Test result: **15+ tests FAILED** - method IS actively called by tools
- Failures include: `test_auto_mode.py`, `test_large_prompt_handling.py`, `test_directory_expansion_tracking.py`

**Conclusion:**
- Signature change is BREAKING
- "Port and Verify" shortcut REJECTED
- Full "Shim and Sync" protocol MANDATORY

### Critical-Engineer Consultations

1. **Phase 0.5 Execution Strategy** (continuation_id: `f8d4ee8a-a1b3-4dfd-92a1-203448eda2c0`)
   - Original recommendation: "Shim and Sync" approach
   - 5 components: Dependencies → Base Tool → Config → Utils → Server
   - Component-by-component with validation gates

2. **Dependency Migration Strategy**
   - Discovered package mismatch bug
   - Mandated: "Stabilize, Sync, then Migrate"
   - Phase 0.75 inserted for isolated provider migration

3. **Base Tool Merge Strategy**
   - Attempted simplification to "Port and Verify"
   - RuntimeError validation PROVED breaking change exists
   - Confirmed: Full "Shim and Sync" protocol required

---

## Current State

### Git Status
- **Branch:** `sync/01-base-tool-shim`
- **Latest Commit:** `d6a8ab8` (integration plan update)
- **Parent Branch:** `upstream-integration-staging`
- **Baseline:** Stable (8b1e155 - dependency fix merged)

### Upstream Comparison
- Fresh clone: `/tmp/zen-upstream-analysis`
- Diff file: `/tmp/base_tool.diff` (903 lines)
- Breaking change identified and validated

### Test Status
- **Baseline:** 926+ tests passing (with corrected dependencies)
- **Validation Test:** Temporarily added RuntimeError - PROVED breaking change
- **Current:** RuntimeError reverted, ready for shim implementation

---

## Next Session Tasks

### STEP 2: Base Tool Shim Implementation

**Critical-Engineer Protocol:** Full "Shim and Sync" execution required

#### Task Sequence

**1. Create Schema Snapshot Test** (FIRST - Safety Net)
```bash
# Create snapshot directory
mkdir -p tests/snapshots

# Create test: tests/test_base_tool_schema_snapshot.py
# Purpose: Capture current schema generation behavior
# Validate: Load 2-3 complex tools (critical-engineer, consensus, debug)
# Generate: Call get_model_field_schema() on each tool
# Save: Baseline JSON snapshots
# Test: Future runs must match snapshots exactly

# Commit BEFORE making changes to base_tool.py
git add tests/snapshots/ tests/test_base_tool_schema_snapshot.py
git commit -m "test(sync): Add schema snapshot validation for base_tool.py"
```

**2. Build Compatibility Shim**
```python
# In tools/shared/base_tool.py (manual editing required)

# Add consultation evidence at top of file (near imports):
# // Critical-Engineer: consulted for Base tool abstraction merge strategy

# Create backward-compatible wrapper:
# DEPRECATED: Maintained for backward compatibility with existing tools
# TODO: Refactor all tool calls post-integration and remove this wrapper
def get_websearch_instruction(self, use_websearch: bool, tool_specific: Optional[str] = None) -> str:
    """Shim for backward compatibility."""
    return self._internal_get_websearch_instruction(tool_specific if use_websearch else None)

# NEW internal implementation (port from upstream)
def _internal_get_websearch_instruction(self, tool_specific: Optional[str] = None) -> str:
    # ... Port upstream logic from /tmp/zen-upstream-analysis/tools/shared/base_tool.py
    pass
```

**3. Manual Three-Way Merge**
- Port `get_model_field_schema()` refactoring (broken into 6 helper methods)
- Preserve HestAI-specific modifications
- Add new helper methods: `_format_available_models_list()`, `_collect_ranked_capabilities()`, etc.
- Ensure no HestAI logic is lost during merge

**4. Validation Gauntlet**
```bash
# MUST PASS 100%:
# 1. Schema snapshot test
python -m pytest tests/test_base_tool_schema_snapshot.py -v

# 2. Full quality checks
./code_quality_checks.sh

# 3. HestAI regression suite
python -m pytest tests/test_critical_engineer.py tests/test_testguard.py tests/test_registry.py -v

# 4. Quick simulator
python communication_simulator_test.py --quick

# All 926+ tests must pass
python -m pytest tests/ -v -m "not integration"
```

**5. Commit & Merge**
```bash
git add tools/shared/base_tool.py tests/
git commit -m "feat(sync): Port upstream base_tool.py with compatibility shim

- Add backward-compatible wrapper for get_websearch_instruction
- Port upstream refactoring of get_model_field_schema() into helper methods
- Preserve HestAI-specific logic via three-way merge
- Schema snapshot tests confirm behavioral parity
- All 926+ tests passing

// Critical-Engineer: consulted for Base tool abstraction merge strategy"

# Merge to staging
git checkout upstream-integration-staging
git merge --no-ff sync/01-base-tool-shim -m "merge: base tool shim (Stage 1 complete)"
git branch -d sync/01-base-tool-shim
```

---

## Remaining Phase 0.5 Components

After base tool shim complete:

### STEP 3: Config Merge
- Merge `config.py` schemas (don't replace)
- Keep HestAI schema optimization settings
- Add Zen config variables with safe defaults

### STEP 4: Utils Sync
- Compare `utils/` directory
- Merge changes carefully (session management, file processing, provider routing)

### STEP 5: Server Sync
- Compare `server.py` (middleware, registration)
- Add consultation evidence comment
- Validate tool registration

### Final Validation
- All 926+ tests passing
- HestAI regression suite passing
- Quick simulator: 6/6 passing
- All 18 tools load successfully

---

## Key Files & Locations

| File | Path | Purpose |
|------|------|---------|
| Integration Plan | `docs/107-DOC-ZEN-INTEGRATION-PLAN.md` | Complete 8-phase plan (updated with Phase 0.75) |
| Phase 0 Report | `docs/108-DOC-PHASE-0-COMPLETION-REPORT.md` | Phase 0 execution summary |
| Phase 0 Handoff | `docs/109-DOC-SESSION-HANDOFF.md` | Quick start for Phase 0.5 |
| This Handoff | `docs/110-DOC-PHASE-0.5-SESSION-1-HANDOFF.md` | Session 1 progress & next steps |
| Base Tool Diff | `/tmp/base_tool.diff` | 903-line diff for analysis |
| Upstream Clone | `/tmp/zen-upstream-analysis/` | Fresh upstream for comparison |
| Backup Files | `.integration-backup/` | Original HestAI files |

---

## Critical-Engineer Guidance

**Core Principle:** "Build systems that don't break"

**Validation Question:** "What will break this in production?"

**Process Adherence:**
- ✅ Data-driven decisions (RuntimeError test proved breaking change)
- ✅ Defense in depth (schema snapshots before merging)
- ✅ Isolation (component-by-component sync)
- ✅ Validation gates (100% test pass required at each step)

**Key Insights:**
1. Trust but verify - `grep` missed dynamic calls, `RuntimeError` caught them
2. No shortcuts on breaking changes - Full protocol prevents production breaks
3. Three-way merge (not copy) - Preserves both histories
4. Evidence-based engineering - Test failures are data, not annoyances

---

## Session Continuation Prompt

```
I'm continuing Phase 0.5 Foundation Sync from Session 1.

Context documents:
- Integration Plan: docs/107-DOC-ZEN-INTEGRATION-PLAN.md
- Session 1 Handoff: docs/110-DOC-PHASE-0.5-SESSION-1-HANDOFF.md

Current state:
- Branch: sync/01-base-tool-shim (ready for shim implementation)
- Baseline: Stable (dependencies fixed, 926+ tests passing)
- Validation: Breaking change PROVED via RuntimeError test

Next task: STEP 2 - Base Tool Shim Implementation
1. Create schema snapshot test (safety net)
2. Build compatibility shim for get_websearch_instruction
3. Manual three-way merge of upstream logic
4. Validation gauntlet (100% pass required)

Critical-engineer continuation_id: f8d4ee8a-a1b3-4dfd-92a1-203448eda2c0

Start by reading docs/110-DOC-PHASE-0.5-SESSION-1-HANDOFF.md for complete context.
```

---

**Status:** Ready for Session 2 - Base Tool Shim Implementation
**Token Budget:** Full budget available for complex manual porting work
**Risk Level:** Managed - Breaking change identified, mitigation strategy validated
