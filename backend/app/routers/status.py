from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
def get_status():
    """Return scheduler job state and DB listing count.

    Useful for verifying that the Playwright scraper (and other jobs) are
    registered and shows when they will next fire.
    """
    from app.database import _get_session_local
    from app.models.listing import Listing
    from app.scheduler import _scheduler

    # --- DB stats ---
    db = _get_session_local()()
    try:
        listing_count = db.query(Listing).count()
        latest_row = db.query(Listing.scraped_at).order_by(Listing.scraped_at.desc()).first()
        latest_scrape = latest_row[0].isoformat() if latest_row else None
    finally:
        db.close()

    # --- Scheduler jobs ---
    jobs = []
    if _scheduler is not None:
        for job in _scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.func_ref.__name__ if hasattr(job, "func_ref") else job.name,
                "next_run_utc": next_run.astimezone(timezone.utc).isoformat() if next_run else None,
                "trigger": str(job.trigger),
            })

    return {
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "db": {
            "listing_count": listing_count,
            "latest_scraped_at": latest_scrape,
        },
        "scheduler": {
            "running": _scheduler.running if _scheduler else False,
            "jobs": jobs,
        },
    }
