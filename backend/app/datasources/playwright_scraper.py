from __future__ import annotations

# Playwright-based Otodom scraper.
#
# Otodom is a Next.js site behind Cloudflare. A plain HTTP client (httpx) gets
# blocked by the bot challenge, so this data source drives a real headless
# Chromium via Playwright, then reads the page's embedded `__NEXT_DATA__` JSON
# (far more stable than scraping DOM nodes).
#
# ToS / robots.txt compliance is the operator's responsibility. Throttle with
# REQUEST_DELAY_S and keep OTODOM_MAX_PAGES modest.
#
# NOTE: Otodom changes its JSON shape periodically. The parsing helpers below
# try the known path first, then fall back to a recursive search, and extract
# every field defensively. If a field stops populating, check a saved
# `__NEXT_DATA__` payload and adjust _parse_item / _extract_location.

import asyncio
import json
import logging
import re
from typing import Any, List, Optional
from urllib.parse import urljoin

from app.datasources.base import DataSource

logger = logging.getLogger(__name__)

# Search result paths for Rzeszów flats (sale / rent).
_SALE_PATH = "/pl/wyniki/sprzedaz/mieszkanie/podkarpackie/rzeszow"
_RENT_PATH = "/pl/wyniki/wynajem/mieszkanie/podkarpackie/rzeszow"

# Otodom encodes room counts as English number words in some payloads.
_ROOMS_WORDS = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
}

# Construction-status enums Otodom uses, mapped to our raw condition strings
# (which the ingestion service then normalises to FinishingCondition).
_STATUS_MAP = {
    "READY_TO_USE": "do zamieszkania",
    "READY_TO_LIVE": "do zamieszkania",
    "TO_COMPLETION": "stan deweloperski",
    "TO_RENOVATION": "do remontu",
}


# ---------------------------------------------------------------------------
# Pure parsing helpers (no I/O — unit tested against fixtures)
# ---------------------------------------------------------------------------

def _extract_next_data(html: str) -> dict:
    """Pull the JSON out of <script id="__NEXT_DATA__">…</script>."""
    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _looks_like_listings(dicts: List[dict]) -> bool:
    """Heuristic: does this list of dicts look like Otodom ad items?"""
    sample = dicts[0]
    keys = set(sample.keys())
    has_area = bool(keys & {"areaInSquareMeters", "area"})
    has_id = bool(keys & {"title", "slug", "id"})
    return has_area and has_id


def _find_listing_items(next_data: dict) -> List[dict]:
    """Locate the array of ad items inside __NEXT_DATA__.

    Tries the known path first, then falls back to a recursive search for the
    largest list of dicts that look like listings.
    """
    try:
        items = next_data["props"]["pageProps"]["data"]["searchAds"]["items"]
        if isinstance(items, list):
            dicts = [i for i in items if isinstance(i, dict)]
            if dicts:
                return dicts
    except (KeyError, TypeError):
        pass

    best: List[dict] = []

    def walk(node: Any) -> None:
        nonlocal best
        if isinstance(node, list):
            dicts = [x for x in node if isinstance(x, dict)]
            if dicts and _looks_like_listings(dicts) and len(dicts) > len(best):
                best = dicts
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(next_data)
    return best


def _num(value: Any) -> Optional[float]:
    """Coerce numbers, numeric strings, or {"value": n} money objects to float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.\-]", "", value.replace(",", "."))
        try:
            return float(cleaned) if cleaned not in ("", "-", ".") else None
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("value", "amount"):
            if key in value:
                return _num(value[key])
    return None


def _rooms_to_int(value: Any) -> Optional[int]:
    """Map ONE/TWO/… or numeric room counts to an int."""
    if isinstance(value, str):
        upper = value.strip().upper()
        if upper in _ROOMS_WORDS:
            return _ROOMS_WORDS[upper]
    n = _num(value)
    return int(n) if n is not None else None


def _extract_location(item: dict) -> tuple[str, str]:
    """Best-effort (district, neighbourhood) extraction.

    Otodom nests location differently across payloads. We gather candidate
    place names, drop the region/city, and use the remaining ones from least
    to most specific.
    """
    loc = item.get("location") or {}
    candidates: List[str] = []

    # reverseGeocoding.locations: ordered region → city → district → estate
    rg = loc.get("reverseGeocoding")
    if isinstance(rg, dict):
        for entry in rg.get("locations") or []:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("fullName")
                if name:
                    candidates.append(str(name).strip())

    # address.{district,subdistrict,city}
    addr = loc.get("address")
    if isinstance(addr, dict):
        for key in ("district", "subdistrict", "quarter", "street"):
            val = addr.get(key)
            if isinstance(val, dict):
                val = val.get("name")
            if isinstance(val, str) and val.strip():
                candidates.append(val.strip())

    # Drop region/city noise and de-dupe while preserving order.
    noise = {"podkarpackie", "rzeszów", "rzeszow", "polska", "poland"}
    seen: set[str] = set()
    places = []
    for c in candidates:
        key = c.lower()
        if key in noise or key in seen:
            continue
        seen.add(key)
        places.append(c)

    if not places:
        return "", ""
    district = places[0]
    neighbourhood = places[-1] if len(places) > 1 else district
    return district, neighbourhood


def _extract_condition(item: dict) -> Optional[str]:
    """Pull a raw finishing/construction status if present in the item."""
    for key in ("constructionStatus", "construction_status", "state", "condition"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return _STATUS_MAP.get(val.strip().upper(), val.strip())
    return None


def _parse_item(item: dict, transaction_type: str, base_url: str) -> Optional[dict]:
    """Convert one Otodom ad item into a canonical listing dict."""
    from datetime import datetime

    slug = item.get("slug")
    url = item.get("url")
    if not url and slug:
        url = urljoin(base_url, f"/pl/oferta/{slug}")
    if not url:
        return None

    price = _num(item.get("totalPrice")) or _num(item.get("price"))
    area = _num(item.get("areaInSquareMeters")) or _num(item.get("area"))
    if not price or not area:
        return None

    district, neighbourhood = _extract_location(item)

    return {
        "url": url,
        "title": (item.get("title") or "").strip() or url,
        "transaction_type": transaction_type,
        "district": district,
        "neighbourhood": neighbourhood,
        "price_pln": price,
        "area_m2": area,
        "rooms": _rooms_to_int(item.get("roomsNumber")) or 1,
        "floor": _num(item.get("floorNumber")),
        "year_built": _num(item.get("buildYear") or item.get("yearBuilt")),
        "finishing_condition": _extract_condition(item),
        "lat": _num((item.get("location") or {}).get("coordinates", {}).get("latitude")),
        "lng": _num((item.get("location") or {}).get("coordinates", {}).get("longitude")),
        "scraped_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Playwright-driven data source
# ---------------------------------------------------------------------------

class PlaywrightOtodomDataSource(DataSource):
    """Scrapes Rzeszów sale + rent flats from Otodom via headless Chromium."""

    def __init__(self) -> None:
        from app.config import get_settings

        settings = get_settings()
        self._base_url = settings.OTODOM_BASE_URL
        self._delay = settings.REQUEST_DELAY_S
        self._user_agent = settings.USER_AGENT
        self._max_pages = getattr(settings, "OTODOM_MAX_PAGES", 5)

    async def fetch_listings(self) -> List[dict]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error(
                "Playwright is not installed. Run: "
                "pip install -r requirements-scraper.txt && playwright install chromium"
            )
            return []

        results: List[dict] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self._user_agent,
                locale="pl-PL",
                viewport={"width": 1366, "height": 900},
            )
            page = await context.new_page()
            try:
                results.extend(await self._scrape_path(page, _SALE_PATH, "sale"))
                results.extend(await self._scrape_path(page, _RENT_PATH, "rent"))
            finally:
                await context.close()
                await browser.close()

        logger.info("Playwright scraper collected %d listings.", len(results))
        return results

    async def _scrape_path(self, page, path: str, transaction_type: str) -> List[dict]:
        listings: List[dict] = []
        base = urljoin(self._base_url, path)

        for page_no in range(1, self._max_pages + 1):
            url = f"{base}?page={page_no}" if page_no > 1 else base
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_selector("script#__NEXT_DATA__", timeout=15_000)
                html = await page.content()
            except Exception as exc:  # noqa: BLE001 - log and stop this path
                logger.error("Failed to load %s (page %d): %s", path, page_no, exc)
                break

            items = _find_listing_items(_extract_next_data(html))
            if not items:
                logger.info("No items on %s page %d; stopping.", path, page_no)
                break

            parsed = [_parse_item(it, transaction_type, self._base_url) for it in items]
            parsed = [p for p in parsed if p]
            listings.extend(parsed)
            logger.info("%s page %d: %d listings parsed.", path, page_no, len(parsed))

            await asyncio.sleep(self._delay)

        return listings
