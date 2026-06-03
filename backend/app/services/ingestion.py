from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import get_settings
from app.datasources.base import DataSource
from app.models.listing import FinishingCondition, Listing, TransactionType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Finishing-condition normalisation map
# ---------------------------------------------------------------------------
# Keys are substrings (lower-cased) found in the raw data; values are enum members.
_CONDITION_MAP: list[tuple[str, FinishingCondition]] = [
    ("do zamieszkania", FinishingCondition.READY),
    ("pod klucz", FinishingCondition.READY),
    ("move-in", FinishingCondition.READY),
    ("gotowe", FinishingCondition.READY),
    ("ready", FinishingCondition.READY),
    ("do wykończenia", FinishingCondition.FINISHING),
    ("do wykonczenia", FinishingCondition.FINISHING),  # without Polish diacritics
    ("stan deweloperski", FinishingCondition.FINISHING),
    ("deweloperski", FinishingCondition.FINISHING),
    ("developer", FinishingCondition.FINISHING),
    ("finishing", FinishingCondition.FINISHING),
    ("do remontu", FinishingCondition.RENOVATION),
    ("wymaga remontu", FinishingCondition.RENOVATION),
    ("remont", FinishingCondition.RENOVATION),
    ("renovation", FinishingCondition.RENOVATION),
]


def _parse_condition(raw: str | None) -> FinishingCondition:
    """Map a raw finishing-condition string to a FinishingCondition enum value."""
    if not raw:
        return FinishingCondition.UNKNOWN
    lower = raw.lower().strip()
    for pattern, cond in _CONDITION_MAP:
        if pattern in lower:
            return cond
    return FinishingCondition.UNKNOWN


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------


class IngestService:
    """Pulls listings from a DataSource and upserts them into the database."""

    def __init__(self, datasource: DataSource, db: Session) -> None:
        self._datasource = datasource
        self._db = db
        self._settings = get_settings()

    async def run(self) -> int:
        """Fetch + upsert all listings. Returns the number of rows upserted."""
        raw_listings = await self._datasource.fetch_listings()
        included = {c.lower() for c in self._settings.INCLUDED_CONDITIONS}
        upserted = 0

        for raw in raw_listings:
            condition = _parse_condition(raw.get("finishing_condition"))

            # Filter by configured included conditions
            if condition.value not in included:
                continue

            url = (raw.get("url") or "").strip()
            if not url:
                logger.debug("Skipping listing with no URL.")
                continue

            # Parse transaction type
            tt_raw = (raw.get("transaction_type") or "sale").lower()
            try:
                transaction_type = TransactionType(tt_raw)
            except ValueError:
                transaction_type = TransactionType.SALE

            # Parse scraped_at
            scraped_at_raw = raw.get("scraped_at")
            if isinstance(scraped_at_raw, datetime):
                scraped_at = scraped_at_raw
            elif isinstance(scraped_at_raw, str):
                try:
                    scraped_at = datetime.fromisoformat(scraped_at_raw)
                except ValueError:
                    scraped_at = datetime.utcnow()
            else:
                scraped_at = datetime.utcnow()

            # Build attribute dict
            attrs: dict = {
                "url": url,
                "title": (raw.get("title") or "").strip() or url,
                "transaction_type": transaction_type,
                "district": (raw.get("district") or "").strip(),
                "neighbourhood": (raw.get("neighbourhood") or "").strip(),
                "price_pln": float(raw.get("price_pln") or 0),
                "area_m2": float(raw.get("area_m2") or 0),
                "rooms": int(raw.get("rooms") or 1),
                "floor": _safe_int(raw.get("floor")),
                "year_built": _safe_int(raw.get("year_built")),
                "finishing_condition": condition,
                "lat": _safe_float(raw.get("lat")),
                "lng": _safe_float(raw.get("lng")),
                "scraped_at": scraped_at,
            }

            existing: Listing | None = (
                self._db.query(Listing).filter(Listing.url == url).first()
            )
            if existing is not None:
                for key, value in attrs.items():
                    setattr(existing, key, value)
            else:
                self._db.add(Listing(**attrs))

            upserted += 1

        self._db.commit()
        logger.info("Ingestion complete: %d listings upserted.", upserted)
        return upserted


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
