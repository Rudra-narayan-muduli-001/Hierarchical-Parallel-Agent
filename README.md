# 🧠 Parallel Mind 2.0

**Self-Healing · Hierarchical · Multi-LLM Orchestration**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-0.1.0-blue?style=flat-square)]()
[![Tests](https://img.shields.io/badge/Tests-122%20passed-brightgreen?style=flat-square)]()
[![Models](https://img.shields.io/badge/Models-3%20mock%20%2B%203%20real-purple?style=flat-square)]()

---

## What Is This?

Parallel Mind is an **orchestrator for teams of LLMs**. You submit a single task —
it gets classified, decomposed, and delegated down a four-rank hierarchy. Each rank
is a specialized LLM agent that:

1. **Decomposes** its sub-task into smaller pieces and delegates them down
2. **Executes** atomic work (or drives MCP worker pools) at the leaves
3. **Synthesizes** the results back up into a reasoned, merged answer

The system is **self-healing**: when any model times out, rate-limits, or errors,
the parent rank automatically swaps in a replacement — all the way up to a
**Boss Election** if the Boss itself dies.

> **Zero API cost to try it.** The default config ships with 3 deterministic
> mock models that work end-to-end with fault injection, so you can demo the entire
> failover machinery for free before plugging in real providers.

---

## Architecture

```
TASK ROUTER (classifies task → category)
        │
        ▼
    ┌─────────┐
    │  BOSS   │  (tier S) — decomposes, assigns complexity tiers
    └────┬────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
┌────────┐ ┌────────┐ ┌────────┐
│Manager │ │Manager │ │Manager │  (tier A/B)
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Supervisor│ │Supervisor│ │Supervisor│  (tier B/C)
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│Labour  │  │Labour  │  │Labour  │  (tier C/D)
└────┬───┘  └────┬───┘  └────┬───┘
     │           │           │
     ▼           ▼           ▼
┌──────────────────────────────────────────┐
│        MCP Worker Pools (research)       │
│  🔍 Search  ·  🌐 Browser  ·  💻 Code  ·  📁 Files
└──────────────────────────────────────────┘
```

**Every rank is the same class** — Boss, Manager, Supervisor, and Labour share one
`Node` base with different prompts, tiers, and constraints. No duplicated logic.

---

## Key Features

| Feature | Detail | Benefit |
|---------|--------|---------|
| 🎚️ Four-tier hierarchy | S / A / B / C / D model tiers | Complexity-gated model allocation |
| 🔁 Automatic failover | Labour → Supervisor → Manager → Boss | Retries, backoff, model swaps at every rank |
| 🗂️ Pool allocation | Exclusion rules + reuse fallback | Never two siblings on the same model |
| 🗳️ Boss election | Managers vote via LLM | The hierarchy heals its own head |
| 💬 Peer communication | Rank + sibling channels | Supervisors warn each other about overlap |
| 🧰 MCP worker pools | Firecrawl, Playwright, code_exec, filesystem | InfoSeeker-compatible labour variants |
| 📊 Live GUI | React + WebSocket event stream | Watch the tree think, fail, and heal in real time |
| 💰 Cost tracking | Per-node & per-task accounting | Token/cost summary on completion |
| 💾 Resumable | SQLite event log | Replay any task from its last snapshot |
| 🧪 Mock-first | Deterministic fault injection | Full failover testing with zero API spend |

---

## Quick Start

### Prerequisites

- **Python 3.11+** (tested on 3.12)
- **Node.js 18+** & **npm** (for the GUI)

### 1. Install

```bash
pip install -r requirements.txt
cd gui && npm install && cd ..
```

### 2. Configure

Add API keys to `.env` at the repo root (copy from `.env.example`):

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=...
FIRECRAWL_API_KEY=...
```

> **No keys? No problem.** The default config uses 3 mock models
> (`mock-super`, `mock-mid`, `mock-cheap`) — real providers activate the moment
> you reference them in `config/config.yaml`.

### 3. Start the Backend

**Windows PowerShell**
```powershell
$env:PYTHONPATH="src"
python -m uvicorn hierarchy.api.server:app --host 0.0.0.0 --port 8000 --reload
```

**Linux / macOS**
```bash
PYTHONPATH=src python -m uvicorn hierarchy.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Verify it's live:
```bash
curl http://localhost:8000/api/config
```

### 4. Start the GUI

```bash
cd gui && npm run dev
```

Open **http://localhost:3000** — the Vite server proxies `/api/*` to port 8000.

### 5. Or Use the CLI

**Windows PowerShell**
```powershell
$env:PYTHONPATH="src"
python -m hierarchy.cli.main "Implement a binary search tree" --category coding
```

**Linux / macOS**
```bash
PYTHONPATH=src python -m hierarchy.cli.main "Implement a binary search tree" --category coding
```

---

## Testing

All **122 tests** run offline against the mock provider — no API keys, no network.

**Windows PowerShell**
```powershell
$env:PYTHONPATH="src"
python -m pytest tests/ -v
```

**Linux / macOS**
```bash
PYTHONPATH=src python -m pytest tests/ -v
```

| Suite | Count | Covers |
|-------|-------|--------|
| Unit | 114 | Config, schemas, providers, pool allocator, failover, synthesizer, peer bus, cost tracker, event store, node lifecycle, hierarchy, boss election, router |
| Integration | 8 | Full-tree success, labour timeout swap, supervisor/manager API-error swap, boss failure election, 60% failure warning, single-model degraded fallback, zero-model hard failure |

---

## Project Structure

```
parallel-mind-2.0/
├── AGENTS.md                # Build specification (15 phases)
├── ARCHITECTURE.md          # System design & failover rules
├── requirements.txt         # Python dependencies
├── config/
│   ├── config.yaml          # Categories, models, failover, behavior
│   ├── mcp_servers.yaml     # MCP server configs for worker pools
│   └── prompts/             # Per-role system prompts (boss/manager/supervisor/labour)
├── src/hierarchy/
│   ├── api/                 # FastAPI + WebSocket backend
│   ├── cli/                 # CLI entry point
│   ├── config/              # Config loading + Pydantic models
│   ├── core/                # Node, Boss, Manager, Supervisor, Labour, Failover…
│   ├── events/              # Event Bus + SQLite store
│   ├── persistence/         # Repository pattern (resumability)
│   ├── providers/           # mock · openai · anthropic · deepseek
│   ├── registry/            # Model registry + tier ordering
│   ├── router/              # Task → category classification
│   ├── schemas/             # Task, Decomposition, Synthesis, Events
│   ├── telemetry/           # Cost tracker
│   └── workers/             # MCP pools: search, browser, code, file
├── gui/                     # React 18 + TypeScript + Vite
│   └── src/
│       ├── components/      # TreeView, NodeDetail, PeerChat, WarningBanner…
│       ├── state/           # Zustand store
│       └── api/             # REST + WebSocket clients
└── tests/
    ├── unit/                # 114 tests
    └── integration/         # 8 failover scenario tests
```

---

## Configuration Reference

```yaml
tiers:
  order: [S, A, B, C, D]          # S = highest capability

categories:
  coding:
    boss_model: mock-super
    boss_system_prompt: prompts/boss/coding_boss.md
  research:
    boss_model: mock-super
    boss_system_prompt: prompts/boss/research_boss.md
    worker_pools:
      search:     { pool_size: 8 }
      browser:    { pool_size: 2 }
      code:       { pool_size: 1 }
      filesystem: { pool_size: 1 }

models:
  - id: mock-super
    provider: mock
    tier: S
    context_window: 128000
    api_key_env: MOCK_API_KEY
    rate_limit_rpm: 1000

failover:
  max_retries_per_node: 2
  retry_backoff_seconds: [2, 5]
  warning_threshold_percent: 60     # triggers task_warning event
  cooldown_after_failure_seconds: 300

behavior:
  continue_on_degraded: true
  allow_model_reuse_on_pool_exhaustion: true
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Submit task → final output + cost |
| GET  | `/api/tasks/{id}` | Get task status |
| GET  | `/api/tasks/{id}/tree` | Get full node tree |
| GET  | `/api/config` | Sanitized config (no secrets) |
| WS   | `/api/ws/tasks/{id}` | Live event stream for the GUI |

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_text": "Implement a binary search tree", "category": "coding"}'
```

---

## Event Types (GUI Contract)

The WebSocket bus is the single source of truth — the GUI is a pure renderer of
this stream:

```
node_created           { node_id, role, category, tier, model_id, parent_id }
node_status_changed    { node_id, old_status, new_status }
node_thought           { node_id, text }
node_output            { node_id, output }
node_error             { node_id, error_type, message }
node_replaced          { node_id, old_model_id, new_model_id, reason }
node_reused_model      { node_id, model_id }
peer_message           { from_node_id, scope, text }
task_warning           { task_id, kind: "failure_threshold", failure_percent }
task_degraded          { task_id, kind: "single_model" | "hierarchy_unstable" }
task_completed         { task_id, final_output, cost_summary }
task_failed            { task_id, reason: "zero_models_available" }
boss_election_started  { category, candidate_manager_ids }
boss_election_result   { category, new_boss_node_id }
worker_pool_created    { node_id, pool_type, pool_size }
worker_task_started    { node_id, worker_id, subtask_index }
worker_task_completed  { node_id, worker_id, subtask_index }
worker_task_failed     { node_id, worker_id, subtask_index, error }
```

---

## Build Phases

Built in 15 incremental phases (full spec in `AGENTS.md`):

| Phase | Deliverable |
|-------|-------------|
| 0 | Project skeleton, typed config loader |
| 1 | Provider layer + mock provider with fault injection |
| 2 | Schemas: Task, Decomposition, Synthesis, NodeState, Events |
| 3 | Model Registry + Pool Allocator |
| 4 | Node base class + Labour + Context Budget |
| 5 | Event Bus + SQLite event store |
| 6 | Failover manager (swap rules, 60% warning) |
| 7 | Synthesizer (reasoned merge at every non-leaf rank) |
| 8 | Supervisor → Manager → Boss + Boss Election |
| 8b | MCP worker pools (search, browser, code, files) |
| 9 | Peer communication bus |
| 10 | Task Router + Orchestrator + CLI |
| 11 | Real providers: OpenAI, Anthropic, DeepSeek |
| 12 | Cost tracking + resumability |
| 13 | GUI backend (FastAPI + WebSockets) |
| 14 | GUI frontend (React + Zustand) |
| 15 | Full test sweep + docs + v1.0 |

---

> *"A single model is a single point of failure."*
>
> **Parallel Mind 2.0** — when one mind isn't enough, build a parliament.
>
