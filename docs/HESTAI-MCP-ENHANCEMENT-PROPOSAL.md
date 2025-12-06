# HestAI-MCP Server Enhancement Proposal

## Strategic Vision: From Tool Collection to Agent Operating System

**Document Version:** 1.0
**Date:** 2025-12-06
**Status:** Proposal for Review
**Related Repositories:**
- `elevanaltd/hestai-mcp-server` (this repo)
- `elevanaltd/hestai` (workflow definitions, .claude folder)
- `elevanaltd/hestai-orchestrator` (archived - Odyssean Anchor research)
- `elevanaltd/hestai-research` (research findings)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [GitHub Issues Relevance Analysis](#3-github-issues-relevance-analysis)
4. [Enhancement Proposals](#4-enhancement-proposals)
   - 4.1 [Episodic Memory System](#41-episodic-memory-system)
   - 4.2 [System Steward as Context Curator](#42-system-steward-as-context-curator)
   - 4.3 [Odyssean Anchor Integration](#43-odyssean-anchor-integration)
   - 4.4 [Enhanced /load Command via MCP](#44-enhanced-load-command-via-mcp)
   - 4.5 [North Star Summary Integration](#45-north-star-summary-integration)
   - 4.6 [Repomix Skill Activation](#46-repomix-skill-activation)
   - 4.7 [Multi-Tier Agent Strategy](#47-multi-tier-agent-strategy)
   - 4.8 [Persistent Storage Options](#48-persistent-storage-options)
5. [Architecture Vision](#5-architecture-vision)
6. [Implementation Roadmap](#6-implementation-roadmap)
7. [Technical Specifications](#7-technical-specifications)
8. [Risks and Considerations](#8-risks-and-considerations)
9. [Comparison: Current vs Proposed Workflow](#9-comparison-current-vs-proposed-workflow)
10. [Appendices](#10-appendices)

---

## 1. Executive Summary

### The Core Question

Can HestAI-MCP-Server evolve from a collection of tools that Claude Code invokes into a comprehensive **Agent Operating System** that orchestrates the entire HestAI workflow?

### Key Findings

1. **Yes, this is architecturally feasible** - The current infrastructure (conversation_memory, clink, registry) provides a foundation that can be extended.

2. **The leap is significant but achievable in phases** - Building everything at once is unrealistic, but incremental value delivery is possible.

3. **The genius insight**: The MCP server can become an Agent OS where:
   - Holistic Orchestrator (HO) acts as the shell
   - Agents are processes with persistent identity (Odyssean Anchors)
   - System Steward is the memory kernel
   - conversation_memory + episodic_memory provide the unified memory subsystem

4. **Immediate opportunities exist** - Session summarization, anchor management, and context curation can be implemented now with zero infrastructure risk.

### Recommended Approach

A phased implementation starting with **Episodic Memory** (secretary notes at session end) and **Odyssean Anchors** (agent identity persistence), building toward **System Steward as Context Curator** and eventually **Persistent Storage**.

---

## 2. Current State Analysis

### 2.1 HestAI-MCP-Server Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Claude Code CLI                                               │
│       │                                                        │
│       ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              HestAI-MCP-Server                          │  │
│  │                                                         │  │
│  │  Tools:                                                 │  │
│  │  ├── chat          (general conversation)               │  │
│  │  ├── thinkdeep     (extended reasoning)                 │  │
│  │  ├── consensus     (multi-model agreement)              │  │
│  │  ├── codereview    (code analysis)                      │  │
│  │  ├── debug         (debugging assistance)               │  │
│  │  ├── planner       (task decomposition)                 │  │
│  │  ├── clink         (CLI delegation)                     │  │
│  │  ├── registry      (approval workflows)                 │  │
│  │  ├── testguard     (test enforcement)                   │  │
│  │  ├── critical_engineer (architecture validation)        │  │
│  │  └── ...                                                │  │
│  │                                                         │  │
│  │  Utils:                                                 │  │
│  │  ├── conversation_memory.py  (thread persistence)       │  │
│  │  ├── storage_backend.py      (in-memory storage)        │  │
│  │  └── model_context.py        (token allocation)         │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│       │                                                        │
│       ▼                                                        │
│  External Providers: Gemini, OpenAI, X.AI, DIAL, OpenRouter   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Conversation Memory System

**Location:** `utils/conversation_memory.py`

**Capabilities:**
- UUID-based thread identification
- Cross-tool continuation via `continuation_id`
- Newest-first file prioritization
- Dual prioritization strategy (collection vs presentation)
- Configurable TTL (3-24 hours)
- 50-turn maximum per thread

**Limitations:**
- In-memory only (lost on server restart)
- No cross-session persistence
- No pattern detection
- No summarization/compression

### 2.3 Storage Backend

**Location:** `utils/storage_backend.py`

**Current Implementation:**
```python
class InMemoryStorage:
    """
    Thread-safe in-memory storage with TTL support.

    Interface compatible with Redis:
    - setex(key, ttl, value)
    - get(key)

    Limitation: Process-specific, lost on restart.
    """
```

**Historical Note:** Redis support existed in Docker deployment but was removed for simplicity. The abstraction layer remains compatible.

### 2.4 The .claude Folder Structure (from elevanaltd/hestai)

```
.claude/
├── agents/              # Agent constitutions (.oct.md files)
├── commands/            # 23 slash commands
│   ├── load.md          # Session initialization
│   ├── BUILD.md         # Build operations
│   ├── fix.md           # Fix workflows
│   └── ...
├── hooks/               # Enforcement and automation
│   ├── skill-activation-prompt.ts  # AI-powered skill selection
│   ├── SessionStart.ts             # Session initialization
│   ├── enforce-*.sh                # Various enforcement hooks
│   └── ...
├── skills/              # 23+ skill directories
│   ├── holistic-orchestrator-mode/
│   ├── code-extraction/
│   └── ...
└── settings.json        # Hook routing configuration
```

### 2.5 The /load Command (Current Implementation)

**12-Step Sequence:**
1. Parse arguments
2. Read constitution (PRIMACY)
3. Micro-RAPH anchor (LOCK)
4. Load PROJECT-CONTEXT
5. Load CHECKLIST + NORTH-STAR
6. Load Git state
7. Pack codebase (repomix) - ~15k tokens
8. READ phase
9. ABSORB phase
10. PERCEIVE phase
11. HARMONISE phase
12. Dashboard synthesis

**Token Cost:** ~30k+ tokens for full load

**Problem:** Loads everything regardless of task, overwhelming agent context.

---

## 3. GitHub Issues Relevance Analysis

Analysis of issues #1-11 from `elevanaltd/hestai`:

| Issue | Title | Priority | MCP Relevance | Implementation Path |
|-------|-------|----------|---------------|---------------------|
| **#1** | Episodic Memory: System Steward with .coord/system-memory/ | P1 | ⭐⭐⭐⭐⭐ **Critical** | Perfect fit - implement as MCP tool |
| **#2** | Role Compliance: enforce-role-boundaries.sh Advisory Mode | P1 | ⭐⭐⭐ Moderate | Could be MCP pre-tool validation |
| **#3** | Session Context: WHY synthesis in /load | P2 | ⭐⭐⭐⭐ High | Implement as session_context tool |
| **#4** | Blockage Resolution Protocol | P1 | ⭐⭐⭐⭐⭐ **Critical** | Extends existing registry tool |
| **#5** | MUST_NEVER Monitoring Research | P4 | ⭐⭐ Low | Post-response difficult in MCP |
| **#6** | MCP Tool Audit (30k tokens) | P1 | ⭐⭐⭐⭐ High | Self-optimization opportunity |
| **#7** | North Star Loading Strategy | P1 | ⭐⭐⭐⭐⭐ **Critical** | Compression over lazy-load |
| **#8** | Repomix Audit (15k tokens) | P1 | ⭐⭐⭐⭐ High | Skill-activated on-demand |
| **#9** | System Tool Audit | - | ⭐ Platform | Anthropic-side, not addressable |
| **#10** | RAPH Audit | P2 | ⭐⭐⭐⭐ High | Micro-RAPH via anchors |
| **#11** | Worktree Boundary Enforcement | Med | ⭐⭐⭐ Moderate | MCP pre-tool validation |

### Key Takeaways

1. **Issues #1, #4, #7 are foundational** - They define the memory, resolution, and context loading architecture.

2. **Issues #6, #8, #10 are optimization** - Reducing token overhead once foundation is solid.

3. **Issue #3 depends on #1** - WHY synthesis needs episodic memory.

4. **Issue #4 (Blockage Resolution) is partially implemented** - Registry tool exists, needs enhancement.

---

## 4. Enhancement Proposals

### 4.1 Episodic Memory System

#### Concept

Transform session-end moments into persistent memory through "secretary notes" - OCTAVE-compressed summaries of what happened, decisions made, and continuation points.

#### Architecture

```
.coord/system-memory/
├── episodes/
│   ├── 2025-12-06.md    # Daily episode files
│   ├── 2025-12-07.md
│   └── ...
├── patterns.md          # OCTAVE-compressed recurring patterns
└── anchors/
    ├── implementation-lead.anchor.md
    ├── critical-engineer.anchor.md
    └── ...
```

#### OCTAVE Episode Format

```markdown
## Session: a1b2c3d4
**Date:** 2025-12-06 14:32 | **Duration:** 47 min | **Turns:** 12
**Primary Tool:** codereview | **Agent:** implementation-lead

### OUTCOMES
- Implemented FK constraint fix for user_projects table
- Added migration script 20251206_fix_fk.sql
- Tests passing after retry

### DECISIONS
- Chose CASCADE over SET NULL for FK behavior
- Deferred index optimization to separate PR

### FILES TOUCHED
- `src/db/migrations/20251206_fix_fk.sql`
- `src/models/user_project.py`
- `tests/test_user_project.py`

### PATTERNS NOTED
- Third FK constraint issue this week (see 12/04, 12/05)
- testguard blocked initial attempt (missing rollback test)

### CONTINUATION POINTS
- Index optimization PR still needed
- Performance testing pending

### KEY LEARNINGS
- FK migrations require explicit rollback tests
- CASCADE behavior needs documentation in schema

---
```

#### Implementation

**New Tool:** `session_summary`

```python
class SessionSummaryTool(SimpleTool):
    """
    Summarize and persist session context as episodic memory.

    Invocation:
    - End of session: HO invokes to capture session learnings
    - Mid-session checkpoint: Capture progress on long sessions
    - Pattern detection: System Steward queries for recurring issues

    Actions:
    - summarize: Generate OCTAVE summary from thread
    - summarize_and_persist: Generate and save to disk
    - get_recent: Retrieve recent episodes for context loading
    """
```

**Input Schema:**
```json
{
  "thread_id": "UUID of conversation thread",
  "agent_role": "implementation-lead | critical-engineer | ...",
  "action": "summarize | summarize_and_persist | get_recent",
  "days_back": 3
}
```

#### Trigger Points

1. **Explicit invocation** - HO calls at session end
2. **Thread TTL expiry** - Auto-summarize before expiration (future)
3. **Turn threshold** - Summarize every N turns for long sessions (future)

---

### 4.2 System Steward as Context Curator

#### Concept

Instead of loading everything at session start, System Steward analyzes the task and provides **curated context** - only what's needed for the specific work.

#### Current Problem

```
/load ho → Loads EVERYTHING:
- Full constitution (~500 tokens)
- PROJECT-CONTEXT (~1000 tokens)
- North Star (~3000 tokens)
- Repomix codebase (~15000 tokens)
- Full RAPH (~2000 tokens)
- Git state (~200 tokens)
────────────────────────────────
Total: ~21,700+ tokens before work begins
```

#### Proposed Solution

```
/load ho [task: "implement FK constraint fix"]
    │
    ▼
System Steward analyzes:
    • What does this task need? → FK, migrations, tests
    • What's in episodic memory? → 2 similar issues this week
    • What files are relevant? → db/migrations/, models/
    • Roadmap context? → Part of "Database Integrity" milestone
    │
    ▼
Returns CURATED context (~3000 tokens):
    • Micro-RAPH anchor (50 tokens)
    • Task-specific episodes (200 tokens)
    • Relevant file list (100 tokens)
    • Continuation points (50 tokens)
    • Minimal git state (50 tokens)
```

#### Implementation

**New Tool:** `session_context`

```python
class SessionContextTool(SimpleTool):
    """
    System Steward's context loading interface.

    Features:
    - Task-aware context curation
    - Roadmap integration for "next task" detection
    - Episodic memory queries
    - Anchor loading
    - Minimal git state
    """

    async def execute(self, arguments: dict) -> list[TextContent]:
        task = arguments.get("task")
        role = arguments.get("role", "holistic-orchestrator")
        roadmap_path = arguments.get("roadmap")
        mode = arguments.get("mode", "curated")  # curated | full | minimal

        if not task and roadmap_path:
            task = await self._get_next_task_from_roadmap(roadmap_path)

        if mode == "curated":
            return await self._curated_context(task, role)
        elif mode == "full":
            return await self._full_context(role)
        else:
            return await self._minimal_context(role)
```

**Input Schema:**
```json
{
  "task": "Optional task description or identifier",
  "role": "holistic-orchestrator",
  "roadmap": ".coord/PROJECT-ROADMAP.md",
  "mode": "curated | full | minimal"
}
```

---

### 4.3 Odyssean Anchor Integration

#### Concept

Based on the SHANK-ARM-FLUKE architecture from `hestai-research`, Odyssean Anchors provide **identity persistence** across sessions - the ~150 tokens that bind an agent to remember who they are.

#### The Leonard Shelby Analogy

Like the protagonist in Memento who tattoos essential truths on his body, agents need permanent "tattoos" that survive context resets:

- **SHANK** (Who I Am - Immutable): Core identity, purpose, constraints
- **ARM** (Current Phase): What phase of work, behavioral mode
- **FLUKE** (Active Capabilities): Skills loaded, deference relationships

#### Anchor Structure

```markdown
# Odyssean Anchor: Implementation Lead

## SHANK (Immutable Identity) ~50 tokens
I am Implementation Lead. My core purpose is delivery through code.
I serve project goals while respecting quality gates.
I do not debate constraints - I implement solutions.
I defer to critical-engineer for architecture, testguard for quality.

## ARM (Phase Context) ~50 tokens
ACTUAL phase: Build execution.
Focus on implementation, not conceptualization.
Bias toward action within validated constraints.

## FLUKE (Active Capabilities) ~50 tokens
Current skills: BUILD, CREATIVE_CODING, DEBUG, REFACTOR
Deference chain: testguard → critical-engineer → principal-engineer
Escalation after: 2 failed validation cycles

---
LAST UPDATED: 2025-12-06T14:32:00Z
TRIGGER: Update when core constraints change
```

#### Implementation

**New Tool:** `anchor`

```python
class AnchorTool(SimpleTool):
    """
    Odyssean Anchor management - identity persistence across sessions.

    Actions:
    - load: Load anchor for role (returns anchor content)
    - create: Create anchor by analyzing constitution
    - update: Update specific anchor component
    - verify: Check anchor alignment with constitution
    """

    async def execute(self, arguments: dict) -> list[TextContent]:
        action = arguments.get("action", "load")
        role = arguments.get("role")

        if action == "load":
            return await self._load_anchor(role)
        elif action == "create":
            return await self._create_anchor_from_constitution(role)
        elif action == "update":
            component = arguments.get("component")  # shank | arm | fluke
            content = arguments.get("content")
            return await self._update_anchor(role, component, content)
        elif action == "verify":
            return await self._verify_anchor_alignment(role)
```

**Anchor Creation Process:**

```python
async def _create_anchor_from_constitution(self, role: str) -> list[TextContent]:
    """
    Use AI to extract SHANK-ARM-FLUKE from full constitution.
    """
    constitution_path = f".claude/agents/{role}.oct.md"
    constitution = Path(constitution_path).read_text()

    extraction_prompt = f"""
    Analyze this agent constitution and extract:

    SHANK (50 tokens max): The immutable core identity.
    What never changes about who this agent IS.

    ARM (50 tokens max): Current phase context.
    What phase of work and what that means for behavior.

    FLUKE (50 tokens max): Active capabilities and deference.
    What skills are loaded and who to defer to.

    Constitution:
    {constitution}

    Output exactly:
    SHANK: [content]
    ARM: [content]
    FLUKE: [content]
    """

    # Use fast model for extraction
    result = await self._call_model(extraction_prompt, model="gemini-2.5-flash")

    # Parse and save anchor
    anchor = self._parse_anchor_response(result)
    await self._save_anchor(role, anchor)

    return [TextContent(type="text", text=f"Anchor created for {role}")]
```

---

### 4.4 Enhanced /load Command via MCP

#### Concept

Replace the 12-step /load command with an MCP tool that provides equivalent functionality with better token efficiency.

#### Mapping /load Steps to MCP

| /load Step | MCP Equivalent |
|------------|----------------|
| 1. Parse arguments | Tool input schema |
| 2. Read constitution | `anchor` tool (load) |
| 3. Micro-RAPH anchor | `anchor` tool (SHANK) |
| 4. Load PROJECT-CONTEXT | `session_context` tool |
| 5. Load NORTH-STAR | `north_star` tool |
| 6. Load Git state | `session_context` (git_state) |
| 7. Pack codebase | `repomix_skill` (on-demand) |
| 8-11. RAPH phases | Anchor already captures essence |
| 12. Dashboard | `session_context` output format |

#### Implementation

The `session_context` tool (Section 4.2) effectively replaces /load with these advantages:

1. **Task-aware loading** - Only loads what's needed
2. **Anchor-based identity** - 150 tokens instead of 500+ constitution
3. **Episodic integration** - Relevant history, not everything
4. **On-demand repomix** - Only when architecture questions arise

---

### 4.5 North Star Summary Integration

#### Concept

Issue #7 recommends **compression over lazy-loading** due to escalation protocol latency requirements. Implement OCTAVE compression for North Star documents.

#### Implementation

**New Tool:** `north_star`

```python
class NorthStarTool(SimpleTool):
    """
    Provides North Star context with OCTAVE compression.

    Reduces 3k tokens → ~800 tokens while preserving
    escalation-critical information.

    Actions:
    - summary: Compressed summary for session start
    - full: Complete North Star when validation triggers
    - escalation: Fast path for escalation protocols (<50ms)
    """

    async def execute(self, arguments: dict) -> list[TextContent]:
        action = arguments.get("action", "summary")

        if action == "summary":
            return await self._get_compressed_summary()
        elif action == "full":
            return await self._get_full_north_star()
        elif action == "escalation":
            return await self._get_escalation_context()
```

**Compression Strategy:**

```python
async def _get_compressed_summary(self) -> list[TextContent]:
    """Apply OCTAVE compression to North Star."""
    north_star = self._load_north_star()

    compression_prompt = f"""
    Compress this North Star document to ~800 tokens using OCTAVE format.

    PRESERVE:
    - Escalation triggers and thresholds
    - Key constraints and boundaries
    - Decision authority matrix
    - Critical success criteria

    REMOVE:
    - Verbose explanations
    - Examples (keep only references)
    - Historical context
    - Redundant phrasings

    Document:
    {north_star}
    """

    compressed = await self._call_model(compression_prompt)
    return [TextContent(type="text", text=compressed)]
```

---

### 4.6 Repomix Skill Activation

#### Concept

Convert eager-loaded repomix (~15k tokens per session) to skill-activated on-demand.

#### Current Problem

```
/load ho → Always runs mcp__repomix__pack_codebase
         → 638 files processed
         → ~15,000 tokens consumed
         → Even for tasks that don't need codebase context
```

#### Proposed Solution

**Skill Trigger Patterns:**
- "architecture"
- "codebase structure"
- "where is"
- "how does the system"
- "module dependencies"
- "file organization"

**Implementation:**

```python
class RepomixSkillTool(SimpleTool):
    """
    Skill-activated repomix - only invoked when codebase context is needed.

    Activation:
    - Explicit invocation
    - Skill trigger detection in session_context
    - HO requests architectural overview
    """

    TRIGGER_PATTERNS = [
        r"architecture",
        r"codebase structure",
        r"where is .+ (located|defined|implemented)",
        r"how does the system",
        r"module dependencies",
        r"file organization",
        r"project structure",
    ]

    async def should_activate(self, prompt: str) -> bool:
        """Detect if prompt suggests need for codebase context."""
        prompt_lower = prompt.lower()
        return any(re.search(pattern, prompt_lower) for pattern in self.TRIGGER_PATTERNS)

    async def execute(self, arguments: dict) -> list[TextContent]:
        scope = arguments.get("scope", "full")  # full | directory | metadata
        directory = arguments.get("directory")

        if scope == "metadata":
            # Return only file list and structure, no content
            return await self._get_codebase_metadata()
        elif scope == "directory" and directory:
            # Pack specific directory only
            return await self._pack_directory(directory)
        else:
            # Full codebase pack
            return await self._pack_full_codebase()
```

**Token Savings:**
- Current: 15k tokens every session
- Proposed: 15k tokens only when needed (~30% of sessions)
- **Estimated savings: ~10.5k tokens average per session**

---

### 4.7 Multi-Tier Agent Strategy

#### Concept

Route tasks to appropriate agent tiers based on complexity:

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| **Opus** | Claude Opus | Complex architecture, security-critical | High |
| **Sonnet** | Claude Sonnet | Standard implementation, refactoring | Medium |
| **Flash** | Gemini Flash | Quick reviews, formatting, simple fixes | Low |
| **Haiku** | Claude Haiku | Trivial changes, comments, renames | Minimal |

#### Implementation via Enhanced clink

```json
// conf/cli_clients/claude.json
{
  "name": "claude",
  "command": "claude",
  "roles": {
    "implementation-lead": {
      "prompt_path": "systemprompts/clink/implementation-lead.txt",
      "additional_args": ["--model", "claude-sonnet-4"]
    },
    "senior-architect": {
      "prompt_path": "systemprompts/clink/senior-architect.txt",
      "additional_args": ["--model", "claude-opus-4"]
    },
    "junior-dev": {
      "prompt_path": "systemprompts/clink/junior-dev.txt",
      "additional_args": ["--model", "claude-haiku-3"]
    }
  }
}
```

**Task Router Tool:**

```python
class TaskRouterTool(SimpleTool):
    """
    Analyzes task complexity and recommends appropriate agent tier.

    HO uses this to determine which clink role to invoke.
    """

    COMPLEXITY_MARKERS = {
        "opus": [
            "architecture decision", "security critical", "novel algorithm",
            "multi-system integration", "breaking change", "schema migration"
        ],
        "sonnet": [
            "implement feature", "refactor", "add tests", "bug fix",
            "api endpoint", "database query"
        ],
        "flash": [
            "code review", "documentation", "formatting", "linting",
            "simple validation"
        ],
        "haiku": [
            "rename", "add comment", "trivial fix", "typo",
            "update version"
        ]
    }

    async def execute(self, arguments: dict) -> list[TextContent]:
        task = arguments.get("task")
        context = arguments.get("context", {})

        tier = await self._classify_task(task, context)

        return [TextContent(type="text", text=json.dumps({
            "recommended_tier": tier,
            "cli_name": "claude",
            "role": f"{tier}-developer",
            "reasoning": self._get_reasoning(task, tier)
        }))]
```

---

### 4.8 Persistent Storage Options

#### Current Limitation

```python
# utils/storage_backend.py
class InMemoryStorage:
    """
    ⚠️ Process-specific storage
    - Lost on MCP server restart
    - 3-24 hour TTL
    - No cross-session persistence
    """
```

#### Option A: File-Based Storage (Recommended)

```python
class FileBasedStorage:
    """
    Simple file-based persistence without external dependencies.

    Structure:
    ~/.hestai/storage/
    ├── threads/
    │   ├── thread_abc123.json
    │   └── thread_def456.json
    └── metadata.json
    """

    def __init__(self, base_path: str = "~/.hestai/storage"):
        self.base_path = Path(base_path).expanduser()
        self.threads_dir = self.base_path / "threads"
        self.threads_dir.mkdir(parents=True, exist_ok=True)

    def setex(self, key: str, ttl_seconds: int, value: str):
        file_path = self.threads_dir / f"{key}.json"
        data = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
            "created_at": time.time()
        }
        file_path.write_text(json.dumps(data))

    def get(self, key: str) -> Optional[str]:
        file_path = self.threads_dir / f"{key}.json"
        if not file_path.exists():
            return None

        data = json.loads(file_path.read_text())
        if time.time() > data["expires_at"]:
            file_path.unlink()
            return None

        return data["value"]
```

**Advantages:**
- Zero external dependencies
- Survives server restarts
- Same interface as current system
- Easy debugging (JSON files)

#### Option B: Redis Revival

The abstraction already exists. Enable via environment variable:

```env
# .env
REDIS_URL=redis://localhost:6379/0
```

```python
def get_storage_backend():
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return RedisStorage(redis_url)

    persistent_path = os.getenv("PERSISTENT_MEMORY_PATH")
    if persistent_path:
        return FileBasedStorage(persistent_path)

    return InMemoryStorage()
```

#### Option C: SQLite Storage

```python
class SQLiteStorage:
    """
    SQLite-based storage for robust persistence.

    Advantages:
    - ACID compliance
    - Query capabilities for pattern detection
    - Single file, no server needed
    """

    def __init__(self, db_path: str = "~/.hestai/storage.db"):
        self.db_path = Path(db_path).expanduser()
        self._init_schema()
```

#### Recommendation

**Phase 1:** Implement FileBasedStorage (simple, no dependencies)
**Phase 2:** Add SQLite option for pattern detection queries
**Phase 3:** Redis for multi-instance deployments (if needed)

---

## 5. Architecture Vision

### 5.1 Current vs Proposed Architecture

```
CURRENT ARCHITECTURE                    PROPOSED ARCHITECTURE
═══════════════════════                 ═══════════════════════

Claude Code CLI                         Claude Code CLI (HO Shell)
      │                                       │
      ▼                                       ▼
┌─────────────────┐                    ┌─────────────────────────────────────┐
│  HestAI-MCP     │                    │         HestAI Agent OS             │
│  (Tool Bag)     │                    │                                     │
│                 │                    │  ┌─────────────────────────────┐   │
│  • chat         │                    │  │     KERNEL (MCP Server)     │   │
│  • thinkdeep    │                    │  │  ┌─────────┐ ┌───────────┐ │   │
│  • codereview   │                    │  │  │ Memory  │ │ Identity  │ │   │
│  • clink        │                    │  │  │ Manager │ │ Manager   │ │   │
│  • etc.         │                    │  │  │(episodic)│ │ (anchors) │ │   │
│                 │                    │  │  └─────────┘ └───────────┘ │   │
└─────────────────┘                    │  │  ┌─────────┐ ┌───────────┐ │   │
      │                                │  │  │ Context │ │ Process   │ │   │
      ▼                                │  │  │ Curator │ │ Control   │ │   │
┌─────────────────┐                    │  │  │ (SS)    │ │ (clink)   │ │   │
│  External       │                    │  │  └─────────┘ └───────────┘ │   │
│  Providers      │                    │  └─────────────────────────────┘   │
│                 │                    │                                     │
│  • Gemini       │                    │  ┌─────────────────────────────┐   │
│  • OpenAI       │                    │  │     PROCESSES (Agents)      │   │
│  • X.AI         │                    │  │                             │   │
└─────────────────┘                    │  │  ┌───────┐ ┌───────┐       │   │
                                       │  │  │  IL   │ │  CE   │ ...   │   │
                                       │  │  │(Opus) │ │(Flash)│       │   │
                                       │  │  │       │ │       │       │   │
                                       │  │  │Anchor │ │Anchor │       │   │
                                       │  │  └───────┘ └───────┘       │   │
                                       │  └─────────────────────────────┘   │
                                       │                                     │
                                       │  ┌─────────────────────────────┐   │
                                       │  │     STORAGE (Persistent)    │   │
                                       │  │  • conversation_memory      │   │
                                       │  │  • episodic_memory          │   │
                                       │  │  • anchors                  │   │
                                       │  └─────────────────────────────┘   │
                                       └─────────────────────────────────────┘
```

### 5.2 Data Flow: Task Execution

```
1. USER INPUT
   │
   ▼
2. HO (Claude Code) receives task
   │
   ▼
3. session_context tool invoked
   │  • Task analysis
   │  • Roadmap lookup
   │  • Episodic memory query
   │  • Anchor loading
   │
   ▼
4. CURATED CONTEXT returned to HO
   │  • ~3000 tokens (vs 21000+)
   │  • Task-specific
   │  • With continuation points
   │
   ▼
5. HO decides delegation strategy
   │  • task_router suggests tier
   │  • HO invokes clink with role
   │
   ▼
6. clink executes via CLI agent
   │  • Anchor injected
   │  • Continuation ID for memory
   │  • Role-specific prompt
   │
   ▼
7. RESULT returned to HO
   │
   ▼
8. session_summary invoked (if session end)
   │  • OCTAVE compression
   │  • Persist to episodic memory
   │  • Update patterns if needed
```

### 5.3 System Steward: The Memory Kernel

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM STEWARD                           │
│              (Memory Kernel of Agent OS)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RESPONSIBILITIES:                                          │
│                                                             │
│  1. CONTEXT CURATION                                        │
│     • Analyze task requirements                             │
│     • Query episodic memory for relevance                   │
│     • Load only necessary context                           │
│     • Prevent agent overwhelm                               │
│                                                             │
│  2. MEMORY MANAGEMENT                                       │
│     • Record session episodes                               │
│     • Detect patterns across sessions                       │
│     • Compress and archive old episodes                     │
│     • Maintain anchor integrity                             │
│                                                             │
│  3. SESSION LIFECYCLE                                       │
│     • Initialize context at session start                   │
│     • Monitor tool executions (future)                      │
│     • Summarize at session end                              │
│     • Handle context revival                                │
│                                                             │
│  INTERFACES:                                                │
│                                                             │
│  • session_context tool (context loading)                   │
│  • session_summary tool (episode recording)                 │
│  • anchor tool (identity management)                        │
│  • north_star tool (strategic context)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Roadmap

### Phase 0: Foundation (Week 1)
*Zero risk, immediate value*

| Task | Effort | Deliverable |
|------|--------|-------------|
| Create `.coord/system-memory/` structure | 30 min | Directory scaffold |
| Implement `session_summary` tool | 2 days | OCTAVE episode recording |
| Implement `anchor` tool | 2 days | Identity persistence |
| Add OCTAVE compression utility | 1 day | Reusable compression |
| Extend default TTL to 24h | 5 min | Better persistence |
| Write tests | 1 day | Validation |

**Exit Criteria:**
- HO can invoke `session_summary` at session end
- Episodes persist to `.coord/system-memory/episodes/`
- Anchors can be created, loaded, and verified

### Phase 1: Context Curation (Week 2-3)
*System Steward intelligence*

| Task | Effort | Deliverable |
|------|--------|-------------|
| Implement `session_context` tool | 3 days | Task-aware loading |
| Add episodic memory queries | 2 days | Relevant history retrieval |
| Implement roadmap parsing | 1 day | "Next task" detection |
| Add `north_star` tool with compression | 2 days | Efficient strategic context |
| Integrate anchor loading | 1 day | Auto-load at context request |
| Write tests | 2 days | Validation |

**Exit Criteria:**
- `session_context` provides curated context based on task
- Token usage reduced by ~60% compared to full /load
- Episodic memory influences context selection

### Phase 2: Persistence & Optimization (Week 4-5)
*Durability and efficiency*

| Task | Effort | Deliverable |
|------|--------|-------------|
| Implement `FileBasedStorage` | 2 days | Survive restarts |
| Add storage selection via env var | 1 day | Flexible deployment |
| Implement `repomix_skill` | 2 days | On-demand codebase pack |
| Add pattern detection | 3 days | Cross-session learning |
| Implement `task_router` | 2 days | Multi-tier recommendations |
| Write tests | 2 days | Validation |

**Exit Criteria:**
- Conversations persist across server restarts
- Repomix only invoked when needed
- Pattern detection flags recurring issues
- Task routing provides tier recommendations

### Phase 3: Integration & Polish (Week 6+)
*Unified experience*

| Task | Effort | Deliverable |
|------|--------|-------------|
| Enhance clink with anchor injection | 2 days | Identity in delegated agents |
| Add multi-tier role configurations | 1 day | Opus/Sonnet/Flash roles |
| Create wrapper script for session hooks | 2 days | Automated session lifecycle |
| Documentation and examples | 2 days | User guidance |
| Performance optimization | 2 days | Token and latency tuning |

**Exit Criteria:**
- Complete Agent OS experience
- Session lifecycle fully automated
- Clear documentation for operators

---

## 7. Technical Specifications

### 7.1 Tool Specifications

#### session_summary

```yaml
name: session_summary
description: >
  Summarize current session to OCTAVE-format episodic memory.
  Call at session end to persist learnings, decisions, and continuation points.

input_schema:
  type: object
  properties:
    thread_id:
      type: string
      description: Conversation thread ID to summarize
    agent_role:
      type: string
      description: Primary agent role
      default: unknown
    action:
      type: string
      enum: [summarize, summarize_and_persist, get_recent]
      default: summarize_and_persist
    days_back:
      type: integer
      description: For get_recent - how many days of episodes
      default: 3
  required: [thread_id]

model_requirements:
  category: FLASH
  reason: Summarization is fast model appropriate
```

#### anchor

```yaml
name: anchor
description: >
  Manage Odyssean Anchors - agent identity persistence across sessions.
  Like Leonard Shelby's tattoos, anchors bind agents to remember who they are.

input_schema:
  type: object
  properties:
    action:
      type: string
      enum: [load, create, update, verify]
      default: load
    role:
      type: string
      description: Agent role (implementation-lead, critical-engineer, etc.)
    component:
      type: string
      enum: [shank, arm, fluke]
      description: For update action - which component to update
    content:
      type: string
      description: For update action - new content
  required: [role]

model_requirements:
  category: FLASH
  reason: Extraction and verification are fast model appropriate
```

#### session_context

```yaml
name: session_context
description: >
  System Steward's context loading interface.
  Provides curated context based on task, not everything.

input_schema:
  type: object
  properties:
    task:
      type: string
      description: Task description or identifier
    role:
      type: string
      default: holistic-orchestrator
    roadmap:
      type: string
      description: Path to project roadmap for next task detection
    mode:
      type: string
      enum: [curated, full, minimal]
      default: curated
  required: []

model_requirements:
  category: FLASH
  reason: Context curation analysis is fast model appropriate
```

### 7.2 Directory Structure

```
.coord/
├── system-memory/
│   ├── episodes/
│   │   ├── 2025-12-06.md
│   │   └── 2025-12-07.md
│   ├── patterns.md
│   └── anchors/
│       ├── implementation-lead.anchor.md
│       ├── critical-engineer.anchor.md
│       └── holistic-orchestrator.anchor.md
├── PROJECT-CONTEXT.md
├── PROJECT-ROADMAP.md
└── PROJECT-CHECKLIST.md
```

### 7.3 Configuration

```env
# .env additions

# Episodic Memory
EPISODIC_MEMORY_PATH=.coord/system-memory
EPISODE_RETENTION_DAYS=30

# Storage Backend
STORAGE_BACKEND=file  # memory | file | redis
PERSISTENT_MEMORY_PATH=~/.hestai/storage

# Conversation Settings (existing)
CONVERSATION_TIMEOUT_HOURS=24
MAX_CONVERSATION_TURNS=50

# Context Loading
DEFAULT_CONTEXT_MODE=curated  # curated | full | minimal
MAX_CONTEXT_TOKENS=5000
```

---

## 8. Risks and Considerations

### 8.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| File-based storage corruption | Low | Medium | JSON validation, atomic writes |
| Anchor drift from constitution | Medium | High | Periodic verification tool |
| Episode accumulation bloat | Medium | Low | Retention policy, OCTAVE compression |
| Context curation accuracy | Medium | Medium | Feedback loop, user override option |
| Multi-tier routing errors | Low | Low | Conservative defaults, tier override |

### 8.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Increased setup complexity | High | Medium | Clear documentation, defaults |
| Migration from current workflow | Medium | Medium | Phased rollout, backward compatibility |
| Performance overhead | Low | Low | Caching, lazy loading |
| User confusion with new tools | Medium | Low | Examples, training |

### 8.3 Constraints

1. **MCP Protocol Limitations**
   - No PostResponse hook for output monitoring
   - Request/response size limits
   - No native session lifecycle events

2. **CLI Agent Constraints**
   - Each invocation is stateless
   - No direct memory sharing between CLI calls
   - Anchor must be re-injected each call

3. **Storage Constraints**
   - File-based storage not suitable for high concurrency
   - Redis adds operational complexity
   - SQLite requires schema management

---

## 9. Comparison: Current vs Proposed Workflow

### Current Workflow

```
1. User starts Claude Code session
2. /load ho → Loads EVERYTHING (21k+ tokens)
3. HO receives task
4. HO uses Task tool → Spawns subagent
5. Subagent is FRESH (no memory, no identity)
6. Subagent completes, returns to HO
7. HO uses HestAI-MCP for quality gates
8. Session ends, context lost
9. Next session starts FRESH
```

**Pros:**
- Simple mental model
- Built-in Claude Code subagent management
- Low setup complexity

**Cons:**
- Each subagent is fresh (no continuity)
- Everything loaded regardless of task
- No cross-session learning
- Context lost at session end
- No identity persistence

### Proposed Workflow

```
1. User starts Claude Code session
2. HO invokes session_context(task="...")
   → System Steward curates context (~3k tokens)
   → Loads relevant episodic memory
   → Loads anchor for HO
3. HO receives curated context + task
4. HO invokes task_router → Gets tier recommendation
5. HO invokes clink(role="implementation-lead")
   → Anchor injected into delegated agent
   → Continuation ID for memory
6. IL completes, returns to HO
7. HO uses HestAI-MCP for quality gates
   → Registry tracks approvals
   → Patterns detected
8. Session end: HO invokes session_summary
   → Episode recorded in OCTAVE
   → Continuation points saved
9. Next session: System Steward loads relevant history
```

**Pros:**
- Agents have identity (anchors)
- Cross-session learning (episodic memory)
- Task-aware context (not everything)
- Continuation possible via IDs
- Patterns detected and surfaced
- ~60% token reduction

**Cons:**
- More complex setup
- New tools to learn
- Requires discipline (session_summary calls)
- Additional MCP overhead

### Verdict

The proposed workflow is **superior for complex, ongoing projects** where context continuity and learning matter. The current workflow remains appropriate for **simple, isolated tasks**.

**Recommendation:** Implement as opt-in enhancement. Users can choose:
- `session_context(mode="full")` → Current behavior
- `session_context(mode="curated")` → New optimized behavior

---

## 10. Appendices

### Appendix A: OCTAVE Compression Format

OCTAVE (Optimized Compressed Text for AI-Vector Encoding) is a compression format designed for AI context efficiency:

**Principles:**
1. Remove redundant phrasing
2. Use bullet points over prose
3. Reference instead of repeat
4. Preserve decision points
5. Maintain action items

**Example:**

```markdown
# Before (verbose)
The implementation lead reviewed the FK constraint issue and decided that
CASCADE behavior would be more appropriate than SET NULL because it maintains
referential integrity automatically when parent records are deleted. This
decision was made after consulting with the database architect who confirmed
that our data model supports this approach. We should document this decision
in the schema documentation.

# After (OCTAVE)
**Decision:** FK behavior = CASCADE (not SET NULL)
- Rationale: Auto referential integrity on parent delete
- Consulted: DB architect (confirmed)
- Action: Document in schema docs
```

### Appendix B: Odyssean Anchor Research Summary

**Source:** `elevanaltd/hestai-research/02-proven-insights/breakthroughs/odyssean-anchor/ODYSSEAN_ANCHOR_FINDINGS.md`

**Key Findings:**

1. **The Constitutional Paradox**
   - Empirical evidence showed agents perform differently than constitutional constraints suggest
   - SHANK-ARM-FLUKE separates identity from phase-specific behavior

2. **Three-Part Architecture**
   - **SHANK**: Immutable core identity (~50 tokens)
   - **ARM**: Phase context (~50 tokens)
   - **FLUKE**: Active capabilities (~50 tokens)

3. **Loading Protocol**
   ```
   load PATHOS_SHANK on ACTUAL_ARM with BUILD,CREATIVE_CODING
   ```

4. **Benefits**
   - Clean governance hierarchy
   - Empirical adaptability without identity drift
   - Natural evolutionary flexibility

### Appendix C: GitHub Issue Details

#### Issue #1: Episodic Memory
- **Priority:** P1
- **Proposal:** `.coord/system-memory/episodes/` structure
- **Key Insight:** Pull-based memory (agents retrieve on demand) prevents context bloat
- **Acceptance:** Directory structure, episode per session, OCTAVE compression

#### Issue #4: Blockage Resolution Protocol
- **Priority:** P1
- **Proposal:** Structured multi-agent resolution without human intervention
- **Key Insight:** COMPLIANCE blockages → fast-track, COHERENCE blockages → synthesis crucible
- **Status:** Partially implemented via registry tool

#### Issue #7: North Star Loading
- **Priority:** P1
- **Recommendation:** Compression over lazy-loading
- **Reason:** Escalation protocols require <50ms lookups
- **Target:** 60-70% size reduction (2-3k token savings)

### Appendix D: Reference Implementation Snippets

See Section 7 for complete tool specifications.

Additional code examples available in the conversation history that generated this report.

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-06 | Claude (Opus 4) | Initial comprehensive proposal |

---

## Next Steps

1. **Review this proposal** with stakeholders
2. **Prioritize Phase 0 tasks** for immediate implementation
3. **Create tracking issues** in hestai-mcp-server repo
4. **Begin implementation** of session_summary and anchor tools
5. **Document learnings** for future iterations
