# PROJECT CONTEXT

## IDENTITY
NAME::HestAI MCP Server
TYPE::Model Context Protocol (MCP) Server
PURPOSE::\"Orchestrate multiple AI models (Claude, Gemini, etc.) for enhanced code analysis, problem-solving, and collaborative development.\"
ORIGIN::\"Fork of zen-mcp-server by Beehive Innovations, rebranded/modified by Elevana Ltd.\"

## ARCHITECTURE
CORE_PRINCIPLE::\"Human-in-the-loop AI orchestration where Claude/Gemini CLI stays in control but leverages specialized models for subtasks.\"
KEY_COMPONENTS::[
  \"HestAI MCP Server (Python)\",
  \"Tools (chat, clink, consensus, analyze, tracer, secaudit)\",
  \"CLI Integration (clink) - delegates to external AI CLIs\",
  \"Context Steward - Session lifecycle management\"
]
INTEGRATION_STATUS::\"Context Steward v2 in development\"
RUNTIME_DEPENDENCIES::[
  \"python>=3.9\",
  \"mcp>=1.0.0\",
  \"google-generativeai>=0.8.0\",
  \"openai>=1.55.2\",
  \"pydantic>=2.0.0\",
  \"python-dotenv>=1.0.0\",
  \"pyyaml>=6.0.0\"
]

## CURRENT_STATE
DATE::2025-12-13
BRANCH::main[c51a909]
COMMIT_MESSAGE::\"feat(context-steward): add anchor architecture support with event sourcing\"
ACTIVE_FOCUS::\"Anchor Architecture Integration with hestai-core\"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4
ISSUE_120_STATUS::OPEN[Phase 3 anchor support COMPLETE, Phase 4-5 remaining]
QUALITY_GATES_STATUS::lint=passing, typecheck=passing, test=passing

RECENT_ACHIEVEMENTS::[
  \"c51a909 feat(context-steward): add anchor architecture support with event sourcing\",
  \"Anchor mode detection in clockin (snapshots/ vs context/)\",
  \"Event emission to events/ in contextupdate (READ-ONLY snapshots/ enforcement)\",
  \"Path traversal security fix with is_relative_to() validation\",
  \"7 comprehensive anchor mode tests\"
]

## ISSUE_120_ARCHITECTURE_OVERHAUL
STATUS::IN_PROGRESS[keystone_issue]
PROBLEM_STATEMENT::[
  \"Sessions siloed per worktree - agents cannot see cross-worktree work\",
  \"Clockout pipeline loses 98.6% of content (tool ops filtered out)\",
  \"No separate git tracking - artifacts pollute project or lost on clone\",
  \"Duplicated PROJECT-CONTEXT.md with divergence risk\"
]

PROPOSED_SOLUTION::\"Anchor Architecture via hestai-core - sibling worktree with event sourcing\"

PHASE_PROGRESS::[
  \"Phase 1 Infrastructure: COMPLETE (PR #125: ~/.hestai/ + git init + setup script + inbox layer)\",
  \"Phase 2 Clockout Fix: COMPLETE (PR #125: TXT removed, consistent naming, JSONL preserved)\",
  \"Phase 3 Anchor Support: COMPLETE (c51a909: dual-mode detection, event emission, path security)\",
  \"Phase 4 Migration: TODO (existing directory migration, PROJECT-CONTEXT merge)\",
  \"Phase 5 Documentation: TODO (spec updates, setup guide, retention policy)\"
]

## HESTAI_CORE_INTEGRATION
STATUS::IN_DEVELOPMENT
LOCATION::\"/Volumes/HestAI-Projects/hestai-core/\"
SPEC::\"spec/CONTEXT-ANCHOR-STRUCTURE.md\"
ARCHITECTURE::[
  \"Sibling Worktree: .hestai-state-wt-{repo_name}-{hash}/ (collision-proof naming)\",
  \"Event Sourcing: Agents emit events to events/, Steward synthesizes snapshots/\",
  \"READ-ONLY: snapshots/ and governance/ are never written directly by agents\",
  \"Symlink: .hestai/ in project root points to sibling worktree\",
  \"Orphan Branch: hestai-state branch for anchor persistence\"
]
MCP_TOOL_ALIGNMENT::[
  \"clockin: Detects anchor mode via snapshots/ existence, stores is_anchor_mode in session\",
  \"contextupdate: Emits events to events/ in anchor mode, direct writes in legacy mode\",
  \"file_lookup: Prioritizes snapshots/ over context/ in search order\",
  \"visibility_rules: Separate read_path (snapshots/), write_path (events/), legacy_path (context/)\"
]
NEXT_STEPS::[
  \"Implement AnchorManager in hestai-core (git worktree add, symlink creation)\",
  \"Implement EventLog for safe JSON event appending\",
  \"Implement Snapshotter for events -> markdown synthesis\",
  \"Add tripwire validation (abort if CWD is anchor directory)\",
  \"Add chmod enforcement for snapshots/ READ-ONLY\"
]

ACCEPTANCE_CRITERIA::[
  \"All 10 Phase 1 requirements implemented\",
  \"Existing projects migrate without data loss\",
  \"CI/CD pipelines work without modification\",
  \"Multi-worktree visibility achieved\",
  \"Clockout atomicity verified (no partial writes)\",
  \"Git Notes linkage traversable\"
]

BLOCKING_ISSUES::[
  \"#119 CSI-HYBRID Session Lifecycle (depends on #120)\",
  \"#104 Verification Gate (depends on #120)\",
  \"#93 Validation Gate Phase 4 (depends on #104)\"
]

NEXT_PRIORITY::[
  \"Phase 3: Detect symlinks in clockin, resolve correctly\",
  \"Phase 3: Add cleanup trigger (daily retention enforcement)\",
  \"Phase 3: Update context path resolution for unified structure\",
  \"Phase 4: Migration script for existing .hestai/ directories\"
]

## CONTEXT_STEWARD_PHASE_STATUS
PHASE_1_FOUNDATION::COMPLETE[7/7 items]
PHASE_2_AI_INTELLIGENCE::COMPLETE[3/3 items]
PHASE_3_DEPRECATION::TODO[#92 deprecate request_doc]
PHASE_4_VALIDATION::BLOCKED[#93 depends on #104 depends on #120]
PHASE_5_GOVERNANCE::FUTURE[#66,#67,#68]

## LOAD_COMMAND_REDESIGN
STATUS::VALIDATED[5/5 specialist consensus]
ARCHITECTURE::\"7-tier ecosystem-integrated design\"
IMPLEMENTATION_STATUS::\"Ready for ecosystem distribution via /config-sync push_all\"

## AUTHORITY
CURRENT_OWNER::implementation-lead[b2-implementation]
PHASE::B2[Build Phase - Issue #120 Unified .hestai Architecture]
PREVIOUS_VALIDATION::holistic-orchestrator[session 7f1e751e: PROJECT-CONTEXT correction + 803-REPORT creation]
ACCOUNTABLE_TO::critical-engineer[via holistic-orchestrator]
LAST_UPDATE::holistic-orchestrator[2025-12-13T17:45:00Z: anchor architecture integration, hestai-core reference, Phase 3 complete, branch tracking c51a909]

QUALITY_GATES::[lint::\"passing\", typecheck::\"passing\", test::\"passing\"]

BRANCH_TRACKING::main[c51a909: feat(context-steward): add anchor architecture support]
MAIN_BRANCH_STATUS::c51a909[anchor architecture support with event sourcing]

## DEVELOPMENT_GUIDELINES
STYLE::\"Follow existing project conventions (formatting, naming).\"
TESTING::\"Run tests via `run_integration_tests.sh` or `pytest`. Ensure 100% pass rate.\"
DOCUMENTATION::\"Maintain strict documentation standards. Update docs/ when features change.\"
CONSTITUTION::\"Adhere to System-Steward constitutional principles (Observation, Preservation, Patterns).\"

## QUICK_REFERENCES

### Specifications
SPEC::\".hestai/workflow/CONTEXT-STEWARD-V2-SPEC.oct.md\"
CRITICAL_ASSESSMENT::\".hestai/reports/800-REPORT-CRITICAL-ENGINEER-CONTEXT-STEWARD-ASSESSMENT.md\"
LOAD_ARCHITECTURE::\".hestai/commands/load.md\"[7-tier ecosystem-integrated design]

### Audit & Operations
MCP_AUDIT_REPORT::\".hestai/reports/801-REPORT-MCP-AUDIT-SESSION-F29CB14C.md\"[comprehensive system health validation]
ISSUE_120_ASSESSMENT::\".hestai/reports/803-REPORT-ISSUE-120-ORCHESTRATION-ASSESSMENT.md\"[keystone issue priority plan]
TOOL_DEPENDENCY_MATRIX::\".hestai/workflow/MCP-TOOL-DEPENDENCY-MATRIX.md\"[change control checklist]
PARALLEL_VALIDATION_PATTERN::\".hestai/patterns/PARALLEL-AGENT-VALIDATION.oct.md\"[orchestration pattern]
PROCESS_CLEANUP_PROTOCOL::\".hestai/operations/PROCESS-CLEANUP-PROTOCOL.md\"[operational runbook]

### Context Files
PROJECT_CONTEXT::\".hestai/context/PROJECT-CONTEXT.md\"[this file]
HISTORY::\".hestai/context/PROJECT-HISTORY.md\"
CHANGELOG::\".hestai/context/PROJECT-CHANGELOG.md\"

### Essential Commands
CODE_QUALITY::\"./code_quality_checks.sh\"
INTEGRATION_TESTS::\"./run_integration_tests.sh\"
LOAD_COMMAND::\"/load ho\" [triggers 7-tier ecosystem-integrated redesign]

## MCP_TOOL_STATUS

ACTIVE::[clockin, clockout, anchorsubmit, chat, clink, consensus, document_submit, context_update, changelog_parser, gather_signals]
DEPRECATED::[thinkdeep, debug, requestdoc]

## CURRENT_CI_STATUS
BRANCH::\"fix-issue-120\"
COMMITS_AHEAD::0
COMMITS_BEHIND::0
QUALITY_GATES::[lint::\"passing\", typecheck::\"passing\", test::\"passing\"]
LAST_MERGE::\"PR #125 Phase 2 consistent naming merged\"

## DEPENDENCY_GRAPH[from_803-REPORT]
KEYSTONE::#120[Unified .hestai Architecture - Phase 1+2 COMPLETE]
TIER_1_QUICK_WINS::[#116 octave_path CLOSED]
TIER_2_FOUNDATION::[#120 Architecture → #119 CSI-HYBRID]
TIER_3_BUG_TRIAGE::[#103 working_dir (may be solved by #120)]
TIER_4_PHASE_PROGRESSION::[#92 deprecation → #104 verification → #93 validation]
TIER_5_PARALLEL::[#97 configurable_paths, #98 rollback, #99 conflict_detection]
TIER_6_GOVERNANCE::[#66 blockage, #67 analyzer, #68 hybrid_enforcement]
