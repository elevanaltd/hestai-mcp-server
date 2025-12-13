# 810-REPORT: HestAI Core - Identity & Context Architecture

**Date:** December 12, 2025
**Type:** Architectural Specification
**Status:** DRAFT (Approved Concept)
**Author:** HestAI MCP (via Codebase Investigator)
**References:**
- `000-LIVING-ORCHESTRA-D1-NORTH-STAR.md` (Governance)
- `HESTAI-SYSTEM-OVERVIEW.md` (System Vision)
- `CURRENT-WORKING-STATE.md` (Operational Reality)
- `BLOCKAGE_RESOLUTION_PROTOCOL.oct.md` (Protocol)

---

## 1. Executive Summary

The **HestAI Core Server** is a new, standalone MCP server dedicated exclusively to **Identity** (Agent Roles, Prompts, RAPH Protocols) and **Context Management** (Project State, ADRs, Workflows).

It solves the "Fat Client" problem where intelligence is locked in local CLI configurations. By centralizing identity and context in an MCP server, any client (Claude, Gemini, Codex) can instantly become a "Living Orchestra" agent.

**Core Philosophy:**
- **Thin Client:** The CLI tool (Claude, Gemini) is just the "Body".
- **Fat Server:** HestAI Core is the "Soul" (Identity) and "Memory" (Context).
- **Universal Driver:** Connect any client to HestAI Core to hydrate it with full project intelligence.

---

## 2. Architecture: The "Soul & Memory" Server

The server provides two primary toolsets: `identity` and `context`.

### 2.1 Identity Provider (The Soul)

Responsible for defining *who* the agent is and *how* they think.

**Tool: `load_identity`**
- **Input:** `role` (e.g., "implementation-lead"), `mode` (e.g., "fast-track" or "full-raph")
- **Process:**
    1.  **Retrieve Role:** Loads the specific Agent Constitution (Shank + Arm + Fluke) from the server's internal library.
    2.  **Inject Governance:** Prepends the **North Star (7 Immutables)** and **Project Context** to the prompt.
    3.  **Inject Protocol:** Adds the **RAPH Protocol** instruction block, requiring the agent to "Read, Absorb, Perceive, Harmonize" before acting.
- **Output:** A comprehensive System Prompt string. The client (Claude) receives this and adopts the persona.

**Tool: `list_roles`**
- **Output:** Returns a list of available roles (e.g., `holistic-orchestrator`, `critical-engineer`) with descriptions, allowing the user to choose.

### 2.2 Context Manager (The Memory)

Responsible for abstracting the file system and ensuring structural compliance (Living Orchestra).

**Tool: `clock_in`**
- **Input:** `focus_area`
- **Process:** Checks git status (clean worktree?), loads `PROJECT-CONTEXT.md`, establishes the session, and returns the **State Vector** (current phase, blockers, active focus).

**Tool: `submit_artifact`**
- **Input:** `type` (ADR, Session Note, Decision), `content`
- **Process:**
    - Auto-formats the content (e.g., adds YAML frontmatter, timestamps).
    - Places it in the correct directory (e.g., `.hestai/docs/adr/`).
    - Updates the index.
    - **Benefit:** Agent doesn't need to know *where* files go, just *what* they are.

**Tool: `update_context`**
- **Input:** `section` (e.g., "Current State"), `update`
- **Process:** Smartly merges updates into `PROJECT-CONTEXT.md` using the "Living Artifacts" principle, preventing staleness.

### 2.3 Protocol Engine (The Conductor)

Responsible for workflow enforcement.

**Tool: `resolve_blockage`**
- **Trigger:** Agent hits a "Wall" (Blocker).
- **Process:** Loads the `BLOCKAGE_RESOLUTION_PROTOCOL` (Wind vs. Wall vs. Door) and guides the agent through the 3-round debate format.

---

## 3. Migration Plan: From "Config" to "Server"

We will extract assets from `hestai-mcp-server` and `.claude` config to build HestAI Core.

| Component | Source (Current) | Destination (HestAI Core) | Transformation |
| :--- | :--- | :--- | :--- |
| **Agent Roles** | `.claude/agents/*.oct.md` & `systemprompts/clink/*.txt` | `library/identities/` | Unified YAML/Markdown format with Shank/Arm/Fluke structure. |
| **North Star** | `.hestai/workflow/000-LIVING-ORCHESTRA...md` | `library/governance/north_star.md` | Injected automatically into every `load_identity` call. |
| **Context Logic** | `tools/clockin.py` (Custom) | `tools/context_manager.py` | Refined to support the `.hestai` unified directory structure. |
| **Protocols** | `BLOCKAGE_RESOLUTION_PROTOCOL.oct.md` | `library/protocols/` | Converted to an interactive MCP workflow tool. |

---

## 4. User Workflow (The "Living Orchestra" Experience)

1.  **Connect:** User opens Claude Desktop or Terminal.
2.  **Select Role:** User runs tool `list_roles`.
3.  **Hydrate:** User runs `load_identity(role="critical-engineer")`.
    *   *System:* "Loading Critical Engineer... Injecting North Star... Harmonizing..."
4.  **Work:**
    *   Agent: "I am ready. Clocking in..." -> `clock_in(focus="Audit")`.
    *   Agent: "Checking Context..." -> Reads State Vector.
    *   Agent: "I see a blocker. Initiating Protocol..." -> `resolve_blockage()`.
5.  **Save:**
    *   Agent: "Audit complete. Saving report..." -> `submit_artifact(type="Report", content=...)`.
6.  **Disconnect:** User runs `clock_out()`.

---

## 5. References

*   **Governance:** `000-LIVING-ORCHESTRA-D1-NORTH-STAR.md` (The 7 Immutables)
*   **System Vision:** `HESTAI-SYSTEM-OVERVIEW.md` (The "Why" and "How")
*   **Current State:** `CURRENT-WORKING-STATE.md` (The baseline)
*   **Protocols:** `BLOCKAGE_RESOLUTION_PROTOCOL.oct.md` (The debate mechanism)
*   **Legacy Reports:** `800-REPORT-CRITICAL-ENGINEER...`, `803-REPORT-ISSUE-120...` (Context history)
