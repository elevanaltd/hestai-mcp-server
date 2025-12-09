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
ACTIVE_FOCUS::"Context Steward v2 - Phase 0 Kernel Implementation"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4
SESSION::"5ab8bad5 (HO orchestrating)"

RECENT_ACHIEVEMENTS::[
  "Created PR #95 for Context Steward v2 architecture",
  "Enabled cross-agent visibility (context files now git-tracked)",
  "Created GitHub Project #4 with 17 issues across 4 phases",
  "Created CONTEXT-STEWARD-V2-SPEC.oct.md",
  "Migrated task tracking from CHECKLIST to GitHub Projects",
  "Implemented Kernel validator (context_validator.py, schemas.py)",
  "Achieved 21/21 tests passing for validation infrastructure"
]

OPEN_PR::#95[Context Steward v2: Architecture Specification and Cross-Agent Visibility]

## AUTHORITY
CURRENT_OWNER::implementation-lead
PHASE::B2[Build Phase - Implementation]
ACCOUNTABLE_TO::critical-engineer[via holistic-orchestrator]
SESSION_ID::5ab8bad5

BLOCKING_ITEMS::none
QUALITY_GATES::[
  lint::"pending",
  typecheck::"pending",
  test::"21/21 passing (test_context_validator.py)"
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

### Context Steward v2 Tools (In Development)
CONTEXT_VALIDATOR::"Kernel validation (Phase 0)"[in_progress]
CONTEXT_ROUTER::"Shell routing logic (Phase 1)"[planned]
CONTEXT_UPDATER::"Context file updates (Phase 1)"[planned]
CONTEXT_ARCHIVER::"Compression and archival (Phase 2)"[planned]

### Deprecated Tools
THINKDEEP::"Replaced by HestAI phase progression (D1-D2-B0)"[deprecated]
DEBUG::"Replaced by domain-specific error routing"[deprecated]

## BRANCH_HEALTH

CURRENT_BRANCH::"feature/context-steward-octave"
BASE_BRANCH::"main"
STATUS::"clean working tree"

RECENT_COMMITS::[
  "cec4c38::Track context files for cross-agent visibility",
  "058f4fa::Add Context Steward v2 spec and critical-engineer assessment",
  "ddc0540::Mock AI helper in requestdoc fixture for template path tests",
  "68cbdc9::Fix PR #77 P1 issues in requestdoc and templates",
  "878eb53::Add tests for PR #77 P1 fixes"
]

QUALITY_STATUS::[
  lint::"pending full run",
  typecheck::"pending full run",
  test::"21/21 new tests passing, full suite pending",
  coverage::"Context Steward components fully covered"
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
