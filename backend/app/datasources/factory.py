from __future__ import annotations

import logging

from app.datasources.base import DataSource

logger = logging.getLogger(__name__)


def build_datasource(data_source: str | None = None) -> DataSource:
    """Return the configured DataSource.

    Recognised values for `data_source` (falls back to settings.DATA_SOURCE):
      - "json_cache" (default): load .json/.ndjson/.csv files from DATA_DIR
      - "playwright":           live scrape via headless Chromium (Cloudflare-safe)
      - "otodom":               legacy httpx + BeautifulSoup scraper

    Imports are local so optional dependencies (e.g. Playwright) are only
    required when that source is actually selected.
    """
    if data_source is None:
        from app.config import get_settings

        data_source = get_settings().DATA_SOURCE

    key = (data_source or "json_cache").strip().lower()

    if key == "playwright":
        from app.datasources.playwright_scraper import PlaywrightOtodomDataSource

        return PlaywrightOtodomDataSource()
    if key == "otodom":
        from app.datasources.otodom_scraper import OtodomScraperDataSource

        return OtodomScraperDataSource()

    if key != "json_cache":
        logger.warning("Unknown DATA_SOURCE %r; falling back to json_cache.", data_source)
    from app.datasources.json_cache import JsonCacheDataSource

    return JsonCacheDataSource()
