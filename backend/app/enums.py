"""Shared enums — no SQLAlchemy dependency so they can be imported by tests."""
from __future__ import annotations

import enum


class FinishingCondition(str, enum.Enum):
    READY = "ready"
    FINISHING = "finishing"
    RENOVATION = "renovation"
    UNKNOWN = "unknown"


class TransactionType(str, enum.Enum):
    SALE = "sale"
    RENT = "rent"
