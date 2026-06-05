#!/usr/bin/env python3
"""Standalone Otodom scraper CLI.

Runs the Playwright data source and writes the collected Rzeszów listings to a
JSON or CSV file that the json_cache data source can ingest. Intended to be run
locally (where a real browser can pass Cloudflare) and the output committed.

Usage:
    # from the backend/ directory, after:
    #   pip install -r requirements.txt -r requirements-scraper.txt
    #   playwright install chromium
    python -m scripts.scrape_otodom --out data/otodom_rzeszow.json
    python -m scripts.scrape_otodom --out data/otodom_rzeszow.csv --pages 3

Then commit the output file under backend/data/ and redeploy; the app will
ingest it on next startup / scheduled run.

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

# Make the app package importable when run as a script from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.datasources.playwright_scraper import PlaywrightOtodomDataSource

logger = logging.getLogger("scrape_otodom")

# Canonical column order for CSV output.
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


async def _run(pages: int | None) -> list[dict]:
    source = PlaywrightOtodomDataSource()
    if pages is not None:
        source._max_pages = pages  # noqa: SLF001 - intentional CLI override
    return await source.fetch_listings()


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Otodom Rzeszów listings.")
    parser.add_argument(
        "--out",
        default="data/otodom_rzeszow.json",
        help="Output file path (.json or .csv). Default: data/otodom_rzeszow.json",
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

    listings = asyncio.run(_run(args.pages))

    if not listings:
        logger.error(
            "No listings collected. Cloudflare may have blocked the request, "
            "or the __NEXT_DATA__ layout changed. Try running non-headless / "
            "from a residential IP, or inspect a saved page."
        )
        return 1

    out = args.out
    parent = os.path.dirname(os.path.abspath(out))
    os.makedirs(parent, exist_ok=True)

    if out.lower().endswith(".csv"):
        _write_csv(out, listings)
    else:
        _write_json(out, listings)

    logger.info("Wrote %d listings to %s", len(listings), out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
