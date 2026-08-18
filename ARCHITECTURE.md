# ARCHITECTURE.md

## 0. Project Summary

This project is a **self-healing, hierarchical multi-LLM orchestration system**. A single user task is handed to a category-specific chain of command — **Boss → Manager(s) → Supervisor(s) → Labour(s)** — where each tier decomposes, delegates, executes, and re-synthesizes work using different LLMs of decreasing cost/capability tier. The system is designed to survive API failures at any level by **replacing the failed agent, never cancelling the task**, to expose everything happening inside the hierarchy through a **live tree-view GUI**, and to allow **peer-to-peer conversation between agents of the same rank**.

There is only **one operating mode** — the Hierarchical Mode. Degraded states (fewer models available, down to a single model) are **emergent states of this same mode**, not alternate modes.

---

## 1. Core Concepts & Terminology

| Term | Meaning |
|---|---|
| **Category** | A domain of work (`coding`, `math`, `research`, `writing`, …), defined in config. Each category has its own Boss. |
| **Tier** | A capability/cost class of a model (e.g. `S`, `A`, `B`, `C`, `D`, S = max). Used to enforce "Boss = always max tier" and to bound what a Manager/Supervisor is allowed to spawn beneath it. |
| **Boss** | Top-of-chain agent for a category. Always instantiated on the highest-tier model configured for that category. Receives the raw task, the full model roster, context-window limits, and its role system prompt. Decomposes the task and spins up Managers, assigning each a complexity tier. |
| **Manager** | Mid-level planner. Receives a sub-task + the "remaining model pool" (global roster minus Boss minus other active Managers). Spawns Supervisors. |
| **Supervisor** | Receives a smaller sub-task + further-shrunk remaining pool. Spawns Labours. Responsible for **reasoned synthesis** of Labour outputs. |
| **Labour** | Leaf worker. Executes one atomic unit of work with one LLM call. No further delegation possible. |
| **Node** | Generic term for any Boss/Manager/Supervisor/Labour instance in the live task tree. Has a unique ID, state, parent, children. |
| **Peer Group** | All active nodes sharing the same `(category, tier-role)` — e.g. all Supervisors currently working under the `coding` Boss — can message each other. |
| **Remaining Pool** | The set of models a given node is allowed to choose subordinates from. Shrinks as you go down, per rules in §5. |

---

## 2. High-Level Diagram

```
                         ┌────────────────────┐
                         │   Task Router        │  (decides category)
                         └─────────┬───────────┘
                                   │
                         ┌─────────▼───────────┐
                         │   BOSS (max tier)     │  category-specific
                         └─────────┬───────────┘
                 ┌─────────────────┼─────────────────┐
        ┌────────▼───────┐ ┌───────▼────────┐ ┌───────▼────────┐
        │   MANAGER A       │ │  MANAGER B      │ │  MANAGER C      │  <-- peer chat (same category+rank)
        └────────┬───────┘ └───────┬────────┘ └───────┬────────┘
           ┌──────┼──────┐        ...                ...
     ┌─────▼──┐ ┌──▼─────┐
     │SUPERVIS│ │SUPERVIS│ ...                                        <-- peer chat
     └───┬────┘ └───┬────┘
     ┌───┼───┐   ┌───┼───┐
   ┌─▼─┐┌─▼─┐  ┌─▼─┐┌─▼─┐
   │LAB││LAB│  │LAB││LAB│                                             <-- peer chat
   └───┘└───┘  └───┘└───┘
```

All node activity is streamed to an **Event Bus**, consumed by the **GUI backend**, rendered as a live collapsible tree.

---

## 3. Component Breakdown

1. **Config Loader** — parses `config.yaml`: categories, boss assignment, model roster, tiers, prompts, failover thresholds.
2. **Model Registry** — normalized list of all models, their provider, API key env var, tier, context window, rate-limit hints.
3. **Task Router** — maps an incoming user request to a category (explicit user choice, or a lightweight classifier call).
4. **Orchestrator Core** — the engine that builds/manages the live node tree, drives delegation, executes calls, handles retries/replacement, triggers synthesis.
5. **Node** (base class, subclassed as Boss/Manager/Supervisor/Labour) — holds state, prompt, model binding, children, status, thought log.
6. **Pool Allocator** — computes the "remaining model pool" for each node per the exclusion rules (§5), with the reuse-fallback described in §5.4.
7. **Context Budget Manager** — trims/summarizes task text and children outputs so nothing exceeds a node's model context window.
8. **Failover Manager** — detects error types (timeout/rate-limit vs generic API error vs total-exhaustion), executes the correct replacement rule per tier (§6), tracks failure %, raises warnings/degradation flags.
9. **Reasoning/Synthesis Engine** — every non-leaf node's "merge children outputs" step is itself an LLM call with a dedicated synthesizer prompt (§7), not string concatenation.
10. **Peer Communication Bus** — pub/sub channels scoped by `(category, rank)` and by `(parent_id)` for tighter sibling chat (§8).
11. **Event Bus / State Store** — async pub/sub bus (`events/bus.py`) with a node registry and tree-snapshot endpoint, plus an append-only JSONL event store (`events/store.py`) and SQLite persistence (`persistence/`) for crash-recovery and audit/history. Emits the event contract in §12b.
12. **GUI Backend** — FastAPI REST (`POST /api/tasks`, `GET /api/tasks/{id}/tree`, `GET /api/config` — sanitized, no secrets) + WebSocket endpoint (`/ws`) streaming live `{type, data, ts}` events.
13. **GUI Frontend** — Vite/React app rendering the tree, node detail panel (status, thoughts, output), peer chat overlay, warnings banner, degraded-hierarchy banner (see §11).

---

## 4. End-to-End Task Flow

1. User submits a task (optionally selecting/confirming category; otherwise Task Router classifies it).
2. Orchestrator instantiates the category's **Boss** node with: task text, its role system prompt, full model roster (minus itself), context window limit.
3. Boss reasons and produces a **decomposition plan**: N sub-tasks, each assigned to a new **Manager**, each Manager given a **complexity tier** (S/A/B/C…).
4. For each Manager: Orchestrator computes its remaining pool (§5), instantiates the Manager node, hands it its sub-task + pool + budget.
5. Each Manager decomposes further into Supervisor-level sub-tasks, same pattern down to Supervisors → Labours.
6. **Labours execute** — one real LLM call per atomic unit, in parallel where independent.
7. Each **Supervisor** waits for its Labours, then performs a **reasoning synthesis pass** (LLM call) combining Labour outputs + their confidence/notes into one Supervisor-level result.
8. Each **Manager** does the same synthesis over its Supervisors' results.
9. **Boss** does the final synthesis over all Managers' results → final answer to user.
10. Every step above emits events (`created`, `status_changed`, `thought`, `output`, `error`, `replaced`, `completed`) to the Event Bus → GUI updates live.

---

## 5. Model Pool Allocation Rules

1. **Boss** = the model explicitly configured as `boss_model` for that category (always the category's max tier).
2. **Manager pool** = `AllModels − {Boss} − {other active Managers in this task}`.
3. **Supervisor pool** = `Manager pool − {this Manager} − {other active Supervisors in this task}`.
4. **Labour pool** = `Supervisor pool − {this Supervisor} − {other active Labours in this task}`.
5. **Complexity ceiling**: a node may only pick subordinates whose tier ≤ the complexity tier assigned to it by its parent (Boss assigns Manager tiers; Manager/Supervisor pass down a tier ceiling too, generally decreasing toward Labour for cost efficiency).
6. **Pool exhaustion fallback**: global no-repeat is a *preference for diversity*, not a hard blocker. If the pool empties before all required subordinates are created, the Allocator **reuses the least-recently-used eligible model** and tags that node `reused: true` (visible in GUI) rather than blocking task progress — consistent with the "never stop the work" principle.

---

## 6. Failure Handling & Self-Healing

| Failing node | Error type | Action |
|---|---|---|
| Labour | timeout / rate-limit | Supervisor **immediately swaps** the Labour's model (from remaining/reuse pool) and re-runs the same atomic task. |
| Supervisor | any API error | Manager **swaps the Supervisor's model**, keeping the *same Labours* underneath it untouched (their in-flight/completed work is preserved). |
| Manager | any API error | Boss **swaps the Manager's model**, keeping all Supervisors/Labours beneath it untouched. |
| Boss | any API error | **No auto-swap.** The existing Managers of that category negotiate (a short structured vote/reasoning exchange) to elect one of themselves as the new Boss; the elected Manager is promoted, a new Manager is spawned to cover its old slot if needed. |

**Provider-layer retries (before failover):** the OpenAI-compatible provider (`providers/openai_provider.py`, and every provider subclassing it) retries 429 rate-limit responses up to 3 times with backoff from the `retry-after` header (capped at 10s — some gateways send multi-minute values), maps 401 → `AuthError`, and 500/502/503 → `ApiError`. Failover per the table above only engages after these provider-level retries are exhausted.

**Global resilience rules (apply everywhere):**
- Never cancel the task on a single failure — always replace and retry the failed slot.
- Each node gets `max_retries_per_node` (config, default 2) with exponential backoff before being marked dead-for-this-task.
- Live failure ratio = `failed_agents_total / instantiated_agents_total` for the current task. If this crosses **60%**, emit a **non-blocking WARNING** event (shown in GUI banner) — work continues.
- If attrition reduces the *available distinct models* to **exactly one**, the system emits a **"Hierarchy degraded — running in single-model fallback"** notice. This is **not a separate mode**: the same Orchestrator keeps running, just every remaining role (Boss/Manager/Supervisor/Labour) is bound to that one model. It proceeds automatically only if the user has indicated to continue regardless (see config `continue_on_degraded: true`, or a runtime confirmation prompt); otherwise it pauses and asks the user.
- If truly **zero models** are available, only then does the task genuinely fail — this is the sole real termination condition.

---

## 7. Reasoning-Based Synthesis (not concatenation)

Every non-leaf node (Supervisor, Manager, Boss) performs a **Synthesis Call**:
- Input: the sub-task definition, each child's output, each child's self-reported confidence/caveats, and any peer-chat notes relevant to the sub-task.
- A dedicated **Synthesizer system prompt** instructs the model to: reconcile contradictions, discard low-confidence/erroneous child output, produce one coherent merged result, and produce a short "synthesis rationale" — this rationale is stored and streamed to the GUI as the node's "thinking" for that phase.
- This is a genuine LLM call (using the node's own bound model), not string-joining.

---

## 8. Peer Communication (same category, same rank)

Two channel scopes:
1. **Sibling channel** — nodes sharing the same immediate parent and rank (tight coordination, e.g. splitting overlapping sub-work, avoiding duplicate labour).
2. **Category-rank channel** — *all* active nodes of the same rank within the same category, regardless of branch/parent (loose broadcast, e.g. "I already solved X, don't redo it," shared discoveries, terminology alignment).

Peer messages are short, structured (`from_id`, `to_scope`, `text`, `task_ref`), are visible in the GUI as chat bubbles on the tree, and are optionally included as extra context in a node's next reasoning/synthesis call (bounded by the Context Budget Manager).

---

## 9. Config File Schema (example)

```yaml
tiers:
  order: [S, A, B, C, D]           # S = highest

categories:
  coding:
    boss_model: llama-3.1-8b-instant
    boss_system_prompt: prompts/boss/coding_boss.md
  research:
    boss_model: llama-3.1-8b-instant
    boss_system_prompt: prompts/boss/research_boss.md
    worker_pools:                 # MCP pools planned for research (§14, not yet wired)
      search: { pool_size: 8 }
      browser: { pool_size: 2 }
      code: { pool_size: 1 }
      filesystem: { pool_size: 1 }

models:
  - id: llama-3.1-8b-instant       # provider-agnostic id (may contain '/')
    provider: groq                 # mock | openai | anthropic | deepseek | groq | nvidia | opencode_zen
    tier: S
    context_window: 131072
    api_key_env: GROQ_API_KEY      # key referenced by env var name, never stored in config
    rate_limit_rpm: 30             # soft-throttle hint
  - id: qwen/qwen3.6-27b
    provider: groq
    tier: B
    context_window: 131072
    api_key_env: GROQ_API_KEY
    rate_limit_rpm: 30

failover:
  max_retries_per_node: 2
  retry_backoff_seconds: [2, 5]
  warning_threshold_percent: 60
  cooldown_after_failure_seconds: 300

behavior:
  continue_on_degraded: true       # auto-continue in single-model fallback
  allow_model_reuse_on_pool_exhaustion: true
```

---

## 10. Node Data Model (internal state / GUI payload)

```json
{
  "id": "sup_3f9a",
  "role": "supervisor",
  "category": "coding",
  "tier": "B",
  "model_id": "some-mid-model",
  "reused": false,
  "parent_id": "mgr_1a2b",
  "children_ids": ["lab_01", "lab_02"],
  "status": "synthesizing",
  "thought_stream": [
    { "ts": "...", "text": "Waiting on 2 labours..." },
    { "ts": "...", "text": "Labour lab_02 timed out, replacing model..." }
  ],
  "output": null,
  "error": null,
  "replaced_history": [ { "from_model": "old-model", "to_model": "new-model", "reason": "timeout", "ts": "..." } ],
  "retries": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

This mirrors `schemas/node_state.py` exactly (the GUI tree is rebuilt from these snapshots).

Node `status` enum: `idle, assigned, thinking, executing, waiting_children, synthesizing, completed, failed, replaced, degraded`.

---

## 11. GUI Design

- **Backend**: FastAPI (`api/server.py`) + WebSocket endpoint (`api/ws.py`) broadcasting Event Bus messages; REST: `POST /api/tasks` (submit), `GET /api/tasks/{id}/tree` (node snapshots), `GET /api/config` (sanitized — no secrets).
- **Frontend**: Vite + React + TypeScript + zustand (`gui/`), plain CSS (no graph library). One WebSocket client (`api/ws.ts`) dispatches `{type, data, ts}` events into a zustand tree store (`state/treeStore.ts`) that mirrors the NodeSnapshot model.
- **Layout** (`components/Layout.tsx`): left column = task list, center = active task view, right = node detail panel.
- **TreeView** (`components/TreeView.tsx`): Boss at top, Managers/Supervisors/Labours as collapsible children; color-coded by status (idle/thinking/executing/waiting/synthesizing/completed/failed/replaced/degraded).
- **NodeDetailPanel**: click a node → live thought stream, markdown-rendered output, model in use, retry/replace history.
- **ChatThread + ChatComposer**: chat-style conversation with the user, answers rendered via `MarkdownViewer.tsx` (react-markdown + remark-gfm); composer lets you pick a category (or auto) and submit a task.
- **PeerChatOverlay**: toggle to show `peer_message` events as chat bubbles between same-rank nodes.
- **WarningBanner**: ≥60% failure warning, single-model degraded notice, task progress.

---

## 12. Cross-Cutting / Non-Functional Additions (gaps I resolved)

These weren't explicitly specified but are necessary for the system to actually work well; decisions made in the project's favor:

1. **Structured JSON output (json_mode)** — every decomposition/synthesis/classification LLM call passes `response_format: json_object` (`json_mode=True`), and results are parsed with a tolerant parser (`core/jsonutil.py`: strips ``` fences, extracts the first `{...}` block) so control decisions never rely on free text. Decompositions are capped at 3 sub-tasks with required fields (`id`, `description`, `assigned_tier`, `assigned_role`) enforced by validation; synthesis child outputs are truncated to 800 chars per child before merging.
2. **Context Budget Manager** — truncates/summarizes history and sibling outputs per node based on its model's context window, so large trees don't blow context limits.
3. **Cost & token tracking** — every node call logs tokens/cost via a `TrackedProvider` wrapper (`telemetry/cost_tracker.py`); aggregated per task and shown in GUI (useful since Boss/Manager tiers are expensive).
4. **Persistence & resumability** — task tree + event log persisted (SQLite via `persistence/`, JSONL via `events/store.py`) so a crash of the orchestrator process doesn't lose an in-flight task; can resume from last consistent state.
5. **Security** — API keys only referenced via env var names in config, never stored/logged in plaintext; secrets redacted from event log/GUI.
6. **Proactive rate-limit awareness** — optional `rate_limit_rpm` per model lets the Orchestrator soft-throttle before hitting real 429s, reducing reactive failovers.
7. **Model reuse tagging** — anywhere diversity fallback triggers (§5.4), the GUI clearly marks it so users understand why the same model appears twice.
8. **Dev/test harness** — a mock-provider mode purely for testing failover logic without burning API credits. This is a *developer tool*, not a user-facing execution mode — it doesn't violate the "single hierarchy mode" rule.
9. **Boss-failure election** — kept lightweight: a short structured reasoning exchange between existing Managers (bounded turns) rather than an open-ended negotiation, to avoid stalling the task.
10. **Provider-level 429 handling** — OpenAI-compatible providers retry rate-limit responses up to 3 times with backoff derived from `retry-after` (capped at 10s) before failover ever engages; 401 maps to `AuthError`, 5xx to `ApiError` (`providers/errors.py`).
11. **Graceful task failure** — if no model survives (zero models available), the orchestrator emits `task_failed` and returns a structured error result instead of crashing the API.

---

## 12b. Event Contract (backend ↔ GUI)

Every event is `{ "type": "...", "data": {...}, "ts": "<ISO-8601>" }`, defined in `schemas/events.py` — the single source of truth the GUI is built against:

```
node_created        { node_id, role, category, tier, model_id, parent_id }
node_status_changed { node_id, old_status, new_status }
node_thought        { node_id, text }
node_output         { node_id, output }
node_error          { node_id, error_type, message }
node_replaced       { node_id, old_model_id, new_model_id, reason }
node_reused_model   { node_id, model_id }
peer_message        { from_node_id, scope, text }
task_warning        { task_id, kind: "failure_threshold", failure_percent }
task_degraded       { task_id, kind: "single_model" | "hierarchy_unstable" }
task_completed      { task_id, final_output, cost_summary }
task_failed         { task_id, reason: "zero_models_available" }
boss_election_started { category, candidate_manager_ids }
boss_election_result  { category, new_boss_node_id }
worker_pool_created   { node_id, pool_type, pool_size }        # planned (§14)
worker_task_started   { node_id, worker_id, subtask_index }    # planned (§14)
worker_task_completed { node_id, worker_id, subtask_index }    # planned (§14)
worker_task_failed    { node_id, worker_id, subtask_index, error }  # planned (§14)
```

---

## 14. InfoSeeker Integration — MCP Worker Pools

### 14.1 Overview
InfoSeeker (github.com/nj19257/InfoSeeker) is adapted into Parallel Mind as a set of **MCP-based worker pools** for the `research` category. The worker pool pattern enables massive parallelization (up to 40 concurrent workers) within a Supervisor's scope.

> **Status (current):** the worker layer is implemented but **not yet wired into the hierarchy**.
> `workers/*` (BaseMCPWorker, WorkerPool, and the four worker types), `config/mcp_servers.yaml`, and the worker/supervisor prompts all exist and are tested in isolation, but the bridge adapter (`core/worker_pool_adapter.py`) that connects a `WorkerPool` to the Node lifecycle does not exist yet — research Supervisors currently run standard LLM Labours. Pool integration and the worker events below are a planned next step.

### 14.2 Architecture

```
Research Boss (LLM tier S)
  └── Research Manager (LLM tier A)
       └── Research Supervisor (LLM tier B) ← manages WorkerPool
            ├── SearchWorker xN (Firecrawl MCP)   ← parallel web search
            ├── BrowserWorker xM (Playwright MCP)  ← browser automation
            ├── CodeWorker (code_exec MCP)         ← code execution
            └── FileWorker (filesystem_tools MCP)  ← file operations
```

### 14.3 What is kept from InfoSeeker
- **Worker pool pattern** — lock-protected pool, `asyncio.gather` parallel execution, retry with backoff
- **MCP server integrations** — Firecrawl (search), Playwright (browser), code_exec, filesystem_tools
- **Decomposition prompts** — research query breakdown strategy for Supervisors
- **Worker system prompts** — agent-level instructions for each worker type

### 14.4 What is replaced
| InfoSeeker original | Parallel Mind replacement |
|---|---|
| LangChain `create_agent()` | Native `BaseMCPWorker` using `mcp` SDK directly |
| LangChain agent loop | Node lifecycle + Event Bus |
| HostAgent (manual orchestration) | Boss → Manager → Supervisor hierarchy |
| ManagerHub (MCP tool) | Pool Allocator + Orchestrator Core |
| Autogen model clients | Unified Provider layer |

### 14.5 Worker Pool Flow
1. Research **Supervisor** receives sub-task and remaining model pool
2. Supervisor loads pool config from `config/mcp_servers.yaml`
3. **WorkerPool** lazily initializes N MCP workers (subprocesses)
4. Supervisor decomposes query into parallel subtasks
5. `WorkerPool.execute_subtasks(subtasks)` runs them via `asyncio.gather`
6. Results flow back for Supervisor synthesis (same as any Labour)

### 14.6 Files Added

| File | Source | Purpose |
|---|---|---|
| `src/hierarchy/workers/base_worker.py` | InfoSeeker agent pattern | Base MCP worker with `mcp` SDK client |
| `src/hierarchy/workers/worker_pool.py` | InfoSeeker pool pattern | Pool manager with retry + parallel execution |
| `src/hierarchy/workers/search_labour.py` | InfoSeeker SearchAgent | Firecrawl web search worker |
| `src/hierarchy/workers/browser_labour.py` | InfoSeeker BrowserAgent | Playwright browser worker |
| `src/hierarchy/workers/code_labour.py` | InfoSeeker CodeAgent | Code execution worker |
| `src/hierarchy/workers/file_labour.py` | InfoSeeker FilesystemAgent | Filesystem operations worker |
| `config/mcp_servers.yaml` | InfoSeeker pool_config.yaml | MCP server configurations |
| `config/prompts/labour/search_labour.md` | InfoSeeker SearchAgent prompt | Search worker system prompt |
| `config/prompts/labour/browser_labour.md` | InfoSeeker BrowserAgent prompt | Browser worker system prompt |
| `config/prompts/labour/code_labour.md` | InfoSeeker CodeAgent prompt | Code worker system prompt |
| `config/prompts/labour/file_labour.md` | InfoSeeker FilesystemAgent prompt | File worker system prompt |
| `config/prompts/supervisor/research_supervisor.md` | InfoSeeker SearchManager prompt | Research decomposition + pool coordination |
| `config/prompts/manager/research_manager.md` | InfoSeeker Manager strategy | Research manager synthesis prompt |

### 14.7 Integration Points

- **Pool Allocator** assigns the `research` category its own model roster (with MCP workers as Labour variants)
- **Supervisor (research variant)** holds a `WorkerPool` reference instead of individual Labour nodes
- **Failover** applies at the Supervisor level: if a pool worker exhausts retries, the Supervisor spawns a replacement
- **Event Bus** tracks pool activity: `worker_pool_created`, `worker_task_started`, `worker_task_completed`, `worker_task_failed`
- **GUI** shows pool workers as child nodes of the research Supervisor

---

## 15. Tech Stack Summary

- **Backend/Orchestrator**: Python (asyncio for parallel Labour execution), Pydantic for schemas.
- **LLM access**: unified adapter layer per provider — `mock`, `openai`, `anthropic`, `deepseek`, `groq`, `nvidia` (NVIDIA NIM), `opencode_zen` — so swapping models is just changing an ID. All HTTP-based providers subclass the OpenAI-compatible provider and share its retry/error handling.
- **Worker Pools (InfoSeeker integration)**: MCP (Model Context Protocol) via `mcp` SDK + `fastmcp`, subprocess isolation (implemented standalone, not yet wired — §14).
- **Event Bus**: in-process async pub/sub with node registry + append-only JSONL event store, broadcast over WebSocket.
- **Persistence**: SQLite (`persistence/`) for task/tree state + JSONL event log (`events/store.py`) for audit/resume.
- **GUI backend**: FastAPI.
- **GUI frontend**: Vite + React + TypeScript + zustand + react-markdown/remark-gfm, plain CSS, WebSocket client.
- **Config**: YAML.

---
