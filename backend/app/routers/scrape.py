from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["scrape"])
logger = logging.getLogger(__name__)

# Prevent two simultaneous Playwright sessions.
_scrape_lock = asyncio.Lock()


class ScrapeResult(BaseModel):
    status: str
    listings_upserted: int
    message: str


@router.post("/scrape", response_model=ScrapeResult)
async def trigger_scrape() -> ScrapeResult:
    """Launch a Playwright Otodom scrape and ingest results into the DB.

    Blocks until the scrape completes (typically 1-3 minutes). Returns 409
    if a scrape is already running.
    """
    if _scrape_lock.locked():
        raise HTTPException(status_code=409, detail="A scrape is already in progress.")

    async with _scrape_lock:
        logger.info("Manual scrape triggered via API.")
        try:
            from app.datasources.playwright_scraper import PlaywrightOtodomDataSource
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Playwright is not installed on this server. "
                    "Run: pip install -r requirements-scraper.txt && playwright install chromium"
                ),
            )

        from app.database import _get_session_local
        from app.services.ingestion import IngestService

        try:
            db = _get_session_local()()
            try:
                service = IngestService(datasource=PlaywrightOtodomDataSource(), db=db)
                count = await service.run()
            finally:
                db.close()
        except Exception as exc:
            logger.exception("Manual scrape failed: %s", exc)
            raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}")

        if count == 0:
            msg = (
                "Scrape completed but returned 0 listings. "
                "Cloudflare may have blocked the request from this server's IP. "
                "Try running the CLI scraper locally instead."
            )
        else:
            msg = f"Successfully upserted {count} listings."

        logger.info("Manual scrape finished: %d listings upserted.", count)
        return ScrapeResult(status="ok", listings_upserted=count, message=msg)
