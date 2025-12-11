# Web Agent Protocol v1.0

> **Status:** RATIFIED
> **Decision Authority:** holistic-orchestrator
> **Issue Reference:** #120 - Unified .hestai Architecture
> **Effective Date:** 2025-12-11

## Purpose

This protocol enables **web-based AI agents** (Claude Code Web, Codex Web, GitHub Copilot Workspace) to participate in HestAI-governed projects despite lacking access to:
- Local `~/.hestai/` session storage
- MCP server tools (`clock_in`, `clock_out`, `context_update`)

## Core Principle

**THE REPOSITORY IS THE SINGLE SOURCE OF TRUTH.**

If context is not in the Git repository, it does not exist for the team.

---

## 1. Context Authority Model

### 1.1 Reading Context (Before Work)

Web agents MUST read project context before starting work:

```
[project]/.hestai/context/PROJECT-CONTEXT.md
```

This file contains:
- Current phase and focus
- Active constraints and decisions
- Recent session summaries
- Known blockers

### 1.2 Updating Context (After Work)

Web agents SHOULD update `PROJECT-CONTEXT.md` directly when making significant changes:

1. **Pull latest** before editing (prevent conflicts)
2. **Append** to relevant sections (don't overwrite)
3. **Commit** context update with code changes
4. **PR review** catches any breakage

**Trust Model:** Web agents are trusted contributors. Context errors are fixed in code review, not prevented by tooling.

---

## 2. Session Contribution Protocol

Since web agents cannot use `clock_in`/`clock_out`, they use the **Inbox Transport Layer**.

### 2.1 Inbox Structure

```
project/.hestai/inbox/
├── pending/           # Write your session notes here
│   └── remote-*.md    # Naming convention below
└── processed/         # System moves files here after ingestion
```

### 2.2 Session Note Format

Create a file in `pending/` with this naming convention:

```
remote-{YYYY-MM-DD}-{PLATFORM}-{BRIEF_TOPIC}.md
```

**Examples:**
- `remote-2025-12-11-claude-web-auth-refactor.md`
- `remote-2025-12-11-copilot-api-endpoints.md`

**File Content Template:**

```markdown
---
source: {web-claude|copilot-workspace|codex-web}
session_type: async-remote
timestamp: {ISO 8601}
author: {username or "anonymous"}
---

## Summary

[2-3 sentences: What was accomplished]

## Changes Made

- [File/component]: [What changed]
- [File/component]: [What changed]

## Decisions

- [Any architectural or design decisions made]

## Context Updates

- [What was added/modified in PROJECT-CONTEXT.md, if any]

## Notes for Next Agent

[Any handoff information, warnings, or TODOs]
```

### 2.3 Commit Message Format

Include HestAI metadata in commit trailers for traceability:

```
feat(auth): implement OAuth2 flow for web login

- Added OAuth2 provider configuration
- Created callback handler
- Updated user session model

[HESTAI-META]
Source: web-claude
Session-Type: async-remote
Context-Update: true
Artifact-Ref: .hestai/inbox/pending/remote-2025-12-11-claude-web-auth.md
```

---

## 3. Ingestion Protocol (Local Agents)

When a local agent runs `clock_in`, the system performs **Inbox Sweeping**:

1. **Detect** files in `project/.hestai/inbox/pending/`
2. **Parse** metadata and content
3. **Archive** to `~/.hestai/projects/{slug}/sessions/archive/`
4. **Move** processed file to `inbox/processed/` (or delete)
5. **Update** local history index

**Timing:** Pull-on-local-activity (eventual consistency accepted).

---

## 4. Fidelity Expectations

| Agent Type | Context Fidelity | Session History | Recommended Use |
|------------|------------------|-----------------|-----------------|
| Local (MCP) | 100% | Full archive | Strategic orchestration, complex features |
| Web (Inbox) | ~80% | Summary only | Tactical fixes, isolated features, reviews |

**Accepted Trade-offs:**
- Web agents lack real-time session streaming
- Web agents cannot query `~/.hestai` history
- Web agents rely on repo-committed context only

**If full context is required:** Switch to local environment or read full documentation in repository.

---

## 5. Conflict Resolution

### 5.1 Context File Conflicts

If `PROJECT-CONTEXT.md` has merge conflicts:

1. **Prefer newer information** (later timestamps)
2. **Preserve all decisions** (append, don't replace)
3. **Flag uncertainty** with `[NEEDS REVIEW]` markers
4. **Request human review** in PR if ambiguous

### 5.2 Inbox Conflicts

Inbox files should never conflict (unique timestamps + platforms in filenames).

If conflicts occur: Keep both files, let local ingestion deduplicate.

---

## 6. Anti-Patterns

**DO NOT:**
- Assume local `~/.hestai` exists or is readable
- Call MCP tools (`clock_in`, `context_update`) from web environment
- Create separate "web-only" context files (one source of truth)
- Skip reading `PROJECT-CONTEXT.md` before work
- Overwrite context sections (append instead)

**DO:**
- Always pull latest before editing context
- Write session notes to inbox for history continuity
- Include `[HESTAI-META]` trailers in commits
- Trust the PR review process to catch errors

---

## 7. Quick Reference

### Starting Work (Web Agent)

```bash
# 1. Read context
cat project/.hestai/context/PROJECT-CONTEXT.md

# 2. Do your work
# ...

# 3. Update context (if significant changes)
# Edit PROJECT-CONTEXT.md, append to relevant sections

# 4. Write session note
# Create .hestai/inbox/pending/remote-YYYY-MM-DD-platform-topic.md

# 5. Commit with metadata
git add .
git commit  # Include [HESTAI-META] block
git push
```

### Minimum Viable Contribution

If you're making a quick fix and don't want full ceremony:

1. Read `PROJECT-CONTEXT.md` (always)
2. Make your change
3. Commit with basic `[HESTAI-META]` trailer
4. Skip inbox note (acceptable for trivial changes)

---

## Appendix A: Rationale

**Why Repo-Authoritative?**
- Distributed teams cannot rely on "local truth"
- Git provides audit trail and conflict resolution
- PR review is the quality gate

**Why Pull-on-Activity Ingestion?**
- Avoids CI complexity
- Accepts eventual consistency for session history
- Inbox is a holding pen, not real-time sync

**Why Accept 80% Fidelity?**
- Web agents are tactical, not strategic
- Maintenance cost of sync mechanisms exceeds value
- Users can switch to local for full capability

---

## Appendix B: Implementation Checklist

- [ ] Update `clock_in` tool to sweep `inbox/pending/`
- [ ] Add `.hestai/sessions/` to `.gitignore`
- [ ] Ensure `.hestai/context/` and `.hestai/inbox/` are tracked
- [ ] Document in project README or CONTRIBUTING.md
- [ ] Create PR template with `[HESTAI-META]` reminder

---

*Protocol authored by ho-liaison, ratified by holistic-orchestrator.*
