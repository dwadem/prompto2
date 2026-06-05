from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["scrape"])
logger = logging.getLogger(__name__)

# In-process scrape state (single-worker deployment).
_state: dict = {"running": False, "listings_upserted": 0, "message": "", "error": ""}


class ScrapeStarted(BaseModel):
    status: str  # "started" | "already_running"


class ScrapeStatus(BaseModel):
    running: bool
    listings_upserted: int
    message: str
    error: str


async def _run_scrape() -> None:
    _state["running"] = True
    _state["listings_upserted"] = 0
    _state["message"] = ""
    _state["error"] = ""

    logger.info("Background scrape started.")
    try:
        from app.datasources.playwright_scraper import PlaywrightOtodomDataSource
        from app.database import _get_session_local
        from app.services.ingestion import IngestService

        db = _get_session_local()()
        try:
            service = IngestService(datasource=PlaywrightOtodomDataSource(), db=db)
            count = await service.run()
        finally:
            db.close()

        _state["listings_upserted"] = count
        if count == 0:
            _state["message"] = (
                "Scrape completed but returned 0 listings. "
                "Cloudflare may have blocked this server's IP. "
                "Try running the CLI scraper locally instead."
            )
        else:
            _state["message"] = f"Successfully upserted {count} listings."
        logger.info("Background scrape finished: %d listings.", count)

    except ImportError:
        _state["error"] = (
            "Playwright is not installed on this server. "
            "Run: pip install -r requirements-scraper.txt && playwright install chromium"
        )
        logger.error(_state["error"])
    except Exception as exc:
        _state["error"] = f"Scrape failed: {exc}"
        logger.exception("Background scrape failed: %s", exc)
    finally:
        _state["running"] = False


@router.post("/scrape", response_model=ScrapeStarted)
async def trigger_scrape(background_tasks: BackgroundTasks) -> ScrapeStarted:
    """Start a Playwright Otodom scrape in the background and return immediately.

    Poll GET /api/scrape/status to track progress.
    Returns 409 if a scrape is already running.
    """
    if _state["running"]:
        raise HTTPException(status_code=409, detail="A scrape is already in progress.")

    background_tasks.add_task(_run_scrape)
    return ScrapeStarted(status="started")


@router.get("/scrape/status", response_model=ScrapeStatus)
async def scrape_status() -> ScrapeStatus:
    """Return the current scrape state."""
    return ScrapeStatus(**_state)
