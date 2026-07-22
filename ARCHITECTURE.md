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
11. **Event Bus / State Store** — append-only event log + live in-memory tree, optionally persisted (SQLite/JSON) for crash-recovery and audit/history.
12. **GUI Backend** — WebSocket/REST server exposing the live tree and event stream to the frontend.
13. **GUI Frontend** — renders the tree, node detail panel (status, thoughts, output), warnings banner, degraded-hierarchy banner.

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
  order: [S, A, B, C, D]     # S = highest

categories:
  coding:
    boss_model: deepseek-v4-pro
    boss_system_prompt: prompts/coding_boss.md
  math:
    boss_model: gpt-5-pro
    boss_system_prompt: prompts/math_boss.md
  research:
    boss_model: claude-opus-x
    boss_system_prompt: prompts/research_boss.md

models:
  - id: deepseek-v4-pro
    provider: deepseek
    tier: S
    context_window: 128000
    api_key_env: DEEPSEEK_API_KEY
    rate_limit_rpm: 60
  - id: gpt-5-pro
    provider: openai
    tier: S
    context_window: 256000
    api_key_env: OPENAI_API_KEY
  - id: some-mid-model
    provider: mistral
    tier: B
    context_window: 32000
    api_key_env: MISTRAL_API_KEY
  - id: cheap-fast-model
    provider: groq
    tier: D
    context_window: 8000
    api_key_env: GROQ_API_KEY

failover:
  max_retries_per_node: 2
  retry_backoff_seconds: [2, 5]
  warning_threshold_percent: 60
  cooldown_after_failure_seconds: 300

behavior:
  continue_on_degraded: true      # auto-continue in single-model fallback
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
  "peer_group_id": "coding:supervisor",
  "task": { "id": "t_77", "description": "...", "parent_task_id": "t_70" },
  "status": "synthesizing",
  "thought_stream": [
    { "ts": "...", "text": "Waiting on 2 labours..." },
    { "ts": "...", "text": "Labour lab_02 timed out, replacing model..." }
  ],
  "output": null,
  "error": null,
  "replaced_history": [ { "from": "old-model", "reason": "timeout", "ts": "..." } ],
  "retries": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

Node `status` enum: `idle, assigned, thinking, executing, waiting_children, synthesizing, completed, failed, replaced, degraded`.

---

## 11. GUI Design

- **Backend**: FastAPI + WebSocket, streaming Event Bus messages to connected clients; REST endpoints for task submission/history.
- **Frontend**: React + a hierarchical graph renderer (e.g. Cytoscape.js / react-d3-tree), collapsible per branch.
- **Tree view**: Boss at top, Managers/Supervisors/Labours as expandable children; color-coded by status (grey=idle, blue=thinking, yellow=executing, green=completed, orange=replaced, red=failed).
- **Node detail panel**: click a node → live thought stream, current output, model in use, retry/replace history.
- **Peer chat overlay**: toggle to show inter-node messages as chat bubbles between same-rank nodes.
- **Top banner**: global warnings (≥60% failure), degraded-hierarchy notice, task progress %.

---

## 12. Cross-Cutting / Non-Functional Additions (gaps I resolved)

These weren't explicitly specified but are necessary for the system to actually work well; decisions made in the project's favor:

1. **Structured decomposition output** — all decomposition/synthesis calls use enforced JSON schema (function-calling/structured output) so the Orchestrator can reliably parse sub-tasks, tiers, and model choices instead of free-text parsing.
2. **Context Budget Manager** — truncates/summarizes history and sibling outputs per node based on its model's context window, so large trees don't blow context limits.
3. **Cost & token tracking** — every node call logs tokens/cost; aggregated per task and shown in GUI (useful since Boss/Manager tiers are expensive).
4. **Persistence & resumability** — task tree + event log persisted (SQLite by default) so a crash of the orchestrator process doesn't lose an in-flight task; can resume from last consistent state.
5. **Security** — API keys only referenced via env var names in config, never stored/logged in plaintext; secrets redacted from event log/GUI.
6. **Proactive rate-limit awareness** — optional `rate_limit_rpm` per model lets the Orchestrator soft-throttle before hitting real 429s, reducing reactive failovers.
7. **Model reuse tagging** — anywhere diversity fallback triggers (§5.4), the GUI clearly marks it so users understand why the same model appears twice.
8. **Dev/test harness** — a mock-provider mode purely for testing failover logic without burning API credits. This is a *developer tool*, not a user-facing execution mode — it doesn't violate the "single hierarchy mode" rule.
9. **Boss-failure election** — kept lightweight: a short structured reasoning exchange between existing Managers (bounded turns) rather than an open-ended negotiation, to avoid stalling the task.

---

## 13. Tech Stack Summary

- **Backend/Orchestrator**: Python (asyncio for parallel Labour execution), Pydantic for schemas.
- **LLM access**: unified adapter layer per provider (OpenAI/Anthropic/DeepSeek/etc.), so swapping models is just changing an ID.
- **Event Bus**: in-process async pub/sub (e.g. `asyncio.Queue` based), broadcast over WebSocket.
- **Persistence**: SQLite (or JSON lines log) for task tree + event history.
- **GUI backend**: FastAPI.
- **GUI frontend**: React + Cytoscape.js (or react-d3-tree) + WebSocket client.
- **Config**: YAML.

---
