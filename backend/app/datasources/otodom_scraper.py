from __future__ import annotations

# ToS compliance is the responsibility of the operator.
# Review https://www.otodom.pl/robots.txt and the site's Terms of Service
# before enabling this data source.  The robots.txt check below will
# short-circuit scraping if the root path is disallowed, but it is the
# operator's responsibility to ensure they are permitted to scrape.

import asyncio
import logging
from typing import List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.datasources.base import DataSource

logger = logging.getLogger(__name__)

_SALE_PATH = "/pl/wyniki/sprzedaz/mieszkanie/podkarpackie/rzeszow"
_RENT_PATH = "/pl/wyniki/wynajmu/mieszkanie/podkarpackie/rzeszow"
_MAX_PAGES = 5


class OtodomScraperDataSource(DataSource):
    """Scrapes sale and rent listings from Otodom for Rzeszów.

    Respects robots.txt (skips if Disallow: / is set) and throttles
    requests at REQUEST_DELAY_S seconds between each HTTP call.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.OTODOM_BASE_URL
        self._delay = self._settings.REQUEST_DELAY_S
        self._headers = {"User-Agent": self._settings.USER_AGENT}
        self._robots_checked = False
        self._scraping_allowed = True

    # ------------------------------------------------------------------
    # robots.txt enforcement
    # ------------------------------------------------------------------

    async def _check_robots(self, client: httpx.AsyncClient) -> bool:
        """Return True if scraping is permitted by robots.txt."""
        robots_url = urljoin(self._base_url, "/robots.txt")
        try:
            resp = await client.get(robots_url, timeout=10.0)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Could not fetch robots.txt (%s); allowing scraping.", exc)
            return True

        disallow_all = False
        in_relevant_agent = False

        for raw_line in resp.text.splitlines():
            line = raw_line.strip()
            if line.lower().startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                in_relevant_agent = agent in ("*", self._settings.USER_AGENT)
            elif in_relevant_agent and line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path == "/":
                    disallow_all = True
                    break

        return not disallow_all

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def fetch_listings(self) -> List[dict]:
        async with httpx.AsyncClient(headers=self._headers, follow_redirects=True) as client:
            if not self._robots_checked:
                self._scraping_allowed = await self._check_robots(client)
                self._robots_checked = True

            if not self._scraping_allowed:
                logger.warning(
                    "robots.txt disallows scraping %s; returning empty list.",
                    self._base_url,
                )
                return []

            results: List[dict] = []
            results.extend(await self._scrape_path(client, _SALE_PATH, "sale"))
            results.extend(await self._scrape_path(client, _RENT_PATH, "rent"))
            return results

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def _scrape_path(
        self, client: httpx.AsyncClient, path: str, transaction_type: str
    ) -> List[dict]:
        listings: List[dict] = []

        for page in range(1, _MAX_PAGES + 1):
            url = urljoin(self._base_url, path)
            params = {"page": page} if page > 1 else {}

            try:
                await asyncio.sleep(self._delay)
                resp = await client.get(url, params=params, timeout=15.0)
                resp.raise_for_status()
            except Exception as exc:
                logger.error("Failed to fetch page %d of %s: %s", page, path, exc)
                break

            page_listings = self._parse_listing_page(resp.text, transaction_type)
            if not page_listings:
                break  # no more results

            listings.extend(page_listings)

            if len(page_listings) < 10:
                break  # last partial page

        return listings

    # ------------------------------------------------------------------
    # HTML parsing  (selectors are Otodom-specific — update as needed)
    # ------------------------------------------------------------------

    def _parse_listing_page(self, html: str, transaction_type: str) -> List[dict]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-cy='listing-item']")  # TODO: verify selector against live HTML
        results: List[dict] = []

        for card in cards:
            try:
                listing = self._parse_card(card, transaction_type)
                if listing:
                    results.append(listing)
            except Exception as exc:
                logger.debug("Failed to parse card: %s", exc)

        return results

    def _parse_card(self, card: BeautifulSoup, transaction_type: str) -> dict | None:
        # TODO: Update CSS selectors once verified against live Otodom HTML.

        title_el = card.select_one("[data-cy='listing-item-title']")
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = card.select_one("a[href]")
        url = urljoin(self._base_url, link_el["href"]) if link_el else ""

        if not url:
            return None

        # Price
        price_el = card.select_one("[aria-label='Cena']")
        price_text = price_el.get_text(strip=True) if price_el else "0"
        price_pln = self._parse_number(price_text)

        # Area & rooms (commonly in a detail list)
        area_m2 = 0.0
        rooms = 1
        for detail in card.select("span[data-testid]"):
            text = detail.get_text(strip=True)
            if "m²" in text or "m2" in text:
                area_m2 = self._parse_number(text)
            elif "pok" in text.lower():
                rooms = int(self._parse_number(text)) or 1

        # Location / district from breadcrumb or location label
        location_el = card.select_one("[data-testid='listing-item-header-address-city-to-district']")
        location_text = location_el.get_text(strip=True) if location_el else ""
        parts = [p.strip() for p in location_text.split(",")]
        district = parts[1] if len(parts) > 1 else ""
        neighbourhood = parts[2] if len(parts) > 2 else district

        # Floor — often in a badge
        floor_el = card.select_one("[aria-label='Piętro']")
        floor: int | None = None
        if floor_el:
            floor = int(self._parse_number(floor_el.get_text(strip=True))) or None

        # Finishing condition
        condition_el = card.select_one("[aria-label='Stan wykończenia']")
        finishing_condition = condition_el.get_text(strip=True) if condition_el else "unknown"

        import datetime

        return {
            "url": url,
            "title": title,
            "transaction_type": transaction_type,
            "district": district,
            "neighbourhood": neighbourhood,
            "price_pln": price_pln,
            "area_m2": area_m2,
            "rooms": rooms,
            "floor": floor,
            "year_built": None,
            "finishing_condition": finishing_condition,
            "lat": None,
            "lng": None,
            "scraped_at": datetime.datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _parse_number(text: str) -> float:
        """Extract the first numeric value from a string."""
        import re

        cleaned = re.sub(r"[^\d,\.]", "", text).replace(",", ".")
        # keep only first numeric token
        match = re.search(r"\d+(?:\.\d+)?", cleaned)
        return float(match.group()) if match else 0.0
