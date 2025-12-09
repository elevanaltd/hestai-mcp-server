# Context Steward v2 Specification

```octave
SPEC_METADATA::[
  VERSION::2.0.0,
  STATUS::approved,
  DATE::2025-12-09,
  AUTHORS::[system-steward,technical-architect],
  SESSION::a1172310,
  ISSUE_REF::github#71
]

## 1. TOOL_ARCHITECTURE ##

TOOLS::[
  document_submit::[
    PURPOSE::"Submit documents for routing/placement via visibility rules",
    PARAMS::{
      type::Literal[adr,session_note,workflow,config],
      intent::str[required],
      content::str[small_<1KB],
      file_ref::str[large_>1KB_inbox_path],
      priority::Literal[blocking,normal],
      continuation_id::str[dialogue_support]
    },
    FLOW::ACCEPT→CLASSIFY→PROCESS→PLACE→ARCHIVE→NOTIFY
  ],

  context_update::[
    PURPOSE::"Request updates to context files (AI-driven merge)",
    PARAMS::{
      target::Literal[PROJECT-CONTEXT,PROJECT-CHECKLIST,PROJECT-ROADMAP],
      intent::str[required],
      content::str[small],
      file_ref::str[large_inbox_path],
      continuation_id::str[dialogue_support]
    },
    FLOW::ACCEPT→ARCHIVE→CROSS_REFERENCE→DETECT_CONFLICTS→MERGE→COMPRESS→WRITE→LOG→RETURN
  ]
]

## 2. INBOX_STRUCTURE ##

DIRECTORY_LAYOUT::[
  .hestai/inbox/::[
    pending/::awaiting_processing[{uuid}-{type}.md],
    processed/::audit_trail[30_days_git_tracked,index.json,{date}/{uuid}.md]
  ]
]

INDEX_SCHEMA::{
  version::str,
  retention_days::30,
  entries::[{
    uuid,type,target,submitted_by,session_id,
    submitted_at,processed_at,status,
    destination,changelog_ref,archived_path
  }]
}

## 3. VISIBILITY_RULES_V2 ##

DOCUMENT_TYPES::[
  adr::{destination:"docs/adr/",format:ADR_template,compress:false},
  session_note::{destination:".hestai/sessions/notes/",format:OCTAVE,compress:true},
  workflow::{destination:".hestai/workflow/",format:OCTAVE,compress:true},
  config::{destination:".claude/",format:preserve,compress:false,requires_validation:true}
]

CONTEXT_TARGETS::[
  PROJECT-CONTEXT::{path:".hestai/context/PROJECT-CONTEXT.md",max_loc:200,overflow:"PROJECT-HISTORY.md"},
  PROJECT-CHECKLIST::{path:".hestai/context/PROJECT-CHECKLIST.md",max_loc:100},
  PROJECT-ROADMAP::{path:".hestai/context/PROJECT-ROADMAP.md",max_loc:150}
]

## 4. CONFLICT_HANDLING ##

DETECTION::[
  METHOD::CHANGELOG_based,
  CHECK::recent_changes_to_same_section
]

SCENARIOS::[
  UNRELATED_CONCURRENT::[
    action::process_in_order,
    notify::"Note: Agent A submitted change at {time} processed first"
  ],
  CONFLICTING_SAME_SECTION::[
    action::flag_conflict,
    status::conflict,
    require::confirmation_via_continuation_id,
    suggest::AI_assisted_resolution
  ]
]

DIALOGUE_SUPPORT::[
  PATTERN::continuation_id[like_clink],
  FLOW::initial_submit→conflict_response→resolution_submit
]

## 5. OCTAVE_INTEGRATION ##

COMPRESSION_PROTOCOL::[
  THRESHOLD::1KB,
  IF[submission_size>1KB]::[
    save_original_to_inbox,
    load_octave-compression_skill,
    compress_to_60-80%_reduction,
    place_compressed_at_destination,
    archive_original_to_processed
  ]
]

CONTEXT_COMPACTION::[
  IF[target>200_LOC_after_merge]::[
    identify_stale[old_achievements,completed_phases,resolved_issues],
    compress_to_PROJECT-HISTORY.md,
    keep_target_under_200_LOC
  ]
]

## 6. IMPLEMENTATION_PHASES ##

PHASE_1_FOUNDATION::[
  TASKS::[
    extract_shared_components_to_context_steward_modules,
    create_inbox_directory_structure,
    implement_document_submit_tool,
    implement_context_update_tool,
    add_continuation_id_support
  ],
  ESTIMATE::8-10_hours
]

PHASE_2_OCTAVE::[
  TASKS::[
    integrate_octave-compression_skill,
    implement_context_compaction,
    add_archive_retention_with_index
  ],
  ESTIMATE::3-4_hours
]

PHASE_3_CONFLICTS::[
  TASKS::[
    enhanced_section_level_diff,
    AI_assisted_resolution_suggestions,
    full_dialogue_flow
  ],
  ESTIMATE::4-5_hours
]

DEPRECATION::[
  request_doc::deprecated[4_week_migration],
  backward_compat::maintained_during_migration,
  removal::after_validation_period
]

## 7. SHARED_MODULES ##

EXTRACTION_MAP::[
  visibility_rules.py::VISIBILITY_RULES[from_requestdoc_L27-32],
  file_lookup.py::find_context_file[from_requestdoc_L342-370],
  utils.py::[sanitize_filename,append_changelog],
  ai.py::ContextStewardAI[existing_enhance]
]

## 8. AUTHORITY ##

PROCESSING::system-steward_ONLY[documentation_specialist],
CONTENT::provided_by_domain_agents,
FORMAT::controlled_by_system-steward,
APPROVALS::[technical-architect:GO,critical-engineer:REQUIRED,holistic-orchestrator:REQUIRED]

## 9. FUTURE_VISION ##

CONTEXT_STEWARD_APP::[
  COMPONENTS::[inbox_monitor,processing_engine,web_dashboard,REST_API],
  HUMAN_OVERSIGHT::[review_gate,routing_overrides,conflict_arbitration],
  INTEGRATION::[MCP_bridge,webhooks,GitHub_auto_PRs]
]
```

---
**Source**: Session a1172310 analysis
**Authority**: system-steward + technical-architect
**Issue**: github.com/elevanaltd/hestai-mcp-server/issues/71
