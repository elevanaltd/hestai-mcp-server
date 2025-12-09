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
DATE::2025-12-09
ACTIVE_FOCUS::"Context Steward v2 - Phase 2 Complete, Phase 3 Next"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4

RECENT_ACHIEVEMENTS::[
  "#91 Conflict detection with continuation_id dialogue (CLOSED)",
  "#90 AI prompt enrichment with git/test/authority signals (CLOSED)",
  "Fixed 3 pre-existing test failures (DISABLED_TOOLS, session UUID collision)",
  "Phase 1 Foundation complete (#82-89 all Done)",
  "Phase 2 AI Intelligence complete (#90-91 Done)"
]

PHASE_STATUS::[
  "Phase 1 Foundation: COMPLETE",
  "Phase 2 AI Intelligence: COMPLETE",
  "Phase 3 Deprecation: #92 TODO",
  "Phase 4 Validation: #93 BLOCKING for rollout"
]

## AUTHORITY
CURRENT_OWNER::implementation-lead
PHASE::B2[Build Phase - Implementation]
ACCOUNTABLE_TO::critical-engineer[via holistic-orchestrator]

BLOCKING_ITEMS::none
QUALITY_GATES::[
  lint::"passing",
  typecheck::"passing",
  test::"1213/1213 passing (full suite)"
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
REQUESTDOC::"Documentation routing and placement"[implemented]
CHAT::"Multi-model conversation orchestration"[implemented]
CLINK::"External CLI delegation"[implemented]
CONSENSUS::"Multi-model consensus building"[implemented]

### Context Steward v2 Tools
CONTEXT_UPDATE::"AI-driven context file merging with conflict detection"[implemented]
DOCUMENT_SUBMIT::"Document routing and placement via visibility rules"[implemented]
GATHER_SIGNALS::"Runtime signal collection (git/test/authority)"[implemented]
CHANGELOG_PARSER::"Section-aware conflict detection"[implemented]

### Deprecated Tools
THINKDEEP::"Replaced by HestAI phase progression (D1-D2-B0)"[deprecated]
DEBUG::"Replaced by domain-specific error routing"[deprecated]

## BRANCH_HEALTH

CURRENT_BRANCH::"feature/context-steward-octave"
BASE_BRANCH::"main"
STATUS::"clean working tree"

RECENT_COMMITS::[
  "188c1bc::feat: Add section-aware conflict detection with continuation_id (#91)",
  "b7e64c8::fix: Exclude decision-records from linting",
  "c316d65::fix: Use unique test session ID to prevent temporal beacon collisions",
  "1716a70::fix: Clear DISABLED_TOOLS in test config",
  "c9d1523::feat: Add gather_signals function for AI context enrichment"
]

QUALITY_STATUS::[
  lint::"passing",
  typecheck::"passing",
  test::"1213/1213 passing (full suite)",
  coverage::"Context Steward v2 components fully covered"
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
