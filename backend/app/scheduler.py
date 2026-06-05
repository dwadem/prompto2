from __future__ import annotations

import asyncio
import logging
import random

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


def _run_playwright_scrape() -> None:
    """Scrape Otodom via headless Chromium and ingest the results immediately.

    Runs as a daily cron job. Playwright must be installed separately:
        pip install -r requirements-scraper.txt
        playwright install chromium
    """
    try:
        from app.database import _get_session_local
        from app.datasources.playwright_scraper import PlaywrightOtodomDataSource
        from app.services.ingestion import IngestService

        logger.info("Playwright daily scrape starting…")
        db = _get_session_local()()
        try:
            service = IngestService(datasource=PlaywrightOtodomDataSource(), db=db)
            count = asyncio.run(service.run())
            logger.info("Playwright daily scrape finished: %d rows upserted.", count)
        finally:
            db.close()
    except ImportError:
        logger.error(
            "Playwright is not installed. Run: "
            "pip install -r requirements-scraper.txt && playwright install chromium"
        )
    except Exception as exc:
        logger.exception("Playwright daily scrape failed: %s", exc)


def start_scheduler(app: FastAPI) -> None:  # noqa: ARG001
    global _scheduler

    settings = get_settings()
    _scheduler = BackgroundScheduler()

    # --- existing ingestion job (re-reads DATA_SOURCE, default json_cache) ---
    _scheduler.add_job(
        _run_ingestion,
        trigger="interval",
        hours=settings.SCHEDULE_INTERVAL_HOURS,
        id="ingestion_job",
        replace_existing=True,
    )
    logger.info(
        "Ingestion job scheduled every %d hour(s) [DATA_SOURCE=%s].",
        settings.SCHEDULE_INTERVAL_HOURS,
        settings.DATA_SOURCE,
    )

    # --- daily Playwright scrape at a random hour ---
    if settings.PLAYWRIGHT_SCRAPE_ENABLED:
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        _scheduler.add_job(
            _run_playwright_scrape,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="playwright_scrape_job",
            replace_existing=True,
        )
        logger.info(
            "Playwright scraper scheduled daily at %02d:%02d "
            "(random hour chosen at startup).",
            hour,
            minute,
        )
    else:
        logger.info(
            "Playwright scraper disabled (set PLAYWRIGHT_SCRAPE_ENABLED=true to enable)."
        )

    _scheduler.start()
