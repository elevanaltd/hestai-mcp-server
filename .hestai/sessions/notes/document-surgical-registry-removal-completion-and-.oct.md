## Session: Testguard/Registry Cleanup & #17 Testing Validation Strategy

**Date:** 2025-12-10
**Focus:** Tech debt removal + integration planning
**Status:** COMPLETED

### Work Completed

#### 1. Comprehensive Blocking Patterns Audit
- Mapped 15+ PreToolUse hooks already in place
- Identified SubagentStop hook gap (currently skipped due to workspace trust)
- Found clear exit-code enforcement pattern (exit 2 = block)

#### 2. Testguard vs TMG Capability Analysis
**Key Finding:** TMG (via clink) is the superset
- TMG: Full codebase access, CLI environment, explicit BLOCKING authority, can research/execute
- Testguard: File-only input, snapshot analysis, advisory tokens
- Critical difference: TMG can *verify claims* by running tests; testguard can only *suggest*

**Recommendation:** Use TMG for #17, not testguard (TMG is strictly more capable)

#### 3. Issue #17 Blocking vs Advisory Decision (via TMG role)
- **BLOCKING:** Skipped tests, assertion weakening, mutation testing gaps (Tier-2 only)
- **ADVISORY:** Coverage gaming (diagnostic only, not a gate)
- **Rationale:** High risk + cheap detection = blocking; slow/probabilistic = advisory

#### 4. Surgical Registry Removal (EXECUTED)
**Completed by implementation-lead via Task(opus):**
- ✅ Deleted 7 files: tools/registry.py + 6 test files
- ✅ Modified 3 files: server.py, critical_engineer.py, testguard.py
- ✅ All tests pass (exit code 0)
- ✅ No cascade failures
- ✅ Preserved testguard fallback token generation (lines 592-599)
- ✅ Preserved critical_engineer functionality

**What was lost:** Registry audit trail, token spend validation
**What was kept:** Token generation, validation workflows, testguard/critical_engineer operational capability

#### 5. Removal Feasibility Assessment
- testguard removal: Easy (~60 min) - replaced by TMG + bash hooks
- critical_engineer removal: Easy (~30-45 min) - but NOT deprecated (still actively used)
- registry removal: DONE - surgical, no breakage

### Decision Tree: Next Steps

**Option A: TMG-Based (Recommended)**
- Enhance TMG prompt for #17 anti-patterns
- Add TMG job to CI (parallel with tests)
- Fail PRs on violations
- Add optional web research to TMG for mutation testing frameworks

**Option B: Bash Hooks Only**
- Simple regex patterns for `.skip`, `describe.only`, `vi.todo`
- Test-file-pairing validation
- Minimal complexity, local + CI

**Option C: Hybrid (Best Balance)**
- Local: Fast bash hooks for syntax patterns
- CI: TMG for semantic analysis + mutation testing
- Web research: TMG can fetch mutation framework docs when needed

### Pending Decisions
1. **Which option for #17?** (A/B/C)
2. **Scope:** eav-monorepo only or all HestAI projects?
3. **Timeline:** Integrate with Stryker mutation work or phased?
4. **Critical_engineer:** Keep as-is or retire?

### Tech Debt Eliminated
- Removed 618 lines from registry.py
- Removed 6 test files (~30 KB)
- Eliminated convoluted hook-registry-token-approval workflow
- Cleaned up testguard/critical_engineer dependencies
- Ready for cleaner #17 implementation

### Codebase Health Post-Removal
- ✅ No cascade failures
- ✅ All remaining tests pass
- ✅ Imports clean
- ✅ Server boots correctly
- ❌ Pre-existing clink config issue (agent-model-tiers.json) - unrelated to removal

### Next Phase: #17 Integration
**Recommended workflow:**
1. Clarify blocking/advisory strategy (Option A/B/C decision)
2. Design CI integration (GitHub Actions workflow)
3. Implement deterministic gates (bash hooks)
4. Wire TMG into CI if chosen
5. Add mutation testing integration
6. Test on eav-monorepo PR workflow
7. Document anti-patterns detected vs #17 requirements