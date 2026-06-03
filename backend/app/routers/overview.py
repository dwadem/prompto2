from __future__ import annotations

import statistics
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.listing import FinishingCondition, Listing, TransactionType
from app.schemas.listing import ConditionBreakdown, DistrictOverviewResponse
from app.services.metrics import (
    NeighbourhoodStats,
    compute_listing_metrics,
    compute_neighbourhood_stats,
    normalize_and_score,
)

router = APIRouter(prefix="/api", tags=["overview"])


def _listing_to_dict(lst: Listing) -> dict:
    return {
        "id": lst.id,
        "url": lst.url,
        "title": lst.title,
        "transaction_type": lst.transaction_type.value if lst.transaction_type else "sale",
        "district": lst.district,
        "neighbourhood": lst.neighbourhood,
        "price_pln": lst.price_pln,
        "area_m2": lst.area_m2,
        "rooms": lst.rooms,
        "floor": lst.floor,
        "year_built": lst.year_built,
        "finishing_condition": lst.finishing_condition.value if lst.finishing_condition else "unknown",
        "lat": lst.lat,
        "lng": lst.lng,
        "scraped_at": lst.scraped_at,
    }


@router.get("/overview", response_model=list[DistrictOverviewResponse])
def get_overview(db: Session = Depends(get_db)):
    settings = get_settings()
    included_conditions = {c.lower() for c in settings.INCLUDED_CONDITIONS}

    all_listings = db.query(Listing).all()
    all_dicts = [_listing_to_dict(lst) for lst in all_listings]
    stats_map = compute_neighbourhood_stats(all_dicts)

    # Filter to sale listings with included conditions
    valid_conditions = {
        FinishingCondition(c) for c in included_conditions
        if c in FinishingCondition._value2member_map_
    }
    sale_listings = [
        lst for lst in all_listings
        if lst.transaction_type == TransactionType.SALE
        and lst.finishing_condition in valid_conditions
    ]

    # Compute metrics for all sale listings
    sale_dicts = [_listing_to_dict(lst) for lst in sale_listings]
    metrics_list = []
    for d in sale_dicts:
        nbhd = d["neighbourhood"]
        dist = d["district"]
        nbhd_stats = stats_map.get(nbhd) or stats_map.get(dist)
        if nbhd_stats is None:
            nbhd_stats = NeighbourhoodStats(
                median_sale_price_per_m2=d["price_pln"] / max(d["area_m2"], 1),
                mean_rent_per_m2=0.0,
                sale_count=1,
                rent_count=0,
            )
        m = compute_listing_metrics(d, nbhd_stats, settings)
        metrics_list.append(m)

    if metrics_list:
        normalize_and_score(metrics_list, settings)

    # Group by district
    district_sale_price_m2: dict[str, list[float]] = defaultdict(list)
    district_rent_price_m2: dict[str, list[float]] = defaultdict(list)
    district_net_yields: dict[str, list[float]] = defaultdict(list)
    district_condition_prices: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for i, lst in enumerate(sale_listings):
        dist = lst.district
        d = sale_dicts[i]
        m = metrics_list[i]
        area = d["area_m2"]
        price_m2 = d["price_pln"] / area if area > 0 else 0
        district_sale_price_m2[dist].append(price_m2)
        district_net_yields[dist].append(m.net_yield_pct)
        cond = d["finishing_condition"]
        district_condition_prices[dist][cond].append(price_m2)

    # Rent listings by district
    for lst in all_listings:
        if lst.transaction_type != TransactionType.RENT:
            continue
        d = _listing_to_dict(lst)
        area = d["area_m2"]
        if area <= 0:
            continue
        rent_m2 = d["price_pln"] / area
        district_rent_price_m2[lst.district].append(rent_m2)

    # Build response
    all_districts = sorted(
        set(district_sale_price_m2.keys()) | set(district_rent_price_m2.keys())
    )

    responses = []
    for dist in all_districts:
        sale_prices = district_sale_price_m2.get(dist, [])
        rent_prices = district_rent_price_m2.get(dist, [])
        net_yields = district_net_yields.get(dist, [])

        mean_sale = statistics.mean(sale_prices) if sale_prices else 0.0
        mean_rent = statistics.mean(rent_prices) if rent_prices else 0.0
        avg_yield = statistics.mean(net_yields) if net_yields else 0.0

        by_condition: list[ConditionBreakdown] = []
        for cond, prices in district_condition_prices.get(dist, {}).items():
            by_condition.append(
                ConditionBreakdown(
                    condition=cond,
                    count=len(prices),
                    mean_price_per_m2=statistics.mean(prices) if prices else 0.0,
                )
            )

        responses.append(
            DistrictOverviewResponse(
                district=dist,
                mean_price_per_m2=mean_sale,
                mean_rent_per_m2=mean_rent,
                avg_net_yield=avg_yield,
                listing_count=len(sale_prices),
                by_condition=by_condition,
            )
        )

    return responses


@router.get("/districts", response_model=list[str])
def get_districts(db: Session = Depends(get_db)):
    """Return a sorted list of distinct districts present in the database."""
    rows = db.query(Listing.district).distinct().order_by(Listing.district).all()
    return [row[0] for row in rows if row[0]]
