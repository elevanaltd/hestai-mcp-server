# Request_Doc Tool: Current vs. Proposed State

## TL;DR: Critical Gaps Identified

The `request_doc` tool was designed to route documentation through Context Steward, but has **5 critical gaps** preventing production use for all document types:

| Need | Status | Gap |
|------|--------|-----|
| **Reports** (build, analysis, status) | ❌ Not supported | No enum values, no routing, no AI tasks |
| **Build Plans** | ❌ Not supported | Not in system at all |
| **Ambiguous Docs** | ❌ Not handled | No classifier; user must manually choose type |
| **ADR Content Generation** | ⚠️ Partial | Template only, no AI synthesis |
| **Session Note AI** | ⚠️ Partial | Task defined in config but not wired |

---

## Current State (4 of 4 Partial Implementations)

### What Works Fully

```
context_update → PROJECT-CONTEXT.md (AI synthesis via ContextStewardAI)
workflow_update → PROJECT-CHECKLIST.md (AI synthesis via ContextStewardAI)
```

### What Works Partially

```
adr → docs/adr/ (Template fallback, no AI)
session_note → .hestai/sessions/ (Template fallback, no AI)
```

### What Doesn't Work

```
build_report → ❌ Not in enum
analysis_report → ❌ Not in enum
status_report → ❌ Not in enum
build_plan → ❌ Not in enum
ambiguous → ❌ Not in enum (no classification)
```

---

## The Core Problem

**Design**: request_doc → VISIBILITY_RULES → AI task → write document

**Reality**:
- VISIBILITY_RULES only has 4 entries (adr, context_update, session_note, workflow_update)
- TASK_MAPPING only maps 2 of them to AI (context_update, workflow_update)
- New document types (reports, build_plans) have no rules or tasks
- Ambiguous documents have no classification mechanism

**Result**: Agents cannot request new document types. System fails silently.

---

## What Context Steward Can Handle

**Currently Wired**:
- `project_context_update` — Intelligently merges facts into PROJECT-CONTEXT.md
- `project_checklist_update` — Updates PROJECT-CHECKLIST.md

**Defined but Not Triggered**:
- `session_compression` — Extracts key learnings from sessions (trigger defined, not implemented)

**Completely Missing**:
- `adr_generation` — Could intelligently generate ADR Decision/Consequences
- `session_note_creation` — Could extract session insights
- `build_report_generation` — Could synthesize CI/test results
- `analysis_report_generation` — Could generate technical analysis
- `status_report_generation` — Could snapshot project state
- `build_plan_generation` — Could create implementation plans
- `doc_type_classification` — Could classify ambiguous requests

---

## Proposed Solution: Unified Routing

### 1. Extend VISIBILITY_RULES

```python
VISIBILITY_RULES = {
    "adr": {"path": "docs/adr/", "format": "ADR_markdown"},
    "context_update": {"path": ".hestai/context/", "format": "OCTAVE"},
    "session_note": {"path": ".hestai/sessions/", "format": "OCTAVE"},
    "workflow_update": {"path": ".hestai/workflow/", "format": "OCTAVE"},
    
    # NEW
    "build_report": {"path": ".coord/reports/", "format": "markdown_report"},
    "analysis_report": {"path": ".coord/reports/", "format": "markdown_report"},
    "status_report": {"path": ".coord/reports/", "format": "markdown_report"},
    "build_plan": {"path": ".coord/build_plans/", "format": "OCTAVE_build_plan"},
    "ambiguous": {"path": "CLASSIFY_VIA_SYSTEM_STEWARD", "format": "DETECT"},
}
```

### 2. Extend TASK_MAPPING

```python
TASK_MAPPING = {
    "context_update": "project_context_update",        # EXISTING
    "workflow_update": "project_checklist_update",     # EXISTING
    "adr": "adr_generation",                           # NEW
    "session_note": "session_note_creation",           # NEW (wire existing)
    "build_report": "build_report_generation",         # NEW
    "analysis_report": "analysis_report_generation",   # NEW
    "status_report": "status_report_generation",       # NEW
    "build_plan": "build_plan_generation",             # NEW
    "ambiguous": "doc_type_classification",            # NEW
}
```

### 3. Add Tasks to conf/context_steward.json

Add 7 task definitions:
- `adr_generation` — Intelligently generate ADR Decision/Consequences
- `session_note_creation` — Extract session insights (wire existing trigger)
- `build_report_generation` — Synthesize CI/test results
- `analysis_report_generation` — Generate technical analysis
- `status_report_generation` — Snapshot project state
- `build_plan_generation` — Create implementation plans
- `doc_type_classification` — Classify ambiguous requests

### 4. Handle Ambiguous Documents via Classification

When user requests:
```python
request_doc(
    type="ambiguous",
    intent="Analyze what we learned about multi-agent scaling",
    files=["session_transcript.txt", "test_results.json"]
)
```

System:
1. Routes to `doc_type_classification` AI task
2. System-steward classifies intent → "analysis_report"
3. Automatically routes to `analysis_report_generation` task
4. Writes to `.coord/reports/YYYY-MM-DD-analysis-scaling.md`
5. Returns classification with reasoning

---

## Implementation Roadmap

### Phase 1: Reports (Critical)
**Timeline**: 2-3 days, 3 new types
**Effort**: ~200 LOC

- Add build_report, analysis_report, status_report to RequestDocRequest
- Add to VISIBILITY_RULES
- Create 3 AI tasks in config
- Create 3 prompt templates
- Tests passing

### Phase 2: Ambiguous Classification (High)
**Timeline**: 2-3 days, intelligent routing
**Effort**: ~250 LOC

- Add "ambiguous" type to enum
- Create `doc_type_classification` AI task
- Classification prompt template
- Automatic routing to recommended type
- Classification confidence tracking

### Phase 3: Build Plans (Medium)
**Timeline**: 2-3 days
**Effort**: ~200 LOC

- Add build_plan type
- Create build_plan_generation task
- OCTAVE schema for plans
- Integration with task-decomposer

### Phase 4: ADR AI (Medium)
**Timeline**: 1-2 days
**Effort**: ~150 LOC

- Create adr_generation task
- Prompt template for Decision/Consequences synthesis
- Replace template fallback

### Phase 5: Session Note AI (Low)
**Timeline**: 1-2 days
**Effort**: ~100 LOC

- Wire session_note to session_note_creation task
- Test extraction of insights

---

## Key Insight: "Ambiguous" Is a Feature

**Current Problem**: Users don't know which type to choose
```
User: "Document scaling analysis"
System: "Is that an ADR? A report? A context update?"
User: "I don't know... just pick one?"
```

**Solution**: Let system-steward classify
```
User: "Document scaling analysis"
System: "Classified as analysis_report. Routing to .coord/reports/"
User: "Perfect"
```

**Implementation**: One AI task (`doc_type_classification`) enables routing all ambiguous requests intelligently.

---

## Where Context Steward Shines

Context Steward is already wired to intelligently handle **synthesis and merging**:

✅ `project_context_update` — Merges new facts into existing context (40-line prompt)
✅ `project_checklist_update` — Updates task status intelligently

**These same patterns can extend to**:
- ADR generation (synthesize Decision from context)
- Report generation (synthesize from logs/data)
- Build plans (decompose into tasks)
- Classification (route ambiguous requests)

**The pattern is identical**: LLM receives context + intent → generates structured output → request_doc writes to disk.

---

## Risk: AI Task Overload

With all 7 new tasks, conf/context_steward.json becomes large. **Mitigation**:

1. **Use conditional triggers** — Only run if type matches
2. **Group by category** — Organize tasks by document family (reports, context, plans)
3. **Disable by default** — Enable incrementally as phases complete
4. **Document each task** — Clear prompt template per type

---

## Success Metrics

### Phase 1: Reports Working
- [ ] All 3 report types route correctly
- [ ] Tests 100% passing
- [ ] AI-generated reports have >80% structural quality

### Phase 2: Ambiguous Classification
- [ ] Classification accuracy >90%
- [ ] Misclassification <5% in production

### Phase 3-5: All Types Wired
- [ ] Zero template-only fallbacks
- [ ] All tests passing
- [ ] Measurable reduction in manual doc work

---

## Related Issues

- **Issue #78**: ADR-004 (Context Management Enhancement)
- **Issue #79**: ADR-005 (Request_Doc Enhancement) ← THIS ISSUE
- **Issue #76**: Context exhaustion (may impact report scope)
- **ADR-003**: Visibility rules (foundation)

---

## Questions Answered from Your Research

**Q: Are reports meant to be handled through request_doc?**
A: Yes, but not yet implemented. This issue adds support.

**Q: How will context steward handle them?**
A: Via new AI tasks (`build_report_generation`, etc.) using same pattern as context_update.

**Q: What about ambiguous docs that don't fit categories?**
A: New "ambiguous" type routes through `doc_type_classification` AI task for intelligent routing.

**Q: Are all 4 types meant to go through request_doc?**
A: **Yes** (adr, context_update, session_note, workflow_update) + NEW types (reports, build_plans). All flow through same routing system.

**Q: Current status?**
- context_update ✅ Fully wired
- workflow_update ✅ Fully wired
- adr ⚠️ Template only (ready for AI wiring)
- session_note ⚠️ Template only (ready for AI wiring)
- reports ❌ Not in system
- build_plans ❌ Not in system
- ambiguous ❌ No classification

---

## Files Affected

**To Add**:
- `systemprompts/context_steward/adr_generation.txt`
- `systemprompts/context_steward/session_note.txt`
- `systemprompts/context_steward/build_report.txt`
- `systemprompts/context_steward/analysis_report.txt`
- `systemprompts/context_steward/status_report.txt`
- `systemprompts/context_steward/build_plan.txt`
- `systemprompts/context_steward/doc_classification.txt`
- `.coord/reports/` (directory for report storage)
- `.coord/build_plans/` (directory for build plan storage)

**To Modify**:
- `tools/requestdoc.py` (extend RequestDocRequest enum + routing logic)
- `conf/context_steward.json` (add 7 new task definitions)
- `tests/test_requestdoc.py` (add tests for new types)

**Documentation**:
- `.hestai/context/REQUEST-DOC-ANALYSIS.oct.md` (this analysis)
- `.hestai/rules/VISIBILITY-RULES.md` (update with new types)

---

**Status**: Analysis complete. Ready for Phase 1 implementation.
**Owner**: Implementation Lead
**Next Step**: Accept issue #79 for Phase 1 work (reports support)
