# AGENTS.md

## Purpose of This Document

This file is the **build specification**. While `ARCHITECTURE.md` describes *what the system is and how it behaves*, this document describes *how to build it, in what order, with what files, and what each piece must do*. Follow this sequentially — each phase produces a runnable, testable increment.

---

## 1. Guiding Build Principles

1. **Build bottom-up, test top-down.** Get a single Labour making a real LLM call working first, then wrap it in a Supervisor, then a Manager, then a Boss.
2. **Mock the LLM layer from day one.** A fake/mock provider must exist before real providers, so failover logic (timeouts, rate limits, errors) can be tested deterministically without burning API credits.
3. **Event Bus first, GUI later.** The orchestrator must emit a complete, correct event stream before any GUI is built — the GUI is just a renderer of that stream.
4. **One mode only.** Never branch code paths for "degraded mode" vs "normal mode" — degraded behavior must fall naturally out of the same allocator/failover logic operating on a shrunken model list. If you find yourself writing `if degraded:`, stop and reconsider.
5. **Everything is a Node.** Boss/Manager/Supervisor/Labour are the same base class with different prompts/constraints — do not duplicate logic four times.
6. **Structured outputs everywhere.** Every LLM call that produces a decomposition, tier assignment, model choice, or synthesis must use a strict JSON schema (Pydantic model) — never parse free text for control decisions.

---

## 2. Full Folder & File Structure

```
llm-hierarchy/
│
├── ARCHITECTURE.md
├── AGENTS.md
├── README.md
├── config/
│   ├── config.yaml                  # main config (categories, models, failover, behavior)
│   ├── prompts/
│   │   ├── boss/
│   │   │   ├── coding_boss.md
│   │   │   ├── math_boss.md
│   │   │   └── research_boss.md
│   │   ├── manager_generic.md
│   │   ├── supervisor_generic.md
│   │   ├── labour_generic.md
│   │   ├── synthesizer_generic.md   # used by Supervisor/Manager/Boss merge step
│   │   ├── router_classifier.md     # task -> category classification
│   │   └── boss_election.md         # used when Boss fails, Managers vote
│   └── schemas/                     # JSON-schema mirrors of Pydantic models (for docs/tools)
│
├── src/
│   └── hierarchy/
│       ├── __init__.py
│       │
│       ├── config/
│       │   ├── loader.py            # parses config.yaml -> typed Config object
│       │   └── models.py            # Pydantic: Config, CategoryConfig, ModelSpec, FailoverConfig, BehaviorConfig
│       │
│       ├── registry/
│       │   └── model_registry.py    # ModelRegistry: lookup, tier ordering, LRU tracking for reuse
│       │
│       ├── providers/
│       │   ├── base.py              # abstract Provider interface: complete(), stream(), supports_structured_output()
│       │   ├── mock_provider.py      # deterministic/fault-injectable provider for tests
│       │   ├── openai_provider.py
│       │   ├── anthropic_provider.py
│       │   ├── deepseek_provider.py
│       │   ├── provider_factory.py   # maps ModelSpec.provider -> Provider instance
│       │   └── errors.py             # normalized error taxonomy: TimeoutError, RateLimitError, ApiError, AuthError
│       │
│       ├── schemas/
│       │   ├── task.py               # Task, SubTask
│       │   ├── decomposition.py      # DecompositionPlan (list of sub-tasks + assigned tier + role)
│       │   ├── synthesis.py          # SynthesisResult (merged_output, rationale, confidence)
│       │   ├── node_state.py         # NodeState enum + NodeSnapshot (GUI payload)
│       │   └── events.py             # Event types (see §5)
│       │
│       ├── core/
│       │   ├── node.py               # Node base class (Boss/Manager/Supervisor/Labour subclass this)
│       │   ├── boss.py
│       │   ├── manager.py
│       │   ├── supervisor.py
│       │   ├── labour.py
│       │   ├── pool_allocator.py     # remaining-pool computation + reuse fallback
│       │   ├── context_budget.py     # trims/summarizes context to fit model window
│       │   ├── synthesizer.py        # shared reasoning-merge routine used by Sup/Mgr/Boss
│       │   ├── failover.py           # error classification + swap logic per §6 of ARCHITECTURE
│       │   ├── peer_bus.py           # pub/sub scoped by (category, rank) and (parent_id)
│       │   ├── boss_election.py      # Manager-vote logic on Boss failure
│       │   └── orchestrator.py       # top-level driver: build tree, run task, own the Event Bus
│       │
│       ├── router/
│       │   └── task_router.py        # classifies incoming task -> category (LLM call or user-specified)
│       │
│       ├── events/
│       │   ├── bus.py                # async pub/sub Event Bus
│       │   └── store.py              # persistence: SQLite/JSONL event log + task-tree snapshotting
│       │
│       ├── persistence/
│       │   ├── db.py                 # SQLite setup/migrations
│       │   └── repository.py         # save/load Task, NodeSnapshot, EventLog for resumability
│       │
│       ├── telemetry/
│       │   └── cost_tracker.py       # token/cost accounting per node & per task
│       │
│       ├── api/
│       │   ├── server.py             # FastAPI app
│       │   ├── ws.py                 # WebSocket endpoint streaming Event Bus to GUI
│       │   ├── routes_tasks.py       # POST /tasks, GET /tasks/{id}, GET /tasks/{id}/tree
│       │   └── routes_config.py      # GET /config (sanitized: no secrets)
│       │
│       └── cli/
│           └── main.py               # `python -m hierarchy.cli.main "task text" --category coding`
│
├── gui/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── api/
│       │   ├── ws.ts                 # WebSocket client, event dispatch
│       │   └── rest.ts
│       ├── state/
│       │   └── treeStore.ts          # client-side tree state built from event stream
│       ├── components/
│       │   ├── TreeView.tsx          # main hierarchical graph (Cytoscape/react-d3-tree)
│       │   ├── NodeDetailPanel.tsx   # thought stream, output, model, retries
│       │   ├── PeerChatOverlay.tsx
│       │   ├── WarningBanner.tsx     # 60% failure / degraded-hierarchy notices
│       │   └── TaskSubmitForm.tsx
│       └── styles/...
│
├── tests/
│   ├── unit/
│   │   ├── test_pool_allocator.py
│   │   ├── test_failover.py
│   │   ├── test_context_budget.py
│   │   ├── test_synthesizer.py
│   │   └── test_boss_election.py
│   ├── integration/
│   │   ├── test_full_tree_mock_success.py
│   │   ├── test_labour_timeout_swap.py
│   │   ├── test_supervisor_api_error_swap.py
│   │   ├── test_manager_api_error_swap.py
│   │   ├── test_boss_failure_election.py
│   │   ├── test_60_percent_failure_warning.py
│   │   ├── test_single_model_degraded_fallback.py
│   │   └── test_zero_model_hard_failure.py
│   └── e2e/
│       └── test_gui_event_stream.py
│
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## 3. Build Order (Phased, Incremental)

### **Phase 0 — Project Skeleton**
- Repo scaffolding, `pyproject.toml`, dependency setup (pydantic, fastapi, uvicorn, pyyaml, pytest, httpx, websockets).
- `config/config.yaml` with 1 category, 3 fake models, minimal prompts.
- `config/loader.py` + `config/models.py`: load & validate config into typed objects.
- **Deliverable**: `python -c "from hierarchy.config.loader import load_config; print(load_config('config/config.yaml'))"` works.

### **Phase 1 — Provider Layer + Mock Provider**
- `providers/base.py` interface.
- `providers/errors.py` normalized exceptions.
- `providers/mock_provider.py`: configurable to return canned structured JSON, or **simulate** `TimeoutError`, `RateLimitError`, `ApiError` on command (for later failover tests).
- `providers/provider_factory.py`.
- **Deliverable**: unit tests calling mock provider with injected faults, asserting correct exception types.

### **Phase 2 — Schemas**
- `schemas/task.py`, `schemas/decomposition.py`, `schemas/synthesis.py`, `schemas/node_state.py`, `schemas/events.py`.
- These are the contracts everything else depends on — lock them early.
- **Deliverable**: round-trip serialize/deserialize tests.

### **Phase 3 — Model Registry + Pool Allocator**
- `registry/model_registry.py`: holds all `ModelSpec`s, tier ordering, LRU usage tracking.
- `core/pool_allocator.py`: implement exclusion rules (§5 of ARCHITECTURE) + reuse-on-exhaustion fallback, tagging `reused: true`.
- **Deliverable**: `tests/unit/test_pool_allocator.py` covers: normal exclusion chain, complexity-tier ceiling enforcement, exhaustion → reuse fallback, single-model-left case.

### **Phase 4 — Node Base Class + Labour**
- `core/node.py`: base class with id, role, category, tier, model binding, status, children, thought log, `run()` lifecycle hook.
- `core/labour.py`: simplest concrete node — executes one atomic LLM call, no children.
- `core/context_budget.py`: basic truncation logic tied to `ModelSpec.context_window`.
- **Deliverable**: a Labour node executes against the mock provider and emits status transitions (`assigned → executing → completed`).

### **Phase 5 — Event Bus & Store**
- `events/bus.py`: async pub/sub.
- `events/store.py` + `persistence/db.py` + `persistence/repository.py`: append-only event log, task/tree snapshot persistence for resumability.
- Wire Node lifecycle → Event Bus (every status change, thought, error emits an event).
- **Deliverable**: run a Labour, dump the full event log, confirm it replays into an identical NodeSnapshot.

### **Phase 6 — Failover Manager**
- `core/failover.py`: classify caught exception → decide swap strategy per rule table (Labour swap by Supervisor, Supervisor swap by Manager, Manager swap by Boss, Boss → election).
- Retry/backoff config wiring (`max_retries_per_node`, `retry_backoff_seconds`).
- Failure-ratio tracker (60% warning) + single-model degraded detector + zero-model hard-failure detector.
- **Deliverable**: `tests/unit/test_failover.py` — inject each error type at each level with mock provider, assert correct swap target and that siblings/children are untouched.

### **Phase 7 — Synthesizer**
- `core/synthesizer.py`: shared routine — given a sub-task + children outputs/confidences + peer notes, make a structured LLM call (mock in tests) producing `SynthesisResult` (merged output + rationale).
- Used identically by Supervisor, Manager, Boss (just different prompt file).
- **Deliverable**: unit test verifying synthesis rationale is captured and streamed as a "thinking" event.

### **Phase 8 — Supervisor → Manager → Boss (compose upward)**
- `core/supervisor.py`: spawns Labours via Pool Allocator, waits, calls Synthesizer, handles Labour failover.
- `core/manager.py`: spawns Supervisors, same pattern, handles Supervisor failover.
- `core/boss.py`: spawns Managers with **assigned complexity tiers**, does final synthesis, handles Manager failover (triggers election on its own failure — but election logic lives one level up, in the orchestrator, since Boss can't manage its own replacement).
- `core/boss_election.py`: on Boss failure, gather active Managers, run bounded structured "vote" exchange (LLM calls using `boss_election.md` prompt), promote winner, backfill a new Manager if needed.
- **Deliverable**: `tests/integration/test_full_tree_mock_success.py` — full Boss→Manager→Supervisor→Labour run against mock provider, happy path, correct final synthesized output.

### **Phase 9 — Peer Communication Bus**
- `core/peer_bus.py`: channels scoped by `(category, rank)` and `(parent_id)`.
- Wire into Manager/Supervisor/Labour so they can publish/subscribe short structured messages, and include relevant peer notes (budget-limited) into their next reasoning/synthesis call.
- **Deliverable**: integration test with 2 sibling Supervisors — one posts "already handled X," the other's synthesis reflects awareness of it.

### **Phase 10 — Task Router + Orchestrator**
- `router/task_router.py`: classify raw task text → category (LLM call, or explicit user override).
- `core/orchestrator.py`: the top-level entry point — takes raw task, resolves category, instantiates Boss, drives the whole run, owns Event Bus + persistence, exposes `run_task(task_text, category=None) -> final_result`.
- **Deliverable**: CLI (`cli/main.py`) can run an end-to-end task fully through mock provider from the command line.

### **Phase 11 — Real Providers**
- `providers/openai_provider.py`, `anthropic_provider.py`, `deepseek_provider.py` (extend as needed) — implement the same `Provider` interface, real HTTP calls, structured-output support, real error mapping into the normalized taxonomy.
- `.env.example` documenting required API key env vars.
- **Deliverable**: swap mock for real provider in config, run one real end-to-end task successfully; run one real end-to-end task with a deliberately bad API key on one model to confirm real failover triggers.

### **Phase 12 — Cost Tracking & Resumability Hardening**
- `telemetry/cost_tracker.py`: token/cost logging per node call, aggregated per task.
- Confirm persistence layer supports resuming an interrupted task from last consistent snapshot.
- **Deliverable**: kill orchestrator mid-task, restart, task resumes rather than restarting from scratch.

### **Phase 13 — GUI Backend (API layer)**
- `api/server.py`, `api/ws.py`: WebSocket streams live Event Bus to any connected client; REST endpoints to submit tasks and fetch current/past tree snapshots.
- `api/routes_config.py`: sanitized config exposure (category list, model list — no secrets) for the GUI's task-submit form.
- **Deliverable**: `wscat`/Postman can connect and watch live JSON events while a task runs via REST trigger.

### **Phase 14 — GUI Frontend**
- Scaffold React app (`gui/`), WebSocket client (`api/ws.ts`) building a local tree store from events (`state/treeStore.ts`).
- `components/TreeView.tsx`: renders Boss→Manager→Supervisor→Labour tree, color-coded by status, collapsible.
- `components/NodeDetailPanel.tsx`: click node → thought stream / output / model / retry history.
- `components/PeerChatOverlay.tsx`: toggleable chat-bubble view of peer messages.
- `components/WarningBanner.tsx`: 60%-failure warning, degraded-hierarchy notice, task progress.
- `components/TaskSubmitForm.tsx`: category selector (or auto), task text box.
- **Deliverable**: full live demo — submit a task in the browser, watch the tree build, execute, fail/replace nodes, synthesize, and complete, all in real time.

### **Phase 15 — Full Test Sweep + Docs Pass**
- Run all integration tests (mock-based) covering every failure scenario in ARCHITECTURE §6, plus the 60%-warning and single-model/zero-model edge cases.
- Update `README.md` with setup, config, run instructions.
- Tag `v1.0`.

---

## 4. Module Responsibility Reference (Quick Lookup)

| Module | Responsibility | Depends on |
|---|---|---|
| `config/loader.py` | YAML → typed `Config` | `config/models.py` |
| `registry/model_registry.py` | Model lookup, tier order, LRU | `config` |
| `providers/*` | Uniform LLM call interface + normalized errors | — |
| `core/node.py` | Shared lifecycle/state machine | `schemas`, `events/bus.py` |
| `core/pool_allocator.py` | Compute remaining model pool per node, reuse fallback | `registry` |
| `core/context_budget.py` | Fit context to model window | `registry` |
| `core/synthesizer.py` | Reasoned merge of children outputs | `providers`, `schemas/synthesis.py` |
| `core/failover.py` | Classify errors, execute correct swap rule, track failure % | `providers/errors.py`, `pool_allocator` |
| `core/peer_bus.py` | Same-rank/same-parent messaging | `events/bus.py` |
| `core/boss_election.py` | Manager vote on Boss failure | `providers`, `peer_bus` |
| `core/orchestrator.py` | End-to-end task driver, owns everything | all of `core/*`, `router`, `events`, `persistence` |
| `events/bus.py` + `store.py` | Live pub/sub + durable log | — |
| `persistence/*` | Resumable task state | `events/store.py` |
| `telemetry/cost_tracker.py` | Token/cost accounting | `providers` |
| `api/*` | Expose orchestrator + live events to GUI | `core/orchestrator.py`, `events/bus.py` |
| `gui/*` | Visualize tree + thoughts + chat + warnings live | `api/*` |

---

## 5. Event Types (contract between backend and GUI)

```
node_created        { node_id, role, category, tier, model_id, parent_id }
node_status_changed { node_id, old_status, new_status }
node_thought        { node_id, text, ts }
node_output         { node_id, output, ts }
node_error          { node_id, error_type, message, ts }
node_replaced       { node_id, old_model_id, new_model_id, reason, ts }
node_reused_model   { node_id, model_id }
peer_message        { from_node_id, scope, text, ts }
task_warning        { task_id, kind: "failure_threshold", failure_percent }
task_degraded       { task_id, kind: "single_model" | "hierarchy_unstable" }
task_completed       { task_id, final_output, cost_summary }
task_failed          { task_id, reason: "zero_models_available" }
boss_election_started { category, candidate_manager_ids }
boss_election_result  { category, new_boss_node_id }
```

This event contract is the single source of truth the GUI is built against — define it in `schemas/events.py` before Phase 13 begins.

---

## 6. Definition of Done (v1.0)

- [ ] All four ranks implemented as one shared `Node` base class.
- [ ] Pool allocation + reuse fallback verified by tests.
- [ ] All four failover rules (Labour/Supervisor/Manager/Boss) verified by tests, with correct scope-of-impact (siblings/children untouched).
- [ ] 60% warning + single-model degraded notice + zero-model hard failure all verified.
- [ ] Synthesis is a real reasoning LLM call at every non-leaf level, with rationale captured.
- [ ] Peer communication works both sibling-scoped and category-rank-scoped.
- [ ] Only one mode exists in code — no `if degraded_mode:` branching.
- [ ] GUI shows live tree, live thought stream, peer chat overlay, and warning banners, driven purely by the Event Bus.
- [ ] Task is resumable after orchestrator restart.
- [ ] README lets a new developer set up config + API keys and run a task end-to-end within 10 minutes.