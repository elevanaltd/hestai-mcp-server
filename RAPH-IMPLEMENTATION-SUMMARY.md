# RAPH Activation Implementation Summary

**Date:** 2025-10-08
**Role:** system-steward
**Scope:** CLI agent constitutional activation protocol

---

## Completed Work

### 1. Updated holistic-orchestrator.txt ✅

**Location:** `/Volumes/HestAI-Tools/hestai-mcp-server/systemprompts/clink/holistic-orchestrator.txt`

**Added ACTIVATION_PROTOCOL section:**
```octave
ACTIVATION_PROTOCOL::
  INVOCATION_PATTERN::[FIRST_TURN→constitutional_activation, CONTINUATION→direct_execution]

  FIRST_TURN_ONLY::"When you receive [FIRST_TURN] marker, perform constitutional activation"

  CONSTITUTIONAL_ACTIVATION (complete in <100 words):
    READ: 3-4 principles relevant to THIS request (with line numbers)
    ABSORB: 1 constitutional tension for THIS SPECIFIC TASK
    PERCEIVE: 1 edge case where constitution guides differently
    HARMONISE: 1 behavioral difference vs generic agent

  SUBSEQUENT_TURNS::"Execute directly, no re-activation"
```

**Key Features:**
- Task-specific RAPH (not generic)
- Line number references for principle citations
- Tension template tied to user request
- Edge case prediction for THIS task
- Behavioral difference concrete and actionable

### 2. Enhanced clink.py Tool ✅

**Location:** `/Volumes/HestAI-Tools/hestai-mcp-server/tools/clink.py`

**Changes to `_prepare_prompt_for_role()` method:**

```python
# FIRST_TURN detection for constitutional activation
continuation_id = self.get_request_continuation_id(request)
is_first_turn = not continuation_id

if is_first_turn:
    # Prepend marker for agents with ACTIVATION_PROTOCOL
    user_content = f"[FIRST_TURN]\n\n{user_content}"
```

**Logic:**
1. Check if `continuation_id` exists
2. If None → first turn → prepend `[FIRST_TURN]` marker
3. If exists → continuation → no marker
4. Agent sees marker → performs RAPH activation from ACTIVATION_PROTOCOL
5. Agent in continuation → executes directly

### 3. Created Test Scenarios ✅

**Location:** `/Volumes/HestAI-Tools/hestai-mcp-server/docs/1000-DOC-RAPH-ACTIVATION-TEST-SCENARIOS.md`

**Test Coverage:**
1. **Scenario 1:** First turn - RAPH expected
2. **Scenario 2:** Continuation - RAPH skipped
3. **Scenario 3:** Multi-turn sequence (1 RAPH + N direct)

**Validation Checklist:**
- Response includes RAPH sections
- Constitutional principles with line numbers
- Tension relates to specific request
- Edge case relevant to context
- Behavioral difference concrete
- RAPH <150 words
- Continuations skip RAPH

**Quality Metrics:**
- Constitutional adherence: 40-50% → 70-85% (30-70% improvement)
- Principle citations: 0-1 vague → 3-4 specific with line numbers
- Behavioral specificity: Vague → Concrete

---

## Architecture Decisions

### ✅ Why RAPH on First Turn Only?

**Problem:**
- CLI agents have 50-turn conversation memory
- RAPH every turn = wasteful + dilutes effectiveness
- RAPH never = no constitutional grounding

**Solution:**
- Constitutional activation = ONCE per conversation
- Continuation_id detection → first turn vs continuation
- Agent maintains constitutional awareness across turns

### ✅ Why Task-Specific RAPH?

**Original concern:**
> "Is there not a middle ground that would work?"

**Middle ground achieved:**
- True RAPH structure (READ/ABSORB/PERCEIVE/HARMONISE)
- **But** connected to actual task at hand
- Not "list principles" but "which principles apply HERE"
- Tension template: "Principle X says Y, which conflicts when [user request scenario]"

**Example:**
```
ABSORB: "JUDGMENT says 'ultimate accountability', but RACI says
'consult critical-engineer', which creates tension when scripts module
blocked needs immediate decision vs proper architectural review"
```

### ✅ System Prompt + User Prompt Timing

**Key insight:**
```
SYSTEM (constitution + RAPH template)
    ↓
USER ([FIRST_TURN] + request)
    ↓
Agent processes BOTH simultaneously
```

**This enables:**
- Constitution available as context
- RAPH can reference user request
- Task-grounded constitutional activation

### ✅ Continuation Detection

**Implementation:**
```python
continuation_id = self.get_request_continuation_id(request)
is_first_turn = not continuation_id
```

**Simplicity:**
- No continuation_id = first turn
- Has continuation_id = continuation
- Clean, reliable detection

---

## Evidence

### Git Commit
```bash
git log -1 --oneline
# af31956 feat: implement first-turn RAPH activation for CLI agents
```

### Files Modified
- `systemprompts/clink/holistic-orchestrator.txt` (new - 461 lines)
- `tools/clink.py` (+12 lines)
- `docs/1000-DOC-RAPH-ACTIVATION-TEST-SCENARIOS.md` (new - 182 lines)

### Implementation Metrics
| Metric | Value |
|--------|-------|
| Token overhead (first turn) | ~200-300 tokens |
| Token overhead (continuation) | 0 tokens |
| RAPH target length | <100 words |
| Expected quality improvement | 30-70% (C038) |
| Conversation memory | 50 turns |
| RAPH frequency | Once per conversation |

---

## Testing Guidance

### Manual Test
```python
# Test 1: First turn
mcp__hestai__clink(
    prompt="Architecture decision: PostgreSQL triggers vs app validation",
    cli_name="gemini",
    role="holistic-orchestrator",
    continuation_id=None  # First turn
)
# Expected: RAPH sections in response

# Test 2: Continuation
cont_id = extract_continuation_id(response1)
mcp__hestai__clink(
    prompt="What are pros/cons?",
    cli_name="gemini",
    role="holistic-orchestrator",
    continuation_id=cont_id  # Continuation
)
# Expected: NO RAPH, direct execution
```

### Verification
- [ ] First turn includes READ/ABSORB/PERCEIVE/HARMONISE
- [ ] Constitutional principles cited with line numbers
- [ ] Tension relates to specific user request scenario
- [ ] Continuation turns skip RAPH
- [ ] Constitutional awareness maintained across turns

---

## Next Steps

### Immediate
1. **Operational testing** with real holistic-orchestrator invocations
2. **Quality assessment** - measure constitutional adherence improvement
3. **User feedback** on RAPH quality and task-specificity

### Short-term
1. **Port to other specialist agents** (quality-observer, surveyor, etc.)
2. **Refine RAPH template** based on operational learnings
3. **Automated testing** - unit tests for first-turn detection

### Long-term
1. **Constitutional adherence metrics** - systematic measurement
2. **RAPH quality scoring** - task-specificity assessment
3. **Multi-agent RAPH patterns** - constitutional coherence across agents

---

## Key Learnings

### ✅ Middle Ground Found

**Question:** "Is there not a middle ground that would work?"

**Answer:** Yes - task-grounded RAPH:
- Maintains true RAPH structure
- But framed around "THIS TASK" not abstract principles
- Forces agent to extract task context and map to constitution
- Example: "Tension when [specific scenario from user request]"

### ✅ Conversation Architecture Respected

**Question:** "What's the way to do RAPH initially, but not every time?"

**Answer:** Continuation detection:
- First turn (no continuation_id) → Full RAPH
- Continuation (has continuation_id) → Direct execution
- Clean, reliable, respects 50-turn memory architecture

### ✅ System + User Prompt Synergy

**Insight:** System prompt and user prompt processed simultaneously
- Constitution available when processing `[FIRST_TURN]`
- RAPH template can reference user request
- Enables task-specific constitutional grounding

---

## Success Criteria

### Implementation ✅
- [x] holistic-orchestrator.txt includes ACTIVATION_PROTOCOL
- [x] clink.py detects first turn and prepends `[FIRST_TURN]`
- [x] Test scenarios documented
- [x] Git commit with implementation evidence

### Quality (Pending Operational Validation)
- [ ] First turn responses include complete task-specific RAPH
- [ ] Constitutional principles cited with line numbers
- [ ] Tension and edge cases are request-specific
- [ ] Continuations skip RAPH and execute directly
- [ ] 30-70% constitutional adherence improvement measured

### System (Pending Validation)
- [ ] RAPH overhead <100 words
- [ ] Conversation memory functions correctly
- [ ] 50-turn limit respected
- [ ] Independent conversation threads maintained

---

**System-Steward Observation:**
First-turn RAPH activation successfully implemented for CLI agents with 50-turn conversation memory. Task-specific constitutional grounding achieved through middle-ground approach: true RAPH structure applied to "THIS TASK" not abstract principles. Continuation detection respects conversation architecture while ensuring constitutional identity grounding at initiation.

**Next Phase:**
Operational validation with real holistic-orchestrator invocations to measure quality improvement and refine RAPH template based on empirical evidence.

---

**Implementation Evidence:**
- Git commit: `af31956`
- Files: 3 modified (systemprompt, tool, docs)
- Lines: +473 (461 new agent + 12 tool logic)
- Test scenarios: 3 comprehensive scenarios with validation checklists
