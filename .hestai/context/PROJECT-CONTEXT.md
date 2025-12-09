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
ACTIVE_FOCUS::"Context Steward v2 implementation"
TASK_TRACKING::https://github.com/orgs/elevanaltd/projects/4

RECENT_ACHIEVEMENTS::[
  "Created PR #95 for Context Steward v2 architecture",
  "Enabled cross-agent visibility (context files now git-tracked)",
  "Created GitHub Project #4 with 17 issues across 4 phases",
  "Created CONTEXT-STEWARD-V2-SPEC.oct.md",
  "Migrated task tracking from CHECKLIST to GitHub Projects"
]

OPEN_PR::#95[Context Steward v2: Architecture Specification and Cross-Agent Visibility]

## DEVELOPMENT_GUIDELINES
STYLE::"Follow existing project conventions (formatting, naming)."
TESTING::"Run tests via `run_integration_tests.sh` or `pytest`. Ensure 100% pass rate."
DOCUMENTATION::"Maintain strict documentation standards. Update docs/ when features change."
CONSTITUTION::"Adhere to System-Steward constitutional principles (Observation, Preservation, Patterns)."

## QUICK_REFERENCES
SPEC::".hestai/workflow/CONTEXT-STEWARD-V2-SPEC.oct.md"
CRITICAL_ASSESSMENT::".hestai/reports/800-REPORT-CRITICAL-ENGINEER-CONTEXT-STEWARD-ASSESSMENT.md"
VISIBILITY_RULES::".hestai/rules/VISIBILITY-RULES.md"

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
