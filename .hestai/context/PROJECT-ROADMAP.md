# PROJECT-ROADMAP: HestAI MCP Server

## Current Focus
**Context Steward v2** - Document governance layer with inbox pattern

Task Tracking: https://github.com/orgs/elevanaltd/projects/4

---

## Phase 1: Context Steward v2 (Current)

### Pre-requisites (Critical-Engineer Assessment)
- #82: Expand PROJECT-CONTEXT.md to 150-200 LOC
- #83: Create current_state.oct State Vector
- #84: Create CONTEXT-NEGATIVES.oct

### Foundation
- #85: Extract shared modules
- #86: Create inbox directory structure
- #87: Update clock_in for State Vector
- #88: Implement document_submit tool

### Context Management
- #89: Implement context_update tool
- #90: Enrich AI prompts with signals
- #91: Conflict detection with continuation_id

### Completion
- #92: Deprecate request_doc
- #93: Validation Gate (BLOCKING for rollout)

**Spec**: `.hestai/workflow/CONTEXT-STEWARD-V2-SPEC.oct.md`

---

## Phase 2: clink Enhancement (Next)

### #66 - Blockage Detection in clink
Detect when CLI agents are blocked/stuck and inject recovery protocols.

### #67 - Response Analyzer Framework
Intelligent relay that analyzes clink responses for quality/completeness.

### #68 - Hook + MCP Hybrid Enforcement
Combine SessionStart hooks with MCP tools for comprehensive governance.

**Dependencies**: Requires Phase 1 complete (Context Steward foundation)

---

## Phase 3: Infrastructure Stability

### #52 - CI Test Suite Stability
Enforce test stability in CI pipeline.

### #48 - Test Metrics Tracking
Establish canonical test suite baseline.

### #47 - Automated clink/apilookup Tests
Add comprehensive tests for CLI delegation tools.

### #45 - Simulator Test Improvements
Infrastructure improvements for communication_simulator_test.py

---

## Phase 4: Architecture Evolution

### #51 - server.py Refactor
Reduce merge surface before Gemini SDK migration.

### #53 - Upstream Sync Strategy
Plan for zen-mcp-server divergence management.

### #50 - Health Instrumentation
Runtime health and operational metrics.

### #49 - Configuration Externalization
Workspace boundaries and session limits to config.

---

## Phase 5: New Capabilities

### #42 - TestGenTool
Comprehensive test suite generation.

### #41 - DocgenTool
Automated code documentation generation.

### #32 - Constitutional Capsules
CLI constitutional injection for agent prompting.

---

## Backlog

### #44 - zen-mcp-server Improvements
Review and apply infrastructure improvements.

### #31 - Archive Cleanup
Optional: Archive .integration-backup directory.

---

## Priority Order
1. **Phase 1** - Context Steward v2 (current)
2. **Phase 2** - clink enhancement trilogy (#66-68)
3. **Phase 3** - Test infrastructure (#52, #48, #47, #45)
4. **Phase 4** - Architecture stability (#51, #53)
5. **Phase 5** - New capabilities (#42, #41, #32)
