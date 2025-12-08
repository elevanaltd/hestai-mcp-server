# Build Plan: Context Steward Session Lifecycle Tools

**Issue**: #71
**Branch**: `feat/context-steward-session-lifecycle`
**Phase**: B2 (TDD Implementation)

---

## RACI Matrix

| Task | Responsible | Accountable | Consulted | Informed |
|------|-------------|-------------|-----------|----------|
| Tool Implementation | implementation-lead | holistic-orchestrator | - | - |
| Code Review | code-review-specialist (Codex) | holistic-orchestrator | - | implementation-lead |
| Validation Gate | critical-engineer (Gemini) | holistic-orchestrator | - | implementation-lead |
| Test Writing | implementation-lead | holistic-orchestrator | test-methodology-guardian | - |

---

## TRACEd Compliance

```octave
T::TEST_FIRST[
  PATTERN::RED→GREEN→REFACTOR,
  EVIDENCE::git_commits_show_test_before_impl,
  COVERAGE::each_tool_has_unit_tests
]

R::CODE_REVIEW[
  AGENT::code-review-specialist_via_Codex,
  TIMING::after_each_tool_implementation,
  CRITERIA::SimpleTool_pattern_compliance+error_handling+security
]

A::ARCHITECTURAL_VALIDATION[
  AGENT::critical-engineer_via_Gemini,
  TIMING::before_PR_merge,
  CRITERIA::ADR-003_compliance+system_coherence
]

C::CONSULT[
  DOMAIN_TRIGGERS::[
    JSONL_parsing→research_report_800,
    visibility_rules→ADR-003,
    tool_patterns→SimpleTool_base_class
  ]
]

E::QUALITY_GATES[
  LINT::"ruff check . --fix",
  FORMAT::"black . && isort .",
  TYPECHECK::"# Python typing",
  TEST::"python -m pytest tests/ -v -m 'not integration'"
]

D::TODOWRITE+ATOMIC_COMMITS[
  PATTERN::one_tool=one_commit,
  FORMAT::conventional[feat|test|fix]
]
```

---

## Implementation Order

### Tool 1: `clock_in` (Foundation)

**File**: `tools/clockin.py`

**Purpose**: Register session start, detect conflicts, return context paths

**Input Schema**:
```python
class ClockInRequest(ToolRequest):
    role: str                    # Required: agent role name
    focus: str = "general"       # Optional: work focus area
    working_dir: str             # Required: project path
```

**Output**:
```python
{
    "session_id": str,           # UUID short
    "context_paths": {
        "project_context": ".hestai/context/PROJECT-CONTEXT.md",
        "checklist": ".hestai/context/PROJECT-CHECKLIST.md"
    },
    "conflict": null | {...},    # If another session active
    "instruction": "Read context_paths. Produce Full RAPH. Submit anchor."
}
```

**Key Logic**:
1. Scan `.hestai/sessions/active/` for conflicts
2. Generate session_id (uuid short)
3. Create `.hestai/sessions/active/{session_id}/session.json`
4. Return context paths (not content)

**Tests Required**:
- `test_clockin_creates_session_directory`
- `test_clockin_detects_focus_conflict`
- `test_clockin_returns_context_paths`
- `test_clockin_handles_missing_hestai_dir`

---

### Tool 2: `clock_out` (Core Value)

**File**: `tools/clockout.py`

**Purpose**: Extract JSONL, compress to OCTAVE, archive session

**Input Schema**:
```python
class ClockOutRequest(ToolRequest):
    session_id: str              # Required: from clock_in
    description: str = ""        # Optional: session summary
```

**Output**:
```python
{
    "summary": str,              # OCTAVE compressed
    "proposed_updates": [...],   # Context changes to apply
    "archive_path": str,         # Where archived
    "message_count": int
}
```

**Key Logic** (from research report L230-289):
```python
def encode_project_path(path: str) -> str:
    return path.replace("/", "-").lstrip("-")

def find_latest_session(project_path: str) -> Path:
    encoded = encode_project_path(project_path)
    session_dir = Path.home() / ".claude/projects" / encoded
    return max(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)

def parse_session_transcript(jsonl_path: Path) -> list[dict]:
    # Extract user/assistant/thinking messages
    # Include thinking where relevant (agent decision)
```

**Tests Required**:
- `test_clockout_finds_session_jsonl`
- `test_clockout_parses_messages_correctly`
- `test_clockout_archives_to_correct_location`
- `test_clockout_handles_missing_session`

---

### Tool 3: `request_doc` (ADR-003 Innovation)

**File**: `tools/requestdoc.py`

**Purpose**: Route documentation requests to correct location via visibility rules

**Input Schema**:
```python
class RequestDocRequest(ToolRequest):
    type: Literal["adr", "context_update", "session_note", "workflow_update"]
    intent: str                  # What should be documented
    scope: Literal["full_session", "from_marker", "specific"] = "specific"
    priority: Literal["blocking", "end_of_session", "background"] = "end_of_session"
    content: str = ""            # If scope=specific
```

**Output**:
```python
{
    "status": "queued" | "created" | "error",
    "path": str,                 # Where doc was/will be created
    "steward": "system-steward"  # Extended role handles all
}
```

**Routing Logic** (from ADR-003 L124-175):
```python
VISIBILITY_RULES = {
    "adr": ("docs/adr/", "ADR_template"),
    "context_update": (".hestai/context/", "OCTAVE"),
    "session_note": (".hestai/sessions/", "OCTAVE"),
    "workflow_update": (".hestai/workflow/", "OCTAVE")
}
```

**Tests Required**:
- `test_requestdoc_routes_adr_to_docs`
- `test_requestdoc_routes_context_to_hestai`
- `test_requestdoc_validates_type_enum`
- `test_requestdoc_queues_for_priority`

---

### Tool 4: `anchor_submit` (Validation)

**File**: `tools/anchorsubmit.py`

**Purpose**: Validate agent anchor, detect drift, return enforcement rules

**Input Schema**:
```python
class AnchorSubmitRequest(ToolRequest):
    session_id: str
    anchor: dict                 # SHANK + ARM + FLUKE structure
```

**Output**:
```python
{
    "validated": bool,
    "drift_warning": null | str,
    "enforcement": {
        "blocked_paths": [...],  # Role-based restrictions
        "delegation_required": [...]
    }
}
```

**Tests Required**:
- `test_anchorsubmit_validates_structure`
- `test_anchorsubmit_detects_phase_drift`
- `test_anchorsubmit_returns_ho_blocked_paths`
- `test_anchorsubmit_stores_anchor_file`

---

## Reference Files

| Reference | Path | Purpose |
|-----------|------|---------|
| SimpleTool Pattern | `tools/simple/base.py` | Base class to extend |
| Tool Registration | `tools/__init__.py` | Add new tool imports |
| JSONL Research | `.coord/reports/cs-tool/800-REPORT...` | Extraction patterns |
| ADR-003 | `eav-monorepo/docs/adr/ADR-003...` | Visibility rules |
| Visibility Rules | `.hestai/rules/VISIBILITY-RULES.md` | Local reference |

---

## Quality Gate Sequence

```
1. implementation-lead → implements tool with TDD
2. ./code_quality_checks.sh → lint+format+test
3. code-review-specialist (Codex) → review changes
4. critical-engineer (Gemini) → validate architecture
5. holistic-orchestrator → approve for merge
```

---

## Commit Strategy

```bash
# Per tool:
git add tests/test_{tool}.py
git commit -m "test({tool}): add unit tests for {tool} tool"

git add tools/{tool}.py tools/__init__.py
git commit -m "feat({tool}): implement {tool} Context Steward tool

- {key feature 1}
- {key feature 2}
- Ref: #71"
```

---

**Authority**: holistic-orchestrator
**Delegation**: implementation-lead
**Validation**: CRS (Codex) + CE (Gemini)
