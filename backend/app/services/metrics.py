from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from app.enums import FinishingCondition


@dataclass
class NeighbourhoodStats:
    median_sale_price_per_m2: float
    mean_rent_per_m2: float
    sale_count: int
    rent_count: int


@dataclass
class ListingMetrics:
    price_per_m2: float
    reno_cost: float
    all_in_cost: float
    all_in_price_per_m2: float
    discount_pct: float
    est_monthly_rent: float
    gross_yield_pct: float
    net_yield_pct: float
    deal_score: float = 0.0


# ---------------------------------------------------------------------------
# Renovation cost
# ---------------------------------------------------------------------------

def compute_reno_cost(condition: str, area_m2: float, config) -> float:
    cond = condition.lower() if isinstance(condition, str) else condition
    if cond in (FinishingCondition.READY, FinishingCondition.READY.value, "ready"):
        return config.RENO_COST_READY * area_m2
    if cond in (FinishingCondition.FINISHING, FinishingCondition.FINISHING.value, "finishing"):
        return config.RENO_COST_FINISHING * area_m2
    if cond in (FinishingCondition.RENOVATION, FinishingCondition.RENOVATION.value, "renovation"):
        return config.RENO_COST_RENOVATION * area_m2
    return config.RENO_COST_RENOVATION * area_m2


# ---------------------------------------------------------------------------
# IQR outlier removal
# ---------------------------------------------------------------------------

def _remove_outliers(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = statistics.median(sorted_v[: n // 2])
    q3 = statistics.median(sorted_v[(n + 1) // 2 :])
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    return [v for v in values if lo <= v <= hi]


# ---------------------------------------------------------------------------
# Neighbourhood stats
# ---------------------------------------------------------------------------

def compute_neighbourhood_stats(
    listings: list[dict], min_comps: int = 5
) -> dict[str, NeighbourhoodStats]:
    sale_by_neighbourhood: dict[str, list[float]] = {}
    sale_by_district: dict[str, list[float]] = {}
    rent_by_neighbourhood: dict[str, list[float]] = {}
    rent_by_district: dict[str, list[float]] = {}

    nbhd_to_district: dict[str, str] = {}

    for lst in listings:
        tt = (lst.get("transaction_type") or "").lower()
        area = float(lst.get("area_m2") or 0)
        price = float(lst.get("price_pln") or 0)
        if area <= 0 or price <= 0:
            continue
        nbhd = (lst.get("neighbourhood") or "").strip()
        dist = (lst.get("district") or "").strip()
        ppm2 = price / area

        if nbhd and dist:
            nbhd_to_district[nbhd] = dist

        if tt == "sale":
            sale_by_neighbourhood.setdefault(nbhd, []).append(ppm2)
            sale_by_district.setdefault(dist, []).append(ppm2)
        elif tt == "rent":
            rent_by_neighbourhood.setdefault(nbhd, []).append(ppm2)
            rent_by_district.setdefault(dist, []).append(ppm2)

    result: dict[str, NeighbourhoodStats] = {}

    def _median_m2(values: list[float]) -> float:
        cleaned = _remove_outliers(values)
        return statistics.median(cleaned) if cleaned else 0.0

    def _mean_m2(values: list[float]) -> float:
        cleaned = _remove_outliers(values)
        return statistics.mean(cleaned) if cleaned else 0.0

    all_nbhds = set(sale_by_neighbourhood) | set(rent_by_neighbourhood)
    all_dists = set(sale_by_district) | set(rent_by_district)

    for nbhd in all_nbhds:
        sale_vals = sale_by_neighbourhood.get(nbhd, [])
        use_district = len(sale_vals) < min_comps

        if use_district:
            dist_key = nbhd_to_district.get(nbhd, "")
            sale_vals_eff = sale_by_district.get(dist_key, sale_vals)
        else:
            sale_vals_eff = sale_vals

        rent_vals = rent_by_neighbourhood.get(nbhd, [])
        clean_sale = _remove_outliers(sale_vals_eff)
        clean_rent = _remove_outliers(rent_vals)

        result[nbhd] = NeighbourhoodStats(
            median_sale_price_per_m2=statistics.median(clean_sale) if clean_sale else 0.0,
            mean_rent_per_m2=statistics.mean(clean_rent) if clean_rent else 0.0,
            sale_count=len(clean_sale),
            rent_count=len(clean_rent),
        )

    for dist in all_dists:
        if dist not in result:
            sale_vals = sale_by_district.get(dist, [])
            rent_vals = rent_by_district.get(dist, [])
            clean_sale = _remove_outliers(sale_vals)
            clean_rent = _remove_outliers(rent_vals)
            result[dist] = NeighbourhoodStats(
                median_sale_price_per_m2=statistics.median(clean_sale) if clean_sale else 0.0,
                mean_rent_per_m2=statistics.mean(clean_rent) if clean_rent else 0.0,
                sale_count=len(clean_sale),
                rent_count=len(clean_rent),
            )

    return result


# ---------------------------------------------------------------------------
# Per-listing metrics
# ---------------------------------------------------------------------------

def compute_listing_metrics(
    listing: dict, stats: NeighbourhoodStats, config
) -> ListingMetrics:
    area = float(listing.get("area_m2") or 0)
    price = float(listing.get("price_pln") or 0)
    condition = (listing.get("finishing_condition") or "unknown")

    price_per_m2 = price / area if area > 0 else 0.0

    reno_cost = compute_reno_cost(condition, area, config)
    all_in_cost = price + reno_cost
    all_in_price_per_m2 = all_in_cost / area if area > 0 else 0.0

    median_sale = stats.median_sale_price_per_m2
    discount_pct = (
        (median_sale - all_in_price_per_m2) / median_sale * 100
        if median_sale > 0
        else 0.0
    )

    mean_rent_pm2 = stats.mean_rent_per_m2
    est_monthly_rent = mean_rent_pm2 * area if mean_rent_pm2 > 0 else 0.0

    gross_yield_pct = (
        est_monthly_rent * 12 / all_in_cost * 100 if all_in_cost > 0 else 0.0
    )

    net_monthly = est_monthly_rent * (1 - config.VACANCY_RATE) * (1 - config.ANNUAL_COSTS_RATE)
    net_yield_pct = (
        net_monthly * 12 / all_in_cost * 100 if all_in_cost > 0 else 0.0
    )

    return ListingMetrics(
        price_per_m2=price_per_m2,
        reno_cost=reno_cost,
        all_in_cost=all_in_cost,
        all_in_price_per_m2=all_in_price_per_m2,
        discount_pct=discount_pct,
        est_monthly_rent=est_monthly_rent,
        gross_yield_pct=gross_yield_pct,
        net_yield_pct=net_yield_pct,
        deal_score=0.0,
    )


# ---------------------------------------------------------------------------
# Normalization & scoring
# ---------------------------------------------------------------------------

def normalize_and_score(
    metrics_list: list[ListingMetrics], config
) -> list[ListingMetrics]:
    if not metrics_list:
        return metrics_list

    def _norm(values: list[float], invert: bool = False) -> list[float]:
        lo, hi = min(values), max(values)
        if hi == lo:
            return [0.5] * len(values)
        normed = [(v - lo) / (hi - lo) for v in values]
        if invert:
            normed = [1.0 - n for n in normed]
        return normed

    discounts = [m.discount_pct for m in metrics_list]
    yields = [m.net_yield_pct for m in metrics_list]
    prices = [m.all_in_price_per_m2 for m in metrics_list]

    norm_discounts = _norm(discounts)
    norm_yields = _norm(yields)
    norm_prices_inv = _norm(prices, invert=True)

    wd = config.SCORE_WEIGHT_DISCOUNT
    wy = config.SCORE_WEIGHT_YIELD
    wp = config.SCORE_WEIGHT_PRICE

    for i, m in enumerate(metrics_list):
        m.deal_score = (
            wd * norm_discounts[i]
            + wy * norm_yields[i]
            + wp * norm_prices_inv[i]
        )

    return metrics_list
