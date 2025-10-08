# Agent Inventory for Platform Categorization

**Total Agents:** 61

**Categorization Task:** Determine optimal execution platform (Gemini CLI, Codex CLI, or Claude Code) based on agent characteristics.

## Complete Agent List

1. accounting-partner.oct.md
2. build-plan-checker.oct.md
3. code-review-specialist.oct.md
4. coherence-oracle.oct.md
5. completion-architect.oct.md
6. complexity-guard.oct.md
7. compression-fidelity-validator.oct.md
8. critical-design-validator.oct.md
9. critical-engineer-sonnet.oct.md
10. critical-engineer.oct.md
11. critical-implementation-validator.oct.md
12. design-architect.oct.md
13. directory-curator.oct.md
14. documentation-compressor.oct.md
15. documentation-researcher.oct.md
16. eav-admin.oct.md
17. eav-coherence-oracle.oct.md
18. edge-optimizer.oct.md
19. error-architect-surface.oct.md
20. error-architect.oct.md
21. hestai-doc-steward.oct.md
22. holistic-orchestrator.oct.md
23. idea-clarifier.oct.md
24. ideator-catalyst.oct.md
25. ideator.oct.md
26. implementation-lead.oct.md
27. octave-forge-master.oct.md
28. octave-specialist.oct.md
29. octave-validator.oct.md
30. quality-observer.oct.md
31. raph-absorb.oct.md
32. raph-harmonise.oct.md
33. raph-perceive.oct.md
34. raph-read-max.oct.md
35. raph-read.oct.md
36. requirements-steward.oct.md
37. research-analyst-pattern-extractor.oct.md
38. research-analyst.oct.md
39. research-curator-subagent.oct.md
40. research-curator.oct.md
41. security-specialist.oct.md
42. semantic-optimizer.oct.md
43. session-briefer.oct.md
44. sessions-manager.oct.md
45. smartsuite-expert.oct.md
46. solution-steward.oct.md
47. subagent-creator.oct.md
48. subagent-system-tester.md
49. synthesizer.oct.md
50. system-steward.oct.md
51. task-decomposer-validator.oct.md
52. task-decomposer.oct.md
53. technical-architect-sonnet.oct.md
54. technical-architect.oct.md
55. test-curator.oct.md
56. test-methodology-guardian.oct.md
57. universal-test-engineer.oct.md
58. validator.oct.md
59. visual-architect.oct.md
60. workflow-scope-calibrator.oct.md
61. workspace-architect.oct.md

## Categorization Criteria

### GEMINI CLI (Free tier, 1M context, autonomous exploration)
**Best For:**
- Broad codebase exploration and pattern discovery
- Research and analysis requiring high token capacity
- Autonomous file discovery across large projects
- Pattern extraction and synthesis
- Documentation analysis and compression

**Keywords to Look For:** research, analysis, exploration, pattern, discovery, synthesis, documentation, curator

### CODEX CLI (Flat-rate subscription, code-focused)
**Best For:**
- Deep code review and analysis
- Implementation validation
- Code quality assessment
- Refactoring suggestions
- Technical architecture analysis

**Keywords to Look For:** code review, implementation, refactor, quality, technical, architecture

### CLAUDE CODE (Limited quota, high-value constitutional work)
**Best For:**
- Constitutional authority and GO/NO-GO decisions
- BLOCKING authority (can halt processes)
- Critical validation (critical-engineer, testguard)
- Actual implementation and code generation
- Strategic orchestration with authority

**Keywords to Look For:** BLOCKING, GO/NO-GO, authority, constitutional, critical, implementation-lead, orchestrator (with authority), steward (with enforcement)

## Special Cases

**Dual Platform Consideration:**
- Agents with both exploration AND validation roles may benefit from running exploration on Gemini/Codex, then validation on Claude Code
- Example: research-analyst (Gemini) → findings passed to → critical-engineer (Claude) for validation

**OCTAVE Framework Agents (meta):**
- octave-specialist, octave-forge-master, octave-validator, subagent-creator
- These may need Claude Code for their generative/transformative capabilities

**RAPH Processing Agents:**
- raph-read, raph-absorb, raph-perceive, raph-harmonise
- These are analysis/synthesis focused → likely Gemini CLI

**Context-Specific:**
- eav-admin, smartsuite-expert (domain-specific business logic)
- sessions-manager, session-briefer (system utilities)
- May depend on whether they make authority decisions

## Instructions for Analysis

Based on agent names alone (without reading full files), categorize each of the 61 agents into:
1. **gemini_cli_agents** - Exploration, research, analysis, pattern discovery
2. **codex_cli_agents** - Code review, implementation analysis, technical assessment
3. **claude_code_agents** - Constitutional authority, GO/NO-GO decisions, implementation
4. **needs_review** - Unclear from name alone, requires description analysis

Use name patterns, keywords, and role implications to make initial categorization.
