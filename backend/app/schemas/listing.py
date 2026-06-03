from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    transaction_type: str
    district: str
    neighbourhood: str
    price_pln: float
    area_m2: float
    rooms: int
    floor: Optional[int]
    year_built: Optional[int]
    finishing_condition: str
    lat: Optional[float]
    lng: Optional[float]
    scraped_at: datetime

    # computed metrics
    price_per_m2: float
    reno_cost: float
    all_in_cost: float
    all_in_price_per_m2: float
    discount_pct: float
    est_monthly_rent: float
    gross_yield_pct: float
    net_yield_pct: float
    deal_score: float


class NeighbourhoodStatsResponse(BaseModel):
    median_sale_price_per_m2: float
    mean_rent_per_m2: float
    sale_count: int
    rent_count: int


class ListingDetailResponse(ListingResponse):
    neighbourhood_stats: NeighbourhoodStatsResponse


class ConditionBreakdown(BaseModel):
    condition: str
    count: int
    mean_price_per_m2: float


class DistrictOverviewResponse(BaseModel):
    district: str
    mean_price_per_m2: float
    mean_rent_per_m2: float
    avg_net_yield: float
    listing_count: int
    by_condition: List[ConditionBreakdown]
