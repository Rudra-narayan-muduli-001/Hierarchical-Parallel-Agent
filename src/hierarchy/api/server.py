"""FastAPI app — serves the REST API + WebSocket endpoint.

Wires routes_tasks, routes_config, and ws together.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hierarchy.api.routes_tasks import router as tasks_router
from hierarchy.api.routes_config import router as config_router
from hierarchy.api.ws import router as ws_router

app = FastAPI(title="Parallel Mind API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(ws_router, prefix="/api")