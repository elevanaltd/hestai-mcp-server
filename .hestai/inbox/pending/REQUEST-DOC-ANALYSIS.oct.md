# Request_Doc Tool Analysis: Current State & Missing Document Types

## Executive Summary

The `request_doc` tool currently supports **4 document types** but has **critical gaps** for production use:

| Doc Type | Status | AI Support | Implementation |
|----------|--------|-----------|---|
| ADR | ✅ Supported | ❌ Template only | Fallback to ADR_template |
| context_update | ✅ Supported | ✅ Full AI | ContextStewardAI merge |
| session_note | ✅ Supported | ❌ Not wired | Template fallback |
| workflow_update | ✅ Supported | ✅ Full AI | ContextStewardAI merge |
| **report** | ❌ NOT SUPPORTED | ❌ No task | No routing, no templates |
| **build_plan** | ❌ NOT SUPPORTED | ❌ No task | No routing, no templates |
| **ambiguous** | ❌ NOT HANDLED | ❌ No classifier | No routing strategy |

---

## Part 1: Current Implementation (What Works)

### Routing Rules (VISIBILITY_RULES)

From `tools/requestdoc.py:26-32`:

```python
VISIBILITY_RULES = {
    "adr": {"path": "docs/adr/", "format": "ADR_template"},
    "context_update": {"path": ".hestai/context/", "format": "OCTAVE"},
    "session_note": {"path": ".hestai/sessions/", "format": "OCTAVE"},
    "workflow_update": {"path": ".hestai/workflow/", "format": "OCTAVE"},
}
```

### AI Task Mapping (TASK_MAPPING)

From `tools/requestdoc.py:34-40`:

```python
TASK_MAPPING = {
    "context_update": "project_context_update",
    "workflow_update": "project_checklist_update",
    # session_note doesn't have AI integration yet
    # adr doesn't have AI integration yet
}
```

**Key Insight**: Two types (adr, session_note) are defined but commented as NOT having AI integration. They fall back to template-based creation.

### Context Steward AI Tasks

From `conf/context_steward.json:23-44`:

**Configured Tasks** (Only 2):
1. **project_context_update** — Merges new info into PROJECT-CONTEXT.md with AI
2. **project_checklist_update** — Updates PROJECT-CHECKLIST.md with AI

**Defined but Not Triggered**:
- **session_compression** (line 6-22) — Triggers on clock_out.post_archive, but trigger not implemented

**Missing Tasks** (Not defined at all):
- adr_generation / adr_update
- session_note_creation
- report_generation
- build_plan_generation

---

## Part 2: The Gaps

### Gap 1: Reports (No Support at All)

**What's Missing**:
- No routing rules for report types
- No visibility rules in ADR-003 for reports
- No placement strategy (docs/reports? .coord/reports? .hestai/reports?)
- No AI task configuration

**Current Behavior**: User calls `request_doc(type="build_report", ...)` → **ERROR** (invalid enum)

**User Intent**: Generate build reports, analysis reports, status reports, execution logs

### Gap 2: Build Plans (No Support at All)

**What's Missing**:
- No routing for build_plan type
- No placement strategy
- No AI task for intelligent plan generation
- No integration with task-decomposer or implementation-lead workflows

**Current Behavior**: User calls `request_doc(type="build_plan", ...)` → **ERROR** (invalid enum)

**User Intent**: Generate build plans, sprints, task decompositions

### Gap 3: Ambiguous Documents (No Classification)

**Scenario**: A user requests "Generate a summary of what we learned about multi-agent orchestration"

**Questions**:
- Is this an ADR? (No, it's not a decision)
- Is this a session_note? (Maybe, but it's more systematic)
- Is this a report? (Maybe, but it's philosophical)
- Should it go to .hestai/context? (Maybe, but it's archival)

**Current Behavior**: No way to classify. User must manually choose type, risks misplacement.

**Better Approach**: Let system-steward classify intent → route to appropriate location + format

### Gap 4: ADR Content Generation (Templates Only, No AI)

**Current**: ADRs use static markdown templates

```markdown
# ADR: [Title]

## Status
[Proposed|Accepted|Deprecated|Superseded]

## Context
[empty - user must fill]

## Decision
[empty - user must fill]

## Consequences
[empty - user must fill]
```

**Problem**: Template requires manual fill-in. System-steward could intelligently generate Decision/Consequences based on context.

**Better Approach**: Wire ADR type to AI task for intelligent content synthesis

### Gap 5: Session Note Processing (No AI)

**Current**: Session notes use template fallback (basic text file)

**Missing**: Could intelligently extract:
- Key decisions made
- Blockers identified
- Principles learned
- Artifacts created

**Better Approach**: Wire session_note type to AI task (session_compression already defined but not triggered)

---

## Part 3: Proposed Unified Routing System

### Extended VISIBILITY_RULES

Add support for reports, build_plans, and "ambiguous" with intelligent routing:

```octave
EXTENDED_VISIBILITY_RULES::[
  // Existing (working)
  adr::{"path": "docs/adr/", "format": "ADR_markdown"},
  context_update::{"path": ".hestai/context/", "format": "OCTAVE"},
  session_note::{"path": ".hestai/sessions/", "format": "OCTAVE"},
  workflow_update::{"path": ".hestai/workflow/", "format": "OCTAVE"},

  // New: Reports
  build_report::{"path": ".coord/reports/", "format": "markdown_report"},
  analysis_report::{"path": ".coord/reports/", "format": "markdown_report"},
  status_report::{"path": ".coord/reports/", "format": "markdown_report"},

  // New: Build Plans
  build_plan::{"path": ".coord/build_plans/", "format": "OCTAVE_build_plan"},

  // New: Ambiguous (routes to classifier)
  ambiguous::{"path": "CLASSIFY_VIA_SYSTEM_STEWARD", "format": "DETECT"}
]
```

### Extended Task Mapping

Add AI tasks for all types:

```octave
EXTENDED_TASK_MAPPING::[
  // Existing
  context_update::"project_context_update",
  workflow_update::"project_checklist_update",

  // New ADR AI task
  adr::"adr_generation",

  // New session task (already defined as session_compression)
  session_note::"session_note_creation",

  // New report tasks
  build_report::"build_report_generation",
  analysis_report::"analysis_report_generation",
  status_report::"status_report_generation",

  // New build plan task
  build_plan::"build_plan_generation",

  // Ambiguous (routes to classifier)
  ambiguous::"doc_type_classification"
]
```

### New Context Steward AI Tasks (conf/context_steward.json)

Add to task configuration:

```json
"adr_generation": {
  "trigger": "request_doc.type=adr",
  "enabled": true,
  "cli": "gemini",
  "role": "system-steward",
  "prompt_template": "systemprompts/context_steward/adr_generation.txt",
  "output": {
    "expected_format": "adr_markdown",
    "write_path": "docs/adr/{YYYYMMDD}-{slug}.md"
  }
}
```

Similar for:
- session_note_creation
- build_report_generation
- analysis_report_generation
- status_report_generation
- build_plan_generation
- doc_type_classification

---

## Part 4: Handling Ambiguous Documents

### Problem Scenario

```
Agent: "Document what we learned about scaling issues in multi-agent orchestration"
System: "Is this an ADR? A report? A session note? A workflow item?"
```

### Solution: Intelligent Classification

1. **User submits**: `request_doc(type="ambiguous", intent="...", files=[...], ...)`
2. **System routes to**: `doc_type_classification` AI task
3. **System-steward classifies** and recommends:
   - Type (adr | report | session_note | context_update | etc.)
   - Location (docs/adr/ | .coord/reports/ | .hestai/context/ | etc.)
   - Format (ADR_markdown | OCTAVE | markdown_report | etc.)
4. **Automatic routing** to appropriate task + location
5. **User informed** of classification decision

### Classification Prompt Template

```
TASK: Classify documentation request into appropriate HestAI document type

INTENT: {{intent}}
CONTEXT_FILES: {{files}}
PROJECT_PHASE: {{current_phase}}

CLASSIFY_INTO_ONE:
  adr              → Permanent architectural decision affecting multiple systems
  context_update   → Current project state, task status, active blockers
  session_note     → Session-specific artifacts, decisions, learnings
  workflow_update  → Workflow/process updates, methodology changes
  build_report     → Build execution, CI results, deployment status
  analysis_report  → Technical analysis, performance analysis, audit results
  status_report    → Status snapshot for stakeholders

RESPONSE FORMAT:
  type:: [adr|context_update|session_note|workflow_update|report|build_plan]
  location:: [docs/adr/|.hestai/context/|.coord/reports/|...]
  reasoning:: [one sentence explaining classification]
```

---

## Part 5: Implementation Roadmap

### Phase 1 (Critical): Core Report Support

**Effort**: 2-3 days, ~200 LOC

- [ ] Extend RequestDocRequest enum: add build_report, analysis_report, status_report
- [ ] Add to VISIBILITY_RULES (routing to .coord/reports/)
- [ ] Create build_report_generation task in conf/context_steward.json
- [ ] Create systemprompts/context_steward/build_report_generation.txt
- [ ] Add tests for report routing
- [ ] Update tool documentation

**Gate**: All report tests passing

### Phase 2 (High): Ambiguous Document Classification

**Effort**: 2-3 days, ~250 LOC

- [ ] Extend RequestDocRequest: add type="ambiguous" option
- [ ] Create doc_type_classification task
- [ ] Create systemprompts/context_steward/doc_classification.txt
- [ ] Wire classification to automatic routing
- [ ] Add tests for classification accuracy
- [ ] Document classification examples

**Gate**: 90%+ classification accuracy on test suite

### Phase 3 (Medium): Build Plan Support

**Effort**: 2-3 days, ~200 LOC

- [ ] Add build_plan type to RequestDocRequest
- [ ] Add to VISIBILITY_RULES (routing to .coord/build_plans/)
- [ ] Create build_plan_generation task
- [ ] Create systemprompts/context_steward/build_plan_generation.txt
- [ ] Add integration with task-decomposer output
- [ ] Add tests

**Gate**: Build plan format compliance with task-decomposer expectations

### Phase 4 (Medium): ADR AI Generation

**Effort**: 1-2 days, ~150 LOC

- [ ] Create adr_generation task
- [ ] Create systemprompts/context_steward/adr_generation.txt
- [ ] Wire ADR requests through AI instead of template fallback
- [ ] Add tests

**Gate**: Generated ADRs match ADR template structure

### Phase 5 (Low): Session Note AI

**Effort**: 1-2 days, ~100 LOC

- [ ] Wire session_note to AI task (session_compression already defined)
- [ ] Create systemprompts/context_steward/session_note_creation.txt (if needed)
- [ ] Test session note AI extraction
- [ ] Validate against existing session formats

**Gate**: Session note extraction tests passing

---

## Part 6: Type-Specific Placement & Format

### ADR (Architecture Decision Record)

**Path**: `docs/adr/YYYYMMDD-{slug}.md`
**Format**: Markdown with standard ADR sections
**AI Task**: adr_generation
**Owner**: system-steward
**TTL**: Permanent (unless superseded)

```markdown
# ADR-XXX: {Title}

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
[Problem statement, constraints, background]

## Decision
[What was decided and why]

## Consequences
[Trade-offs, implications, future considerations]

## Alternatives Considered
[What else could have been done]
```

### Build Report

**Path**: `.coord/reports/{session_id}-build.md` OR `.coord/reports/YYYY-MM-DD-build-summary.md`
**Format**: Markdown with tables (CI results, test status, build logs)
**AI Task**: build_report_generation
**Owner**: system-steward
**TTL**: 30 days (soft), 90 days (hard)

```markdown
# Build Report: {Date} {Phase}

## Summary
[Pass/fail status, metrics summary]

## CI Pipeline Results
[GitHub Actions status, test results]

## Tests
[Unit test coverage, integration test status, failures]

## Artifacts
[Build outputs, deployment status]

## Issues
[Blockers, flakes, degradations]
```

### Analysis Report

**Path**: `.coord/reports/{session_id}-analysis-{topic}.md`
**Format**: Markdown with findings + recommendations
**AI Task**: analysis_report_generation
**Owner**: system-steward
**TTL**: 60 days (soft), 180 days (hard)

### Status Report

**Path**: `.coord/reports/{session_id}-status.md`
**Format**: Markdown with project state snapshot
**AI Task**: status_report_generation
**Owner**: system-steward
**TTL**: 7 days (soft), 30 days (hard)

### Build Plan

**Path**: `.coord/build_plans/{session_id}-plan.oct.md`
**Format**: OCTAVE (structured, compressible)
**AI Task**: build_plan_generation
**Owner**: implementation-lead
**TTL**: Mutable until execution, then archived

```octave
BUILD_PLAN::[
  session_id::c382418f,
  phase::B2,
  owner::implementation-lead,

  TASKS::[
    {id:1, title:"...", owner:"...", depends:[], status:pending},
    {id:2, title:"...", owner:"...", depends:[1], status:pending}
  ],

  CRITICAL_PATH::[1→2→4→7],
  ESTIMATED_DURATION::3d,
  SUCCESS_CRITERIA::[test_pass, code_review_pass, no_blockers]
]
```

---

## Part 7: Request_Doc Enhancement

### Updated RequestDocRequest Model

```python
class RequestDocRequest(BaseModel):
    type: Literal[
        "adr",
        "context_update",
        "session_note",
        "workflow_update",
        "build_report",           # NEW
        "analysis_report",        # NEW
        "status_report",          # NEW
        "build_plan",             # NEW
        "ambiguous"               # NEW
    ] = Field(..., description="Type of documentation to create")

    intent: str = Field(..., description="What should be documented")

    scope: Literal["full_session", "from_marker", "specific"] = Field(
        "specific", description="Scope of content to document"
    )

    priority: Literal["blocking", "end_of_session", "background"] = Field(
        "end_of_session", description="Priority level for documentation"
    )

    content: str = Field("", description="Content to document (if scope=specific)")

    files: list[str] = Field(
        default_factory=list, description="Files to analyze for context"
    )

    working_dir: str = Field(..., description="Project root path")

    # NEW: Optional topic/category hint for ambiguous requests
    suggested_category: Optional[str] = Field(
        None, description="Optional hint for doc type (e.g., 'architecture', 'performance')"
    )
```

### Response for Ambiguous Classification

```json
{
  "status": "updated_by_ai",
  "path": ".coord/reports/YYYY-MM-DD-analysis-scaling.md",
  "steward": "system-steward",
  "format_applied": "markdown_report",
  "classification": {
    "type": "analysis_report",
    "confidence": 0.95,
    "reasoning": "Technical analysis of scaling limitations → analysis_report type"
  },
  "ai_summary": "Generated analysis report on multi-agent orchestration scaling issues",
  "changes": "..."
}
```

---

## Part 8: Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Ambiguous classification misfires | Medium | Start with manual review of classifications; add feedback loop to improve heuristics |
| Report bloat (too many reports) | Low | Enforce TTL; archive reports older than threshold |
| Build plan conflicts with task-decomposer | Medium | Ensure build_plan schema matches task-decomposer expectations; coordinate with task-decomposer owner |
| AI task overload (too many tasks in config) | Low | Organize tasks by category; use conditional triggers |
| Placement conflicts (file exists in multiple locations) | Low | Multi-location context lookup handles priority; document precedence |

---

## Part 9: Success Metrics

### Phase 1 (Reports)
- [ ] All 3 report types routing correctly
- [ ] Tests 100% passing
- [ ] Reports generated via AI have >80% quality score

### Phase 2 (Ambiguous Classification)
- [ ] Classification accuracy >90% on test suite
- [ ] Misclassified documents <5% in production
- [ ] User satisfaction with classifications >4/5

### Phase 3-5 (Build Plans, ADR AI, Session Notes)
- [ ] All types wired through AI
- [ ] Test coverage >85%
- [ ] Zero template-only fallbacks in production
- [ ] User feedback indicates reduced manual effort

---

## Part 10: Related Systems & Dependencies

- **Task-Decomposer**: Build plans should align with task structure
- **System-Steward**: Owns classification, content synthesis, routing
- **Critical-Engineer**: Validates ADR decisions
- **Implementation-Lead**: Owns build plan execution
- **Context Steward AI**: Generates content via ContextStewardAI class

---

## References

- **Current Implementation**: tools/requestdoc.py, tools/context_steward/ai.py
- **Configuration**: conf/context_steward.json
- **Visibility Rules**: .hestai/rules/VISIBILITY-RULES.md (ADR-003)
- **Tests**: tests/test_requestdoc.py, tests/test_requestdoc_ai.py

---

**Status**: Analysis complete. Recommend proceeding with Phase 1 (Report Support) before B2 completion.

**Owner**: System Steward (documentation + routing intelligence)

**Next Step**: Create issue #XX (Request_Doc Enhancement) to track phases 1-5
