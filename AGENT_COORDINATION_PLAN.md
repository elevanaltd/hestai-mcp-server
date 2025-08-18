# MULTI-AGENT COORDINATION PLAN
## Post-Rebranding System Recovery

**WORKSPACE_ARCHITECT COORDINATION AUTHORITY**

### SITUATION ASSESSMENT
**CRITICAL ISSUES IDENTIFIED:**
1. **Import Error**: `cannot import name 'CODEREVIEW_PROMPT' from 'systemprompts'`
2. **Missing Virtual Environment**: `.hestai_venv` not found
3. **Wrapper Script Failure**: Python executable path invalid

### AGENT DEPLOYMENT STRATEGY

#### PHASE 1: ROOT CAUSE ANALYSIS
**Agent**: `error-resolver` (Component-level error resolution)
**Task**: Systematic investigation of import failures and missing components
**Priority**: CRITICAL
**Expected Output**: Complete diagnostic report with fix recommendations

#### PHASE 2: ENVIRONMENT RESTORATION  
**Agent**: `workspace-architect` (B1_02 setup specialist)
**Task**: Rebuild virtual environment with correct naming and paths
**Priority**: HIGH
**Expected Output**: Working `.hestai_venv` with all dependencies

#### PHASE 3: CODE INTEGRITY VALIDATION
**Agent**: `code-review-specialist` (Code quality enforcement)
**Task**: Validate all Python imports and module structure post-rebranding
**Priority**: HIGH  
**Expected Output**: Fixed import paths and validated code integrity

#### PHASE 4: PRODUCTION READINESS
**Agent**: `critical-engineer` (Production readiness validator)
**Task**: Comprehensive system validation and architectural assessment
**Priority**: MEDIUM
**Expected Output**: Production readiness certification

#### PHASE 5: INTEGRATION TESTING
**Agent**: `universal-test-engineer` (Testing specialist)
**Task**: Execute comprehensive test suite to validate all functionality
**Priority**: MEDIUM
**Expected Output**: 90% test coverage with all critical paths verified

### COORDINATION PROTOCOL
1. **Sequential Execution**: Agents deployed in phase order
2. **Handoff Requirements**: Each agent must provide clear deliverables to next
3. **Quality Gates**: No progression without phase completion
4. **Rollback Strategy**: Maintain git checkpoints between phases

### SUCCESS CRITERIA
- ✅ All Python imports resolve correctly
- ✅ Virtual environment rebuilds and activates
- ✅ Wrapper scripts execute without errors
- ✅ Test suite passes with >80% coverage
- ✅ Server starts and responds to basic requests