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
DATE::2025-12-12
BRANCH::main[7169297]
ACTIVE_FOCUS::\"Issue #120 Unified .hestai Architecture - Phase 3 Clockin Updates\"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4
ISSUE_120_STATUS::OPEN[Phase 1+2 COMPLETE, Phase 3-5 remaining]
QUALITY_GATES_STATUS::lint=pending, typecheck=pending, test=pending

RECENT_ACHIEVEMENTS::[
  \"PR #125 Phase 2 - Consistent archive naming and TXT removal MERGED\",
  \"PR #124 Worktree branch operations MERGED\",
  \"PR #123 Clockout pipeline fix MERGED (tool_use + tool_result capture)\",
  \"PR #122 Tool operations preservation MERGED\",
  \"PR #121 Web Agent Protocol MERGED\",
  \"#116 octave_path in response CLOSED\"
]

## ISSUE_120_ARCHITECTURE_OVERHAUL
STATUS::IN_PROGRESS[keystone_issue]
PROBLEM_STATEMENT::[
  \"Sessions siloed per worktree - agents cannot see cross-worktree work\",
  \"Clockout pipeline loses 98.6% of content (tool ops filtered out)\",
  \"No separate git tracking - artifacts pollute project or lost on clone\",
  \"Duplicated PROJECT-CONTEXT.md with divergence risk\"
]

PROPOSED_SOLUTION::\"Centralize via ~/.hestai/ as separate git repo with symlinks; preserve JSONL (gitignored, 30-day); track OCTAVE permanently\"

PHASE_PROGRESS::[
  \"Phase 1 Infrastructure: COMPLETE (PR #125: ~/.hestai/ + git init + setup script + inbox layer)\",
  \"Phase 2 Clockout Fix: COMPLETE (PR #125: TXT removed, consistent naming, JSONL preserved)\",
  \"Phase 3 Clockin Updates: TODO (symlink detection, cleanup trigger)\",
  \"Phase 4 Migration: TODO (existing directory migration, PROJECT-CONTEXT merge)\",
  \"Phase 5 Documentation: TODO (spec updates, setup guide, retention policy)\"
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
LAST_UPDATE::system-steward[2025-12-12T02:19:04Z: context state verification, branch/commit tracking updated]

QUALITY_GATES::[lint::\"passing\", typecheck::\"passing\", test::\"passing\"]

BRANCH_TRACKING::main[7169297: update project context #126]
MAIN_BRANCH_STATUS::7169297[PR #126 project context update merged]

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
