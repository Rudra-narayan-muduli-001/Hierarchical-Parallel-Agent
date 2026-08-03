# Parallel Mind 2.0 — Self-Healing Hierarchical Multi-LLM Orchestration

A self-healing, hierarchical multi-LLM orchestration system where a single user task is delegated through a chain of command — **Boss → Manager → Supervisor → Labour** — with automatic failover, model tier allocation, peer communication, and live GUI visualization.

## Architecture Overview

```
Task Router (category classification)
         │
         ▼
    BOSS (max tier S) ──┐
         │             │
    ┌────┼────┐     Manager (tier A/B)
    │    │    │          │
Manager Manager Manager  Supervisor (tier B/C)
    │    │    │              │
    └────┼────┘           Labour (tier C/D)
         ▼
      Labour
```

**Key Features:**
- **Four-tier hierarchy** with tiered model allocation (S/A/B/C/D)
- **Automatic failover** at every level (Labour→Supervisor→Manager→Boss)
- **Model pool allocation** with exclusion rules + reuse fallback
- **Boss election** on failure via Manager vote
- **Peer communication** (category-rank + sibling channels)
- **Worker pools** (MCP-based: Firecrawl search, Playwright browser, code exec, filesystem)
- **Live GUI** with WebSocket event streaming
- **Cost tracking** per node and per task
- **Resumable** execution via SQLite event log

---

## Quick Start

### Prerequisites

- **Python 3.11+** (tested on 3.12)
- **Node.js 18+** (for GUI)
- **npm** (comes with Node.js)

### 1. Clone & Install

```bash
# From the repo root:

# Python backend dependencies
pip install -r requirements.txt

# GUI frontend dependencies
cd gui
npm install
cd ..
```

### 2. Configure

Edit `config/config.yaml` to set categories, models, failover, and behavior.

Add API keys to a `.env` file in the repo root (copy from `.env.example`):

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=...
FIRECRAWL_API_KEY=...
```

> **Note:** The default config ships with 3 **mock models** (`mock-super`, `mock-mid`, `mock-cheap`) so you can run end-to-end without any API keys. Real providers (OpenAI, Anthropic, DeepSeek) are implemented and activate when you reference them in `config.yaml`.

### 3. Run the Backend

```powershell
# Windows PowerShell (set PYTHONPATH so `hierarchy` package resolves)
$env:PYTHONPATH="src"
python -m uvicorn hierarchy.api.server:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Linux / macOS
PYTHONPATH=src python -m uvicorn hierarchy.api.server:app --host 0.0.0.0 --port 8000 --reload
```

The API server starts on **http://localhost:8000**.

Verify it's live:
```bash
curl http://localhost:8000/api/config
```

### 4. Run the GUI

In a **second terminal**:

```bash
cd gui
npm run dev
```

The Vite dev server starts on **http://localhost:3000** and proxies `/api/*` to the backend on port 8000.

Open **http://localhost:3000** in your browser to use the UI.

### 5. Run the CLI (alternative to GUI)

In a **third terminal**:

```powershell
# Windows PowerShell
$env:PYTHONPATH="src"
python -m hierarchy.cli.main "Implement a binary search tree" --category coding
```

```bash
# Linux / macOS
PYTHONPATH=src python -m hierarchy.cli.main "Implement a binary search tree" --category coding
```

---

## Testing

All 122 tests run without a live server (they use the mock provider):

```powershell
# Windows PowerShell
$env:PYTHONPATH="src"
python -m pytest tests/ -v
```

```bash
# Linux / macOS
PYTHONPATH=src python -m pytest tests/ -v
```

Breakdown:
- **114 unit tests** — config, schemas, providers, pool allocator, failover, synthesizer, peer bus, cost tracker, event store, node lifecycle, hierarchy (Boss/Manager/Supervisor), boss election, router
- **8 integration tests** — full tree success, labour timeout swap, supervisor/manager API-error swap, boss failure election, 60% failure warning, single-model degraded fallback, zero-model hard failure

---

## Project Structure

```
Parallel Mind 2.0/
├── AGENTS.md                # Build specification (phased plan)
├── ARCHITECTURE.md          # System architecture & design
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Python project config + pytest config
├── config/
│   ├── config.yaml          # Categories, models, failover, behavior
│   ├── mcp_servers.yaml     # MCP server configs for worker pools
│   └── prompts/             # System prompts per role (boss/manager/supervisor/labour)
├── src/hierarchy/
│   ├── api/                 # FastAPI + WebSocket backend
│   ├── cli/                 # CLI entry point
│   ├── config/              # Config loading & Pydantic models
│   ├── core/                # Core orchestration (Node, Boss, Manager, Supervisor, Labour, Failover, PeerBus, Orchestrator)
│   ├── events/              # Event Bus + Store (SQLite)
│   ├── persistence/         # Repository pattern for SQLite
│   ├── providers/           # LLM providers (mock, openai, anthropic, deepseek)
│   ├── registry/            # Model registry with tier ordering
│   ├── router/              # Task router (category classification)
│   ├── schemas/             # Pydantic schemas (Task, Decomposition, Synthesis, Events)
│   ├── telemetry/           # Cost tracker
│   └── workers/             # MCP worker pools (search, browser, code, file)
├── gui/                     # React + TypeScript + Vite frontend
│   ├── src/
│   │   ├── components/      # TreeView, NodeDetailPanel, PeerChatOverlay, WarningBanner, TaskSubmitForm
│   │   ├── state/           # Zustand store + types
│   │   └── api/             # REST + WebSocket clients
│   ├── package.json
│   └── vite.config.ts
└── tests/
    ├── unit/                # 114 unit tests
    └── integration/         # 8 integration tests (failover scenarios)
```

---

## Configuration Reference

### `config/config.yaml`

```yaml
tiers:
  order: [S, A, B, C, D]      # S = highest capability

categories:
  coding:
    boss_model: mock-super
    boss_system_prompt: prompts/boss/coding_boss.md
  research:
    boss_model: mock-super
    boss_system_prompt: prompts/boss/research_boss.md
    worker_pools:
      search: { pool_size: 8 }
      browser: { pool_size: 2 }
      code: { pool_size: 1 }
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
  warning_threshold_percent: 60
  cooldown_after_failure_seconds: 300

behavior:
  continue_on_degraded: true
  allow_model_reuse_on_pool_exhaustion: true
```

---

## API Endpoints

| Method | Endpoint              | Description                          |
|--------|-----------------------|--------------------------------------|
| POST   | `/api/tasks`          | Submit task, returns final output + cost |
| GET    | `/api/tasks/{id}`     | Get task status                      |
| GET    | `/api/tasks/{id}/tree`| Get full node tree                  |
| GET    | `/api/config`         | Get sanitized config (no secrets)   |
| WS     | `/api/ws/tasks/{id}`  | Live event stream                    |

### Example: Submit a Task via REST

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_text": "Implement a binary search tree", "category": "coding"}'
```

---

## Event Types (GUI Contract)

The backend emits these events on the WebSocket bus — the GUI renders them in real time:

```
node_created          { node_id, role, category, tier, model_id, parent_id }
node_status_changed   { node_id, old_status, new_status }
node_thought          { node_id, text }
node_output           { node_id, output }
node_error            { node_id, error_type, message }
node_replaced         { node_id, old_model_id, new_model_id, reason }
peer_message          { from_node_id, scope, text }
task_warning          { task_id, kind: "failure_threshold", failure_percent }
task_degraded         { task_id, kind: "single_model" | "hierarchy_unstable" }
task_completed        { task_id, final_output, cost_summary }
task_failed           { task_id, reason: "zero_models_available" }
boss_election_started { category, candidate_manager_ids }
boss_election_result  { category, new_boss_node_id }
worker_pool_created   { node_id, pool_type, pool_size }
worker_task_started   { node_id, worker_id, subtask_index }
worker_task_completed { node_id, worker_id, subtask_index }
worker_task_failed    { node_id, worker_id, subtask_index, error }
```

---

## Build Phases

This project was built in 15 phases (see `AGENTS.md` for the full specification):

| Phase | Description |
|-------|-------------|
| 0  | Project skeleton, config loader |
| 1  | Provider layer + MockProvider with fault injection |
| 2  | Schemas (Task, Decomposition, Synthesis, NodeState, Events) |
| 3  | Model Registry + Pool Allocator (exclusion rules + reuse) |
| 4  | Node base class + Labour + Context Budget + Event Bus |
| 5  | Event Store + SQLite persistence |
| 6  | Failover Manager (error classification, swap rules, 60% warning) |
| 7  | Synthesizer (reasoning merge at Supervisor/Manager/Boss) |
| 8  | Supervisor → Manager → Boss + Boss Election |
| 8b | MCP Worker Pools (Firecrawl, Playwright, Code, Filesystem) |
| 9  | Peer Communication Bus (category-rank + parent scopes) |
| 10 | Task Router + Orchestrator + CLI |
| 11 | Real Providers (OpenAI, Anthropic, DeepSeek) |
| 12 | Cost Tracker + Resumability |
| 13 | GUI Backend (FastAPI + WebSocket) |
| 14 | GUI Frontend (React + Zustand + WebSocket) |
| 15 | Full Test Sweep + README + v1.0 tag |

---

## License

MIT
