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

@app.on_event("startup")
async def startup_event() -> None:
    """Initialise the database and run the first ingestion pass."""
    settings = get_settings()

    # Ensure DB tables exist
    init_db()
    logger.info("Database initialised.")

    # Run initial ingestion
    try:
        from app.datasources.json_cache import JsonCacheDataSource
        from app.datasources.otodom_scraper import OtodomScraperDataSource
        from app.services.ingestion import IngestService

        if settings.DATA_SOURCE == "otodom":
            datasource = OtodomScraperDataSource()
        else:
            datasource = JsonCacheDataSource()

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

    # Start background scheduler
    start_scheduler(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "city": "Rzeszów"}
