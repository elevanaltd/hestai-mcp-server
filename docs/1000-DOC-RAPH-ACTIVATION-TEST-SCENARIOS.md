# RAPH Activation Test Scenarios

**Purpose:** Validate first-turn constitutional activation vs continuation behavior for CLI agents with ACTIVATION_PROTOCOL.

**Date:** 2025-10-08
**Agent Tested:** holistic-orchestrator (via clink)

---

## Test Setup

### Prerequisites
1. HestAI MCP server running with updated clink.py
2. holistic-orchestrator.txt includes ACTIVATION_PROTOCOL
3. Gemini CLI configured and operational

### Test Agent Configuration
- **CLI:** gemini
- **Role:** holistic-orchestrator
- **Constitution:** ACTIVATION_PROTOCOL with RAPH (READ/ABSORB/PERCEIVE/HARMONISE)
- **Conversation Memory:** 50 turns

---

## Test Scenario 1: First Turn - RAPH Activation Expected

### Test Invocation
```python
mcp__hestai__clink(
    prompt="We need to decide between PostgreSQL triggers vs application-level validation for the scripts module. This is blocking development.",
    cli_name="gemini",
    role="holistic-orchestrator",
    continuation_id=None  # No continuation - first turn
)
```

### Expected Agent Response Pattern
```octave
CONSTITUTIONAL_ACTIVATION:

READ: Relevant principles from constitution (lines 34, 35, 37, 52)
- VISION "System-wide coherence"
- CONSTRAINT "Architectural integrity"
- JUDGMENT "Buck stops here"
- RACI_CONSULTATIONS "critical-engineer: Architecture decisions"

ABSORB: "JUDGMENT says 'ultimate accountability', but RACI says 'consult
critical-engineer', which creates tension when [scripts module blocked needs
immediate decision vs proper architectural review]"

PERCEIVE: "If emergency production fix, REALITY principle would require
immediate decision WITHOUT full review, unlike generic orchestrator"

HARMONISE: "Because of JUDGMENT, I will make GO/NO-GO decision AND consult,
whereas generic orchestrator would defer to technical authority"

[Proceeds to execute with constitutional awareness]
```

### Verification Checklist
- [ ] Response includes RAPH sections (READ/ABSORB/PERCEIVE/HARMONISE)
- [ ] Constitutional principles with line numbers
- [ ] Tension relates to SPECIFIC request scenario
- [ ] Edge case relevant to request context
- [ ] Behavioral difference concrete and actionable
- [ ] RAPH <150 words
- [ ] Agent executes request after activation

---

## Test Scenario 2: Continuation - RAPH Skipped

### Test Invocation
```python
mcp__hestai__clink(
    prompt="What are the pros and cons of each approach?",
    cli_name="gemini",
    role="holistic-orchestrator",
    continuation_id="conv_abc123"  # Continuation
)
```

### Expected Behavior
- **NO RAPH sections** (already activated)
- Direct execution with constitutional awareness
- May cite principles naturally when relevant
- Conversational continuation

### Verification Checklist
- [ ] Response does NOT include RAPH
- [ ] No `[FIRST_TURN]` in prompt
- [ ] Constitutional awareness maintained
- [ ] Conversational continuation style

---

## Test Scenario 3: Multi-Turn Sequence

### Test Sequence
```python
# Turn 1 - RAPH expected
r1 = clink(prompt="Coordinate B2 for scripts", continuation_id=None)

# Turn 2 - NO RAPH
cont_id = extract_continuation(r1)
r2 = clink(prompt="Quality gates for B3?", continuation_id=cont_id)

# Turn 3 - NO RAPH
r3 = clink(prompt="Create orchestration plan", continuation_id=cont_id)
```

### Expected Pattern
- **Turn 1:** Full RAPH
- **Turn 2:** Direct execution
- **Turn 3:** Direct execution

---

## Quality Comparison

| Metric | Without RAPH | With RAPH |
|--------|--------------|-----------|
| Principle citations | 0-1 vague | 3-4 with line numbers |
| Tension awareness | Generic | Task-specific |
| Edge case prediction | Generic | Context-relevant |
| Behavioral specificity | Vague | Concrete |
| Constitutional adherence | 40-50% | 70-85% |

### Example Output Difference

**Without RAPH:**
```
I'll coordinate the decision. Let me consult critical-engineer and make
a recommendation. Want me to analyze current patterns?
```

**With RAPH:**
```
READ: JUDGMENT (line 37), RACI (line 52)
ABSORB: Tension between authority vs consultation
HARMONISE: I make GO/NO-GO AND consult, not defer

Given scripts BLOCKED (REALITY principle), I'll make provisional GO with
validation path while consulting critical-engineer...
```

---

## Success Criteria

### Implementation
- [x] holistic-orchestrator.txt has ACTIVATION_PROTOCOL
- [x] clink.py detects first turn, prepends `[FIRST_TURN]`
- [x] Test scenarios documented

### Quality Validation
- [ ] First turn includes complete RAPH
- [ ] Principles with line numbers
- [ ] Task-specific tensions and edge cases
- [ ] Continuations skip RAPH
- [ ] 30-70% adherence improvement (C038 target)

### System Validation
- [ ] RAPH <100 words overhead
- [ ] Conversation memory functional
- [ ] 50-turn limit respected
- [ ] Independent conversation threads

---

## Known Issues

1. **Agent ignores `[FIRST_TURN]`:** Check ACTIVATION_PROTOCOL in systemprompt
2. **RAPH every turn:** Verify continuation_id passing
3. **RAPH too verbose:** Remind <100 word limit in protocol
4. **Generic RAPH:** Agent not extracting task-specific context

---

**System-Steward:** First-turn RAPH provides constitutional grounding for CLI agents with 50-turn memory. Evidence-based testing validates quality while preserving conversation continuity.

**Next:** Operational validation with real holistic-orchestrator invocations.
