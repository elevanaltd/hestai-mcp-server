# PROJECT CONTEXT

## IDENTITY
NAME::HestAI MCP Server
TYPE::Model Context Protocol (MCP) Server
PURPOSE::"Orchestrate multiple AI models (Claude, Gemini, etc.) for enhanced code analysis, problem-solving, and collaborative development."
ORIGIN::"Fork of zen-mcp-server by Beehive Innovations, rebranded/modified by Elevana Ltd."

## ARCHITECTURE
CORE_PRINCIPLE::"Human-in-the-loop AI orchestration where Claude/Gemini CLI stays in control but leverages specialized models for subtasks."
KEY_COMPONENTS::[
  "HestAI MCP Server (Python)",
  "Tools (chat, clink, consensus, analyze, tracer, secaudit)",
  "CLI Integration (clink) - delegates to external AI CLIs",
  "Context Steward - Session lifecycle management"
]
INTEGRATION_STATUS::"Context Steward v2 in development"
RUNTIME_DEPENDENCIES::[
  "python>=3.9",
  "mcp>=1.0.0",
  "google-generativeai>=0.8.0",
  "openai>=1.55.2",
  "pydantic>=2.0.0",
  "python-dotenv>=1.0.0",
  "pyyaml>=6.0.0"
]

## CURRENT_STATE
DATE::2025-12-10
ACTIVE_FOCUS::"Context Steward v2 - Complete Clockout Flow (#104)"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4

RECENT_ACHIEVEMENTS::[
  "#107 history_archive persistence FIXED (PR #111 - pending CI)",
  "#104 Clockout verification gate implemented (CE: GO)",
  "OCTAVE compression at clockout WORKING",
  "1258 tests passing (full suite)",
  "CRS review: 3 issues fixed (artifact type, path traversal, blocking gate)"
]

NEXT_PRIORITY::"Complete clockout flow - AI-driven context_update to PROJECT-CONTEXT"

## CLOCKOUT_FLOW_STATUS
INTENDED_FLOW::[
  "1. Session transcript created → WORKING",
  "2. OCTAVE compression by AI → WORKING (see archive/{session_id}-octave.oct.md)",
  "3. context_update by AI → NOT_IMPLEMENTED (clockout doesn't call context_update)",
  "4. PROJECT-CONTEXT updated → NOT_IMPLEMENTED (depends on step 3)"
]

GAP_ANALYSIS::[
  "clockout.py creates transcript + OCTAVE compression",
  "BUT: clockout does NOT call context_update to merge session insights into PROJECT-CONTEXT",
  "RESULT: Session wisdom stays in archive, doesn't flow to PROJECT-CONTEXT automatically"
]

IMPLEMENTATION_NEEDED::[
  "After OCTAVE compression succeeds:",
  "  1. Extract context-worthy items from OCTAVE (DECISIONS, OUTCOMES, BLOCKERS)",
  "  2. Call context_update with extracted content",
  "  3. AI merges into PROJECT-CONTEXT.md",
  "  4. If compaction triggered, history_archive now persists (PR #111)"
]

PHASE_STATUS::[
  "Phase 1 Foundation: COMPLETE",
  "Phase 2 AI Intelligence: COMPLETE",
  "Phase 3 Deprecation: #92 TODO",
  "Phase 4 Validation: #93 UNBLOCKED (pending PR #111 merge)"
]

## AUTHORITY
CURRENT_OWNER::implementation-lead
PHASE::B2[Build Phase - Implementation]
ACCOUNTABLE_TO::critical-engineer[via holistic-orchestrator]

QUALITY_GATES::[
  lint::"passing",
  typecheck::"passing",
  test::"72/72 passing (clockout + context_update)"
]

## DEVELOPMENT_GUIDELINES
STYLE::"Follow existing project conventions (formatting, naming)."
TESTING::"Run tests via `run_integration_tests.sh` or `pytest`. Ensure 100% pass rate."
DOCUMENTATION::"Maintain strict documentation standards. Update docs/ when features change."
CONSTITUTION::"Adhere to System-Steward constitutional principles (Observation, Preservation, Patterns)."

## QUICK_REFERENCES

### Specifications
SPEC::".hestai/workflow/CONTEXT-STEWARD-V2-SPEC.oct.md"
CRITICAL_ASSESSMENT::".hestai/reports/800-REPORT-CRITICAL-ENGINEER-CONTEXT-STEWARD-ASSESSMENT.md"
VISIBILITY_RULES::".hestai/rules/VISIBILITY-RULES.md"

### Context Files
PROJECT_CONTEXT::".hestai/context/PROJECT-CONTEXT.md"[this file]
STATE_VECTOR::".hestai/context/current_state.oct"[Phase 0 deliverable]
CONTEXT_NEGATIVES::".hestai/context/CONTEXT-NEGATIVES.oct"[Phase 0 deliverable]
CHANGELOG::".hestai/context/PROJECT-CHANGELOG.md"
ROADMAP::".hestai/context/PROJECT-ROADMAP.md"
HISTORY::".hestai/context/PROJECT-HISTORY.md"

### Validator Components (Kernel)
VALIDATOR::"/tools/context_steward/context_validator.py"
SCHEMAS::"/tools/context_steward/schemas.py"
TESTS::"/tests/test_context_validator.py"

### Quality Commands
CODE_QUALITY::"./code_quality_checks.sh"
INTEGRATION_TESTS::"./run_integration_tests.sh"
UNIT_TESTS::"pytest tests/ -v -m 'not integration'"

## MCP_TOOL_STATUS

### Active Tools
CLOCKIN::"Session registration and context initialization"[implemented]
CLOCKOUT::"Session archival and transcript extraction"[implemented]
ANCHORSUBMIT::"Agent anchor validation"[implemented]
REQUESTDOC::"Documentation routing and placement"[deprecated→use_document_submit]
CHAT::"Multi-model conversation orchestration"[implemented]
CLINK::"External CLI delegation"[implemented]
CONSENSUS::"Multi-model consensus building"[implemented]

### Context Steward v2 Tools
DOCUMENT_SUBMIT::"Document routing and placement"[implemented]
CONTEXT_UPDATE::"AI-driven context file merging with conflict detection"[implemented]
CHANGELOG_PARSER::"Section-aware conflict detection with continuation_id"[implemented]
GATHER_SIGNALS::"Runtime signal gathering (git, test, authority)"[implemented]

### Deprecated Tools
THINKDEEP::"Replaced by HestAI phase progression (D1-D2-B0)"[deprecated]
DEBUG::"Replaced by domain-specific error routing"[deprecated]

## BRANCH_HEALTH

CURRENT_BRANCH::"feature/context-steward-octave"
BASE_BRANCH::"main"
STATUS::"8 commits ahead of origin"

RECENT_COMMITS::[
  "cb06877::fix: Persist history_archive artifact to PROJECT-HISTORY.md (#107)",
  "ed48f4f::fix: Add path containment validation to prevent traversal attacks",
  "312dae7::fix: Select artifact by type, not array order in contextupdate",
  "a9af46a::feat: Implement clockout verification gate",
  "425207b::feat: Implement COMPACTION_ENFORCEMENT gate for context_update (#107)"
]

PR_STATUS::[
  "PR #111: feat: Context Steward v2 - Coherence Gates and Security Fixes",
  "Status: CI running (lint, test-full 3.10/3.11/3.12)",
  "URL: https://github.com/elevanaltd/hestai-mcp-server/pull/111"
]

QUALITY_STATUS::[
  lint::"passing",
  typecheck::"passing",
  test::"1258 passed, 11 skipped, 12 deselected, 1 xfailed",
  coverage::"Full suite including clockout + context_update + history_archive persistence"
]

## INTEGRATION_GUARDRAILS

### Context Steward Integration Points
CLOCKIN_INTEGRATION::"Must validate session directory structure before registration"
REQUESTDOC_INTEGRATION::"Must validate templates before rendering"
ANCHORSUBMIT_INTEGRATION::"Must validate anchor structure before acceptance"

### Validation Flow
REQUEST→VALIDATOR→[VALID→PROCEED|INVALID→REJECT|CORRUPTED→LKG_RECOVERY]

### LKG (Last Known Good) Protection
SNAPSHOT_TRIGGER::"After successful validation"
RECOVERY_TRIGGER::"On validation failure with corruption detected"
LOCATION::".lkg/ directory (per context directory)"

### Quality Gate Enforcement
PRE_COMMIT::"All quality gates must pass (lint+typecheck+test)"
PRE_MERGE::"CI pipeline must be green"
PRE_DEPLOY::"Integration tests must pass"

## CONTEXT_LIFECYCLE
TARGET::<200_LOC[current_file]
FORMAT::mixed_prose+OCTAVE[context_efficiency]
ON_UPDATE::[
  "1. Merge new information into PROJECT-CONTEXT.md",
  "2. Append change record to PROJECT-CHANGELOG.md",
  "3. Check LOC count after merge"
]
ON_EXCEED_200_LOC::[
  IDENTIFY::stale_items[
    "old_RECENT_ACHIEVEMENTS[keep_last_5]",
    "completed_phases",
    "resolved_issues",
    "deprecated_notes"
  ]
  ARCHIVE::move_to_PROJECT-HISTORY.md[under_dated_section]
  COMPACT::keep_PROJECT-CONTEXT_focused[
    "current_phase",
    "active_work",
    "recent_achievements[last_5]",
    "current_architecture"
  ]
  LOG::note_compaction_in_CHANGES
]
