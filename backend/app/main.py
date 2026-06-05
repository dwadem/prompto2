from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, _get_session_local
from app.routers import listings, overview
from app.scheduler import start_scheduler

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rzeszów Buy-to-Let Investment Analyser",
    description="API for analysing buy-to-let investment opportunities in Rzeszów, Poland.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_origins = [o.strip() for o in get_settings().CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # wildcard origin is incompatible with allow_credentials per CORS spec
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(listings.router)
app.include_router(overview.router)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def _run_initial_ingestion() -> None:
    """Background task: ingest sample data after the server is already up."""
    settings = get_settings()
    try:
        from app.datasources.factory import build_datasource
        from app.services.ingestion import IngestService

        datasource = build_datasource(settings.DATA_SOURCE)

        SessionLocal = _get_session_local()
        db = SessionLocal()
        try:
            service = IngestService(datasource=datasource, db=db)
            count = await service.run()
            logger.info("Initial ingestion complete: %d listings upserted.", count)
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Initial ingestion failed: %s", exc)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise DB and scheduler, then kick off ingestion in the background.

    Ingestion is deliberately deferred so the health-check endpoint responds
    immediately after uvicorn starts; Railway (and other PaaS) probe it before
    the ingestion job finishes.
    """
    # DB schema creation is fast and must finish before any request is served.
    init_db()
    logger.info("Database initialised.")

    # Scheduler is lightweight to start.
    start_scheduler(app)

    # Ingestion runs in the background so /api/health responds right away.
    asyncio.create_task(_run_initial_ingestion())


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "city": "Rzeszów"}
