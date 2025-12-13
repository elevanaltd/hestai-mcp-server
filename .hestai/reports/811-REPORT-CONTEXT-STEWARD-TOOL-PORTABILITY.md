# REPORT: Context Steward Tool Portability (clockin/clockout/documentsubmit/contextupdate)

Date: 2025-12-13

## Scope
Assess how well these tools would “survive” if rebuilt in a new MCP server, focusing on architecture coupling and rewrite effort:
- `tools/clockin.py`
- `tools/clockout.py`
- `tools/documentsubmit.py`
- `tools/contextupdate.py`

This report is based on static code inspection of the above files and their direct imports.

## Executive Summary
These tools are **not strongly coupled to the model/provider orchestration layer** (they all run as “utility” tools and largely do filesystem work), but they are **strongly coupled to the Context Steward subsystem**:
- The **`.hestai/` filesystem contract** (sessions, context files, inbox, changelog/history) is foundational.
- `clockout` and `contextupdate` are additionally coupled to **AI delegation via `ContextStewardAI`** (config + clink + external CLI + OCTAVE parsing) and to each other (`clockout` calls `ContextUpdateTool` directly).

If a new MCP server preserves `.hestai` semantics and ports `tools/context_steward/*`, the tools are relatively portable. If the new server changes storage/workflow conventions (no `.hestai`, different transcript format, no delegated AI), `clockout`/`contextupdate` become substantial rewrites rather than straightforward ports.

## Portability Ratings (High = easy to port)
| Tool | Portability | Why |
|---|---:|---|
| `clockin` | High | Mostly creates/reads `.hestai` state + optional validators/registry |
| `documentsubmit` | Medium-High | Simple inbox + visibility routing + changelog; compression is TODO |
| `clockout` | Medium-Low | Transcript discovery/parsing + optional AI compression + context sync |
| `contextupdate` | Low | Core Context Steward workflow (inbox, changelog, conflict/compaction gates, AI merge contract) |

## Architectural Dependencies (What you must bring, or replace)

### Shared Tool Framework Coupling
All four tools are implemented as `BaseTool` subclasses and return `mcp.types.TextContent` containing a serialized `ToolOutput`:
- `tools/shared/base_tool.py` (tool interface and runtime glue)
- `tools/models.py` (`ToolOutput`, `ToolModelCategory`)

In a new server, you can either:
1) Port the minimal “tool wrapper” patterns (Pydantic request model + JSON response schema), or
2) Rewrap the same core logic into the new MCP SDK conventions and keep only the domain logic.

### Filesystem Contract Coupling (`.hestai`)
All four tools assume a specific project-local layout rooted at `working_dir`:
- `.hestai/context/` (e.g., `PROJECT-CONTEXT.md`, `PROJECT-CHECKLIST.md`, `PROJECT-ROADMAP.md`, `PROJECT-HISTORY.md`)
- `.hestai/sessions/active/<session_id>/session.json`
- `.hestai/sessions/archive/` (clockout writes raw JSONL and optionally `.oct.md` + verification JSON)
- `.hestai/inbox/{pending,processed}/` (submit/process audit trail)

This is the biggest portability lever: preserve it and porting is easy; change it and you’re rewriting.

### Global Registry Coupling (`~/.hestai`)
`clockin`/`clockout` optionally use:
- `tools/shared/global_registry.py` → `~/.hestai/sessions.registry.json`

This is portable, but it is an explicit cross-project assumption and may be undesirable in some deployments (multi-user servers, locked-down environments, ephemeral containers).

### Context Steward Subsystem Coupling
`documentsubmit` and `contextupdate` depend heavily on:
- `tools/context_steward/inbox.py` (submit/process/index)
- `tools/context_steward/visibility_rules.py` (routing destinations, formats)
- `tools/context_steward/utils.py` (changelog append helpers, filename sanitation)
- `tools/context_steward/changelog_parser.py` (conflict detection)
- `tools/context_steward/file_lookup.py` (finding context file placement)
- `tools/context_steward/schemas.py` (LOC/max constraints)

### AI Delegation Coupling (Optional but substantial)
`contextupdate` and `clockout` use:
- `tools/context_steward/ai.py` → reads `conf/context_steward.json`, delegates to `tools/clink.py` / external CLI, parses OCTAVE responses

If you want the same AI merge/compression behaviors in a new server, plan to port this entire delegation path (and its configuration + external runtime expectations).

## Tool-by-Tool Notes

### `tools/clockin.py`
Primary responsibilities:
- Select project root from `_session_context.project_root` or `working_dir`.
- Ensure `.hestai/{sessions/active,context}` directories exist (resolves `.hestai` symlink).
- Create `sessions/active/<session_id>/session.json`.
- Detect focus conflicts by scanning existing active sessions.
- Optionally include validated `current_state.oct` and `CONTEXT-NEGATIVES.oct`.
- Trigger periodic cleanup of old archives and stale sessions.
- Optionally register session in `~/.hestai/sessions.registry.json`.

Porting effort:
- Easy if `.hestai` layout is preserved.
- Optional pieces are easy to drop:
  - State vector/context negatives validation (can be removed or replaced).
  - Global registry.
  - Cleanup policy.

Risk areas in a new server:
- If the new server runs in a restricted FS environment, global home-dir registry and symlink resolution may be undesirable.

### `tools/clockout.py`
Primary responsibilities:
- Resolve project root from `_session_context`, global registry, or fallbacks.
- Find the session transcript JSONL via layered resolution:
  - Hook-provided transcript path from `clockin` metadata
  - Temporal beacon scanning
  - Metadata inversion via project config
  - `CLAUDE_TRANSCRIPT_DIR` escape hatch
  - Legacy fallback path encoding
- Copy raw JSONL to `.hestai/sessions/archive/` (explicitly preserved).
- Parse JSONL into messages, build summary.
- Optional AI compression to OCTAVE (`ContextStewardAI`), write `.oct.md`, generate verification JSON, optionally sync extracted context into `PROJECT-CONTEXT` by calling `ContextUpdateTool`.
- Remove active session dir; remove from global registry.

Porting effort:
- Moderate if you keep the same “Claude JSONL transcript” assumption and `.hestai` session layout.
- High if transcript format differs (or if you want a generic cross-client transcript pipeline).
- Very high if you want to keep AI compression + verification + context sync without porting the Context Steward AI subsystem.

Key coupling to note:
- `clockout` is not just “archive the session”; it is also a coordinator that can write to context state by directly invoking `ContextUpdateTool`.

### `tools/documentsubmit.py`
Primary responsibilities:
- Accept inline content or `file_ref`.
- Submit to inbox (`.hestai/inbox/pending/<uuid>.json`) for audit trail.
- Route destination based on `DOCUMENT_TYPES` and write a `.md` (or `.oct.md`) file into the destination.
- Move inbox item to processed and update processed index.
- Append changelog entry.

Porting effort:
- Straightforward if `.hestai/inbox` + visibility rules exist.
- Currently has a TODO for OCTAVE compression; if your new server expects actual compression, you’ll need to implement it or delegate it (similar to `ContextStewardAI`).

### `tools/contextupdate.py`
Primary responsibilities:
- Accept update content inline or by `file_ref`.
- Find/create target context file (via `find_context_file` and default to `.hestai/context/<TARGET>.md`).
- Submit update to inbox for audit trail.
- Read current content + changelog; detect conflicts (including “recent conflicts” heuristics).
- Optionally merge via `ContextStewardAI.run_task()` (returns artifacts; enforces a compaction gate).
- Enforce max LOC by archiving old sections into `PROJECT-HISTORY.md` (compaction).
- Write updated context, append changelog, process inbox item.

Porting effort:
- This is the most architecture-bound tool in the set.
- It is portable mainly by extracting `tools/context_steward/*` as a library and keeping the `.hestai` + changelog conventions.
- Rewriting from scratch is non-trivial because it encodes workflow rules (audit trail, conflict semantics, compaction gate, schema constraints, AI artifact contract).

## Recommendations for a New MCP Server

### Fastest / Lowest-Risk Migration (“Port the subsystem”)
If the goal is functional parity:
- Preserve the `.hestai/` filesystem contract.
- Port these modules wholesale:
  - `tools/context_steward/*`
  - `tools/shared/global_registry.py` (optional)
  - Minimal `ToolOutput` schema contract (or adapt to the new server’s response format)
- Rewrap tool entrypoints into the new server’s MCP framework, keeping domain logic intact.

### Cleaner Long-Term Architecture (“Split domain logic from MCP glue”)
If you want reusability across MCP servers:
- Extract a pure-python library layer (no `BaseTool`, no `mcp.types`):
  - `context_steward.sessions` (clockin/clockout domain logic)
  - `context_steward.inbox` (already close)
  - `context_steward.context_update` (conflict + compaction + IO)
  - `context_steward.ai_delegate` (optional plugin)
- Make transcript parsing and discovery pluggable (client-specific adapters).
- Keep “context sync from clockout” as an integration hook, not a hard import/call of `ContextUpdateTool`.

### If You Intend to Rewrite (Expectations)
To reproduce current behavior you’ll need to re-spec (and then implement):
- The `.hestai` directory semantics and file naming conventions.
- Inbox audit trail + processed index format.
- Changelog format + conflict detection heuristics.
- Compaction/archival rules (`PROJECT-HISTORY.md`) and the “compaction enforcement” gate.
- AI task contract (what `ContextStewardAI` returns: `summary`, `artifacts`, `compaction_performed`) and downstream validation.
- Transcript discovery + security checks (path containment, DoS limits).

## Minimal “Survival Set” (If you only want basics)
If the new server only needs session lifecycle without AI and without context merging:
- Keep `clockin` (filesystem session tracking).
- In `clockout`, keep only: locate transcript path (or accept as input) + copy raw JSONL to archive + delete active session.
- Drop: AI compression, OCTAVE parsing, verification, and `ContextUpdateTool` sync.
