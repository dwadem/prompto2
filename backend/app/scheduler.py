from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_ingestion() -> None:
    """Synchronous wrapper that runs the async ingestion pipeline."""
    try:
        # Import here to avoid circular imports at module load time
        from app.database import _get_session_local
        from app.datasources.json_cache import JsonCacheDataSource
        from app.datasources.otodom_scraper import OtodomScraperDataSource
        from app.services.ingestion import IngestService

        settings = get_settings()
        SessionLocal = _get_session_local()

        if settings.DATA_SOURCE == "otodom":
            datasource = OtodomScraperDataSource()
        else:
            datasource = JsonCacheDataSource()

        db = SessionLocal()
        try:
            service = IngestService(datasource=datasource, db=db)
            count = asyncio.run(service.run())
            logger.info("Scheduled ingestion finished: %d rows upserted.", count)
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Scheduled ingestion failed: %s", exc)


def start_scheduler(app: FastAPI) -> None:  # noqa: ARG001
    """Create and start the background scheduler, attaching it to the FastAPI app lifecycle."""
    global _scheduler

    settings = get_settings()

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_ingestion,
        trigger="interval",
        hours=settings.SCHEDULE_INTERVAL_HOURS,
        id="ingestion_job",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started; ingestion runs every %d hour(s).",
        settings.SCHEDULE_INTERVAL_HOURS,
    )
