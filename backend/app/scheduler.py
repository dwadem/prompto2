from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_ingestion() -> None:
    """Re-ingest from the configured DATA_SOURCE (default: json_cache)."""
    try:
        from app.database import _get_session_local
        from app.datasources.factory import build_datasource
        from app.services.ingestion import IngestService

        settings = get_settings()
        db = _get_session_local()()
        try:
            service = IngestService(datasource=build_datasource(settings.DATA_SOURCE), db=db)
            count = asyncio.run(service.run())
            logger.info("Scheduled ingestion finished: %d rows upserted.", count)
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Scheduled ingestion failed: %s", exc)


def start_scheduler(app: FastAPI) -> None:  # noqa: ARG001
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
        "Scheduler started; json_cache ingestion runs every %d hour(s).",
        settings.SCHEDULE_INTERVAL_HOURS,
    )
