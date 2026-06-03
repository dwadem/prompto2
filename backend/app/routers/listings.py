from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.listing import FinishingCondition, Listing, TransactionType
from app.schemas.listing import ListingDetailResponse, ListingResponse, NeighbourhoodStatsResponse
from app.services.metrics import (
    NeighbourhoodStats,
    compute_listing_metrics,
    compute_neighbourhood_stats,
    normalize_and_score,
)

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _listing_to_dict(lst: Listing) -> dict:
    """Convert an ORM Listing to a plain dict for metrics computation."""
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


def _build_listing_response(lst: Listing, metrics, extra: dict | None = None) -> dict:
    """Merge ORM fields + computed metrics into a response dict."""
    base = _listing_to_dict(lst)
    base.update({
        "price_per_m2": metrics.price_per_m2,
        "reno_cost": metrics.reno_cost,
        "all_in_cost": metrics.all_in_cost,
        "all_in_price_per_m2": metrics.all_in_price_per_m2,
        "discount_pct": metrics.discount_pct,
        "est_monthly_rent": metrics.est_monthly_rent,
        "gross_yield_pct": metrics.gross_yield_pct,
        "net_yield_pct": metrics.net_yield_pct,
        "deal_score": metrics.deal_score,
    })
    if extra:
        base.update(extra)
    return base


@router.get("", response_model=list[ListingResponse])
def list_listings(
    district: Optional[str] = Query(None),
    finishing_condition: list[str] = Query(default=[]),
    max_price: Optional[float] = Query(None),
    max_all_in_cost: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    min_rooms: Optional[int] = Query(None),
    min_net_yield: Optional[float] = Query(None),
    min_discount: Optional[float] = Query(None),
    sort_by: str = Query("deal_score"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    included_conditions = {c.lower() for c in settings.INCLUDED_CONDITIONS}

    # 1. Load all listings (sale + rent) for neighbourhood stats computation
    all_listings = db.query(Listing).all()
    all_dicts = [_listing_to_dict(lst) for lst in all_listings]
    stats_map = compute_neighbourhood_stats(all_dicts)

    # 2. Load SALE listings filtered by INCLUDED_CONDITIONS
    sale_q = db.query(Listing).filter(Listing.transaction_type == TransactionType.SALE)

    # Filter by included conditions
    valid_conditions = [
        FinishingCondition(c) for c in included_conditions if c in FinishingCondition._value2member_map_
    ]
    if valid_conditions:
        sale_q = sale_q.filter(Listing.finishing_condition.in_(valid_conditions))

    # Apply pre-compute filters
    if district:
        sale_q = sale_q.filter(Listing.district == district)
    if finishing_condition:
        fc_enums = [
            FinishingCondition(c) for c in finishing_condition
            if c in FinishingCondition._value2member_map_
        ]
        if fc_enums:
            sale_q = sale_q.filter(Listing.finishing_condition.in_(fc_enums))
    if max_price is not None:
        sale_q = sale_q.filter(Listing.price_pln <= max_price)
    if min_area is not None:
        sale_q = sale_q.filter(Listing.area_m2 >= min_area)
    if min_rooms is not None:
        sale_q = sale_q.filter(Listing.rooms >= min_rooms)

    sale_listings = sale_q.all()

    # 3. Compute metrics for each listing
    metrics_list = []
    listings_with_metrics = []

    for lst in sale_listings:
        d = _listing_to_dict(lst)
        nbhd = d["neighbourhood"]
        dist = d["district"]
        # Try neighbourhood first, fallback to district
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
        listings_with_metrics.append((lst, nbhd_stats))

    # 4. Normalize & score
    normalize_and_score(metrics_list, settings)

    # 5. Apply post-compute filters
    filtered = []
    for i, (lst, nbhd_stats) in enumerate(listings_with_metrics):
        m = metrics_list[i]
        if min_net_yield is not None and m.net_yield_pct < min_net_yield:
            continue
        if min_discount is not None and m.discount_pct < min_discount:
            continue
        if max_all_in_cost is not None and m.all_in_cost > max_all_in_cost:
            continue
        filtered.append((lst, m))

    # 6. Sort
    sort_field_map = {
        "deal_score": lambda x: x[1].deal_score,
        "net_yield_pct": lambda x: x[1].net_yield_pct,
        "gross_yield_pct": lambda x: x[1].gross_yield_pct,
        "discount_pct": lambda x: x[1].discount_pct,
        "price_pln": lambda x: x[0].price_pln,
        "all_in_cost": lambda x: x[1].all_in_cost,
        "area_m2": lambda x: x[0].area_m2,
        "all_in_price_per_m2": lambda x: x[1].all_in_price_per_m2,
    }
    key_fn = sort_field_map.get(sort_by, lambda x: x[1].deal_score)
    reverse = sort_dir.lower() != "asc"
    filtered.sort(key=key_fn, reverse=reverse)

    return [
        ListingResponse(**_build_listing_response(lst, m))
        for lst, m in filtered
    ]


@router.get("/{listing_id}", response_model=ListingDetailResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    settings = get_settings()

    lst = db.query(Listing).filter(Listing.id == listing_id).first()
    if lst is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Compute neighbourhood stats using all listings
    all_listings = db.query(Listing).all()
    all_dicts = [_listing_to_dict(l) for l in all_listings]
    stats_map = compute_neighbourhood_stats(all_dicts)

    d = _listing_to_dict(lst)
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
    # Single listing: normalize_and_score with one element (score will be 0.5 for all equal)
    normalize_and_score([m], settings)

    stats_response = NeighbourhoodStatsResponse(
        median_sale_price_per_m2=nbhd_stats.median_sale_price_per_m2,
        mean_rent_per_m2=nbhd_stats.mean_rent_per_m2,
        sale_count=nbhd_stats.sale_count,
        rent_count=nbhd_stats.rent_count,
    )

    response_dict = _build_listing_response(lst, m, extra={"neighbourhood_stats": stats_response})
    return ListingDetailResponse(**response_dict)
