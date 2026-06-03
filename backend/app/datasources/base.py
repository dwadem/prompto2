from __future__ import annotations

import abc
from typing import List


class DataSource(abc.ABC):
    """Abstract base class for all listing data sources."""

    @abc.abstractmethod
    async def fetch_listings(self) -> List[dict]:
        """Fetch and return a list of raw listing dicts."""
        ...
