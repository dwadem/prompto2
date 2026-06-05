from __future__ import annotations

import csv
import io
import json
import logging
import os
from typing import List

from app.datasources.base import DataSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Field-name aliasing
# ---------------------------------------------------------------------------
# Real-world exports (spreadsheets, Otodom CSV dumps, scraped JSON) use varied
# column names, in English or Polish. Map them all to the canonical keys the
# ingestion service expects. Keys here are lower-cased; matching is exact after
# lower-casing and stripping surrounding whitespace.
_FIELD_ALIASES: dict[str, str] = {
    # url
    "link": "url",
    "href": "url",
    "listing_url": "url",
    "adres_url": "url",
    # title
    "name": "title",
    "nazwa": "title",
    "tytul": "title",
    "tytuł": "title",
    # transaction type
    "type": "transaction_type",
    "typ": "transaction_type",
    "transaction": "transaction_type",
    "oferta": "transaction_type",
    "rodzaj_oferty": "transaction_type",
    # district
    "dzielnica": "district",
    # neighbourhood
    "neighborhood": "neighbourhood",
    "osiedle": "neighbourhood",
    "okolica": "neighbourhood",
    # price
    "price": "price_pln",
    "price_zl": "price_pln",
    "cena": "price_pln",
    "cena_pln": "price_pln",
    "cena_zl": "price_pln",
    # area
    "area": "area_m2",
    "area_sqm": "area_m2",
    "m2": "area_m2",
    "metraz": "area_m2",
    "metraż": "area_m2",
    "powierzchnia": "area_m2",
    "surface": "area_m2",
    # rooms
    "room": "rooms",
    "rooms_count": "rooms",
    "number_of_rooms": "rooms",
    "pokoje": "rooms",
    "liczba_pokoi": "rooms",
    # floor
    "pietro": "floor",
    "piętro": "floor",
    "floor_number": "floor",
    # year built
    "year": "year_built",
    "built_year": "year_built",
    "rok": "year_built",
    "rok_budowy": "year_built",
    # finishing condition
    "condition": "finishing_condition",
    "finishing": "finishing_condition",
    "stan": "finishing_condition",
    "stan_wykonczenia": "finishing_condition",
    "stan_wykończenia": "finishing_condition",
    # coordinates
    "latitude": "lat",
    "szerokosc": "lat",
    "lon": "lng",
    "long": "lng",
    "longitude": "lng",
    "dlugosc": "lng",
    # timestamp
    "scraped": "scraped_at",
    "date": "scraped_at",
    "data": "scraped_at",
}

# Fields whose values may arrive as messy numeric strings ("450 000 zł",
# "62,5 m²") and need cleaning before float()/int() conversion downstream.
_NUMERIC_FIELDS = {"price_pln", "area_m2", "rooms", "floor", "year_built", "lat", "lng"}


def _normalize_keys(record: dict) -> dict:
    """Remap aliased keys to canonical keys without clobbering existing ones."""
    out: dict = {}
    for key, value in record.items():
        if not isinstance(key, str):
            out[key] = value
            continue
        canonical = _FIELD_ALIASES.get(key.strip().lower(), key.strip())
        # Don't overwrite a canonical key that's already populated.
        if canonical in out and out[canonical] not in (None, ""):
            continue
        out[canonical] = value
    return out


def _clean_number(value):
    """Turn a messy numeric string into a plain numeric string.

    "450 000 zł" -> "450000", "62,5 m²" -> "62.5". Leaves non-strings and
    already-clean values untouched. Returns None for empty strings.
    """
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text == "":
        return None
    # Drop thousands separators (spaces, incl. non-breaking) then convert a
    # decimal comma to a dot. Finally strip everything that isn't part of a
    # number, keeping a single leading minus.
    text = text.replace(" ", "").replace(" ", "")
    text = text.replace(",", ".")
    cleaned = []
    seen_dot = False
    for i, ch in enumerate(text):
        # ASCII digits only: str.isdigit() also matches "²", "½", etc.
        if ch in "0123456789":
            cleaned.append(ch)
        elif ch == "." and not seen_dot:
            cleaned.append(ch)
            seen_dot = True
        elif ch == "-" and i == 0:
            cleaned.append(ch)
    result = "".join(cleaned).rstrip(".")
    return result or None


def _clean_record(record: dict) -> dict:
    """Normalise keys, then clean numeric fields. Returns a new dict."""
    normalised = _normalize_keys(record)
    for field in _NUMERIC_FIELDS:
        if field in normalised:
            normalised[field] = _clean_number(normalised[field])
    return normalised


def _records_from_json(text: str) -> List[dict]:
    """Parse a JSON file: list, {"listings": [...]}, or a single object."""
    data = json.loads(text)
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        listings = data.get("listings")
        if isinstance(listings, list):
            return [r for r in listings if isinstance(r, dict)]
        return [data]
    return []


def _records_from_ndjson(text: str) -> List[dict]:
    """Parse newline-delimited JSON: one object per non-blank line."""
    records: List[dict] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("Skipping malformed NDJSON line %d: %s", line_no, exc)
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _records_from_csv(text: str) -> List[dict]:
    """Parse CSV with a header row into a list of dicts."""
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


class JsonCacheDataSource(DataSource):
    """Loads listings from cache files in DATA_DIR.

    Supported formats (by extension):
      - .json           : a list, a {"listings": [...]} object, or one object
      - .ndjson / .jsonl: newline-delimited JSON (one object per line)
      - .csv            : header row + one listing per row

    Records may use English or Polish column names (see _FIELD_ALIASES); keys
    are normalised and messy numeric strings ("450 000 zł") are cleaned before
    being handed to the ingestion service.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        if data_dir is None:
            # Imported lazily so the pure parsing helpers in this module stay
            # importable without pydantic-settings (e.g. in unit tests).
            from app.config import get_settings

            data_dir = get_settings().DATA_DIR
        self._data_dir = data_dir

    async def fetch_listings(self) -> List[dict]:
        combined: List[dict] = []

        if not os.path.isdir(self._data_dir):
            logger.warning("DATA_DIR %s does not exist; no listings loaded.", self._data_dir)
            return combined

        files_read = 0
        for filename in sorted(os.listdir(self._data_dir)):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in (".json", ".ndjson", ".jsonl", ".csv"):
                continue

            filepath = os.path.join(self._data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError as exc:
                logger.warning("Could not read %s: %s", filename, exc)
                continue

            try:
                if ext == ".csv":
                    raw_records = _records_from_csv(text)
                elif ext in (".ndjson", ".jsonl"):
                    raw_records = _records_from_ndjson(text)
                else:
                    raw_records = _records_from_json(text)
            except (json.JSONDecodeError, csv.Error) as exc:
                logger.warning("Skipping %s (parse error): %s", filename, exc)
                continue

            cleaned = [_clean_record(r) for r in raw_records]
            combined.extend(cleaned)
            files_read += 1
            logger.info("Loaded %d records from %s", len(cleaned), filename)

        # De-duplicate by URL, keeping the last occurrence (later files win).
        deduped: dict[str, dict] = {}
        no_url: List[dict] = []
        for rec in combined:
            url = (rec.get("url") or "").strip()
            if url:
                deduped[url] = rec
            else:
                no_url.append(rec)

        result = list(deduped.values()) + no_url
        logger.info(
            "json_cache: %d file(s), %d record(s), %d unique by URL.",
            files_read,
            len(combined),
            len(deduped),
        )
        return result
