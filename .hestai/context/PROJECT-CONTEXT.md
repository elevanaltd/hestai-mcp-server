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
DATE::2025-12-11[21:36]
BRANCH::fix/issue-120-clockout-pipeline[71cf145]
ACTIVE_FOCUS::\"Context Steward v2 - Clockout Pipeline Completion + /load Command Ecosystem Integration\"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4
SESSION_VERIFIED::true[system-steward context validation 21:36 UTC]

RECENT_ACHIEVEMENTS::[
  \"Session c63e80ae: /load command 7-tier redesign with 5/5 specialist consensus (HO-Liaison+Edge-Optimizer+Critical-Engineer+Principal-Engineer+HO)\",
  \"Cross-session learnings index: governance cascades architecture, failure mode design, ecosystem context awareness\",
  \"#121 Web Agent Protocol MERGED to main (feature/issue-120-web-agent-protocol)\",
  \"#120 Clockout pipeline COMPLETE: tool_use + tool_result capture + verification gate working\",
  \"Issue #120: Raw JSONL preservation + sensitive params redaction + output summarization\",
  \"Verification gate implementation: Path traversal protection + artifact reality checks\",
  \"Context sync integration: OCTAVE compression → PROJECT-CONTEXT auto-merge (holistic path)\"
]

NEXT_PRIORITY::[
  \"Ecosystem-integrated load.md distribution via /config-sync push_all to all projects\",
  \"Lazy GC implementation: zombie session cleanup on clock_in (principal-engineer identified 100% abandonment)\",
  \"Test new /load command: verify 7-tier flow + fail-hard clockin + dashboard display\",
  \"Branch-binding for sessions (#110) + partial symlink pattern for worktree context sharing\"
]

## CLOCKOUT_FLOW_STATUS
INTENDED_FLOW::[
  \"1. Session transcript created → COMPLETE\",
  \"2. Raw JSONL preservation → COMPLETE (#120: _preserve_raw_JSONL_before_parsing)\",
  \"3. Tool_use/tool_result extraction → COMPLETE (#120: expanded _parse_session_transcript)\",
  \"4. OCTAVE compression by AI → COMPLETE (archive/{session_id}-octave.oct.md)\",
  \"5. Verification gate (path traversal + artifact reality checks) → COMPLETE\",
  \"6. Context sync to PROJECT-CONTEXT → COMPLETE (auto-merge via context_update tool)\"
]

ISSUE_120_COMPLETION::[
  \"Previously: Lost 98.6% of session content (only user/assistant messages captured)\",
  \"Now: tool_use → name+id+redacted_params; tool_result → output+summary; raw JSONL preserved\",
  \"Verification gate: Blocks malicious OCTAVE content before context sync\",
  \"Security hardening: Path traversal validation + sensitive param redaction + output summarization\",
  \"Holistic path: JSONL → transcript → OCTAVE compression → verification → PROJECT-CONTEXT sync\"
]

LOAD_COMMAND_REDESIGN::[
  ARCHITECTURE::[\"7-tier ecosystem-integrated design validated by 5/5 specialist consensus\"],
  TIER_1::\"Constitutional RAPH (micro-RAPH identity binding)\",
  TIER_2::\"Session lifecycle (clock_in fail-hard + context state vector)\",
  TIER_3::\"Context negatives filtering (excluded items + enforcement state)\",
  TIER_4::\"Anchor submit soft-fail (enforcement rules without blocking capability)\",
  TIER_5::\"Codebase lazy loading (conditional repomix on architectural questions only)\",
  TIER_6::\"RAPH context-aware (role-specific prompt loading)\",
  TIER_7::\"Dashboard display (enforcement rules + behind/ahead counts + state summary)\",
  DECISION_RATIONALE::[
    \"Fail-hard on clockin: session_id required for clockout compression+context_sync (audit_gap without it)\",
    \"Soft-fail on anchor_submit: enforcement_rules_missing_gracefully_degrades_guards_not_capability\",
    \"Lazy repomix: conditional_pack avoids 40KB×10_loads=400K_tokens_wasted (principal-engineer validation)\",
    \"Partial symlink: .hestai/context_shared across worktrees, sessions/local per-branch (race_condition_prevention)\"
  ],
  IMPLEMENTATION_STATUS::\"Ready for ecosystem distribution via /config-sync push_all\"
]

NEXT_PHASE::[
  \"PR #120 submission and merge (code ready on fix/issue-120-clockout-pipeline)\",
  \"Distribute ecosystem-integrated /load to hestai,eav,eav-monorepo,ingest,cep projects\",
  \"Branch-awareness (#110) → add git branch field to session.json\",
  \"Lazy GC on clock_in → zombie session recovery (holistic-orchestrator finding)\"
]

PHASE_STATUS::[
  \"Phase 1 Foundation: COMPLETE\",
  \"Phase 2 AI Intelligence: COMPLETE\",
  \"Phase 3 Deprecation: #92 TODO\",
  \"Phase 4 Validation: #93 UNBLOCKED (pending PR #111 merge)\"
]

## AUTHORITY
CURRENT_OWNER::implementation-lead[b2-implementation]
PHASE::B2[Build Phase - Issue #120 clockout pipeline completion + ecosystem /load integration]
PREVIOUS_VALIDATION::holistic-orchestrator[163bc14b: systemic gap analysis complete; c63e80ae: ecosystem-first /load redesign validated]
CURRENT_VALIDATION::system-steward[2025-12-11T21:36Z: timestamp+branch+commit verified; lint/typecheck/test gates pending]
ACCOUNTABLE_TO::critical-engineer[via holistic-orchestrator]

QUALITY_GATES::[
  lint::\"pending\",
  typecheck::\"pending\",
  test::\"pending\"
]

BRANCH_TRACKING::fix/issue-120-clockout-pipeline[71cf145: docs(session) compress session 3674be37 model-tracking-test to OCTAVE; ready for PR submission]
MAIN_BRANCH_STATUS::6bf3dc3[Merge_PR_#121_Web_Agent_Protocol]
IMPLEMENTATION_STATUS::Code complete; clockout + /load ecosystem integration working; quality gates pending; atomic commit ready

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

### Audit & Operations (New - 2025-12-10)
MCP_AUDIT_REPORT::\".hestai/reports/801-REPORT-MCP-AUDIT-SESSION-F29CB14C.md\"[comprehensive system health validation]
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

BRANCH::\"fix/issue-120-clockout-pipeline\"
COMMITS_AHEAD::1
QUALITY_GATES::[lint::\"pending\", typecheck::\"pending\", test::\"pending\"]
LAST_MERGE::\"PR #121 merged (Web Agent Protocol)\",PENDING::\"clockout enhancements + /load ecosystem redesign for #120\"

## SYSTEMIC_INSIGHTS[from_holistic-orchestrator]

KEY_FINDINGS::[
  \"Clockout design assumes user performs explicit action; actual data shows 100% abandonment rate (12 zombie sessions)\",
  \"PROJECT_CONTEXT mixes strategic[identity+architecture] with tactical[current_PRs]→recommend split into STATUS file\",
  \"Sessions lack git branch awareness→loses context when switching branches\",
  \"Governance architecture must be visible to specialists during review, not discovered mid-consensus (c63e80ae learning)\",
  \"Specialists optimize locally; orchestrators validate globally→bidirectional consultation needed\"
]

REMEDIATION_ROADMAP::[
  \"Tier_0: Ecosystem-integrated /load distribution + branch binding (#110) + lazy GC on clock_in (zombie recovery)\",
  \"Tier_1: Split PROJECT_CONTEXT into strategic+PROJECT_STATUS tactical\",
  \"Tier_2: Cross-session discovery + anchor.json as source of truth (requires specialist consultation on race_conditions)\",
  \"Tier_3: Consolidate workflow documentation (deferred)\"
]
