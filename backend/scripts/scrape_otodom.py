#!/usr/bin/env python3
"""Standalone Otodom scraper CLI.

Runs the Playwright data source and either:
  - writes listings to a JSON/CSV file (default, for committing to the repo), or
  - upserts them directly into a database via --db (useful with Postgres).

Usage:
    # Write to file (commit and let json_cache ingest on next deploy):
    python -m scripts.scrape_otodom --out data/otodom_rzeszow.json

    # Write directly to a local SQLite DB:
    python -m scripts.scrape_otodom --db sqlite:///./data/rzeszow.db

    # Write directly to Render Postgres (paste External Database URL from Render):
    python -m scripts.scrape_otodom --db postgresql://user:pass@host:5432/rzeszow

    # DATABASE_URL env var is used as a fallback when --db is given without a value:
    DATABASE_URL=postgresql://... python -m scripts.scrape_otodom --db

ToS / robots.txt compliance is the operator's responsibility.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.datasources.playwright_scraper import PlaywrightOtodomDataSource

logger = logging.getLogger("scrape_otodom")

_CSV_FIELDS = [
    "url", "title", "transaction_type", "district", "neighbourhood",
    "price_pln", "area_m2", "rooms", "floor", "year_built",
    "finishing_condition", "lat", "lng", "scraped_at",
]


def _write_json(path: str, listings: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(listings, fh, ensure_ascii=False, indent=2)


def _write_csv(path: str, listings: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in listings:
            writer.writerow(row)


def _upsert_to_db(database_url: str, listings: list[dict]) -> int:
    """Upsert listings into the given database. Returns count upserted."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker

    from app.models.listing import Base
    from app.services.ingestion import IngestService
    from app.datasources.base import DataSource

    url = make_url(database_url)
    connect_args = {"check_same_thread": False} if url.drivername.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    class _StaticSource(DataSource):
        def __init__(self, items: list[dict]) -> None:
            self._items = items

        async def fetch_listings(self) -> list[dict]:
            return self._items

    db = Session()
    try:
        service = IngestService(datasource=_StaticSource(listings), db=db)
        return asyncio.run(service.run())
    finally:
        db.close()


async def _scrape(pages: int | None) -> list[dict]:
    source = PlaywrightOtodomDataSource()
    if pages is not None:
        source._max_pages = pages  # noqa: SLF001
    return await source.fetch_listings()


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Otodom Rzeszów listings.")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--out",
        default=None,
        help="Output file path (.json or .csv). Default: data/otodom_rzeszow.json",
    )
    output_group.add_argument(
        "--db",
        nargs="?",
        const=os.environ.get("DATABASE_URL", "sqlite:///./data/rzeszow.db"),
        metavar="DATABASE_URL",
        help=(
            "Upsert directly into a database. "
            "Accepts a SQLAlchemy URL (sqlite:/// or postgresql://). "
            "Falls back to DATABASE_URL env var if no value given."
        ),
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Max result pages per transaction type (overrides OTODOM_MAX_PAGES).",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging."
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    listings = asyncio.run(_scrape(args.pages))

    if not listings:
        logger.error(
            "No listings collected. Cloudflare may have blocked the request, "
            "or the __NEXT_DATA__ layout changed. Try running from a residential "
            "IP, or inspect a saved page."
        )
        return 1

    if args.db:
        logger.info("Upserting %d listings into %s …", len(listings), args.db)
        count = _upsert_to_db(args.db, listings)
        logger.info("Done: %d listings upserted.", count)
    else:
        out = args.out or "data/otodom_rzeszow.json"
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        if out.lower().endswith(".csv"):
            _write_csv(out, listings)
        else:
            _write_json(out, listings)
        logger.info("Wrote %d listings to %s", len(listings), out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
