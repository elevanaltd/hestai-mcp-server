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

### Audit & Operations (New - 2025-12-10)
MCP_AUDIT_REPORT::".hestai/reports/801-REPORT-MCP-AUDIT-SESSION-F29CB14C.md"[comprehensive system health validation]
TOOL_DEPENDENCY_MATRIX::".hestai/workflow/MCP-TOOL-DEPENDENCY-MATRIX.md"[change control checklist]
PARALLEL_VALIDATION_PATTERN::".hestai/patterns/PARALLEL-AGENT-VALIDATION.oct.md"[orchestration pattern]
PROCESS_CLEANUP_PROTOCOL::".hestai/operations/PROCESS-CLEANUP-PROTOCOL.md"[operational runbook]

### Context Files
PROJECT_CONTEXT::".hestai/context/PROJECT-CONTEXT.md"[this file]
HISTORY::".hestai/context/PROJECT-HISTORY.md"
CHANGELOG::".hestai/context/PROJECT-CHANGELOG.md"

### Essential Commands
CODE_QUALITY::"./code_quality_checks.sh"
INTEGRATION_TESTS::"./run_integration_tests.sh"

## MCP_TOOL_STATUS

ACTIVE::[clockin, clockout, anchorsubmit, chat, clink, consensus, document_submit, context_update, changelog_parser, gather_signals]
DEPRECATED::[thinkdeep, debug, requestdoc]

## CURRENT_CI_STATUS

BRANCH::"feature/context-steward-octave"
COMMITS_AHEAD::8
QUALITY_GATES::[lint::"passing", typecheck::"passing", test::"1258 passed"]
LAST_MERGE::"PR #111 merged (coherence gates + security fixes)"
