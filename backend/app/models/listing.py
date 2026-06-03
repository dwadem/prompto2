from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.enums import FinishingCondition, TransactionType


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType), nullable=False
    )
    district: Mapped[str] = mapped_column(String, nullable=False, default="")
    neighbourhood: Mapped[str] = mapped_column(String, nullable=False, default="")
    price_pln: Mapped[float] = mapped_column(Float, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    finishing_condition: Mapped[FinishingCondition] = mapped_column(
        SAEnum(FinishingCondition), nullable=False, default=FinishingCondition.UNKNOWN
    )
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
