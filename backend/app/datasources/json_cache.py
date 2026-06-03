from __future__ import annotations

import json
import os
from typing import List

from app.config import get_settings
from app.datasources.base import DataSource


class JsonCacheDataSource(DataSource):
    """Loads listings from all *.json files in the configured DATA_DIR.

    Each file may be either:
    - A JSON array (list) of listing dicts, or
    - A JSON object with a "listings" key whose value is a list of listing dicts.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        self._data_dir = data_dir or settings.DATA_DIR

    async def fetch_listings(self) -> List[dict]:
        combined: List[dict] = []

        if not os.path.isdir(self._data_dir):
            return combined

        for filename in sorted(os.listdir(self._data_dir)):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self._data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue

            if isinstance(data, list):
                combined.extend(data)
            elif isinstance(data, dict) and "listings" in data:
                listings = data["listings"]
                if isinstance(listings, list):
                    combined.extend(listings)

        return combined
