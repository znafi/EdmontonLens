"""FastAPI application entrypoint for EdmontonLens.

Run locally with:
    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import agent, neighbourhoods, parks, transit, waste

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edmontonlens.api")

app = FastAPI(
    title="EdmontonLens API",
    description="AI-powered civic analytics for City of Edmonton open data.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transit.router)
app.include_router(parks.router)
app.include_router(waste.router)
app.include_router(neighbourhoods.router)
app.include_router(agent.router)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure local tables exist so the API works immediately in dev."""
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not initialise local DB on startup: %s", exc)


@app.get("/")
def root() -> dict[str, object]:
    """Health/info endpoint."""
    return {
        "service": "EdmontonLens API",
        "status": "ok",
        "bigquery_enabled": settings.bigquery_enabled,
        "gemini_enabled": settings.gemini_enabled,
        "gemini_model": settings.gemini_model,
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
