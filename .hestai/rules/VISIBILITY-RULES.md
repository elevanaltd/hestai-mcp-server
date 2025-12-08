# Visibility Rules

Rules enforced by stewards for documentation placement.

```octave
VISIBILITY_RULES::[

  RULE_1::PERMANENT_ARCHITECTURAL→docs/[
    CRITERIA::[
      affects_architecture_across_apps,
      changes_how_developers_work,
      permanent_decision,
      would_help_new_developer
    ],
    FORMAT::ADR_template|standard_markdown,
    OWNER::system-steward
  ],

  RULE_2::PROJECT_OPERATIONAL_STATE→.hestai/context/[
    CRITERIA::[
      current_status_or_progress,
      task_tracking,
      agent_coordination_data,
      changes_frequently
    ],
    FORMAT::OCTAVE_compressed,
    OWNER::system-steward[context_stewardship_extension]
  ],

  RULE_3::SESSION_ARTIFACTS→.hestai/sessions/[
    CRITERIA::[
      session_specific,
      temporary_or_archival,
      handoff_artifacts
    ],
    FORMAT::JSON_metadata+OCTAVE_transcript,
    OWNER::system-steward[context_stewardship_extension]
  ],

  RULE_4::METHODOLOGY→.hestai/workflow/[
    CRITERIA::[
      HestAI_methodology[not_project_specific],
      North_Star_immutables,
      informal_decisions[not_ADR_worthy]
    ],
    FORMAT::OCTAVE,
    OWNER::system-steward
  ],

  RULE_5::CLAUDE_CONFIG→.claude/[
    CRITERIA::agent_constitutions|commands|hooks|skills,
    FORMAT::YAML_frontmatter+markdown,
    OWNER::system-steward[with_skills-expert_consultation]
  ]
]
```

---

**Source**: ADR-003 HestAI Documentation Architecture
**Authority**: system-steward
