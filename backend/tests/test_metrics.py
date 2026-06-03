"""Unit tests for metrics.py — hand-checked numbers, stdlib only (pytest-compatible too)."""
from __future__ import annotations

import math
import sys
import os
import unittest

# Make sure app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from types import SimpleNamespace

from app.services.metrics import (
    ListingMetrics,
    NeighbourhoodStats,
    _remove_outliers,
    compute_listing_metrics,
    compute_neighbourhood_stats,
    compute_reno_cost,
    normalize_and_score,
)


def approx(a, b, rel=1e-5):
    """Return True if a ≈ b within relative tolerance."""
    return math.isclose(a, b, rel_tol=rel)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_config(**kw):
    defaults = dict(
        RENO_COST_READY=0.0,
        RENO_COST_FINISHING=1800.0,
        RENO_COST_RENOVATION=2800.0,
        VACANCY_RATE=0.08,
        ANNUAL_COSTS_RATE=0.20,
        SCORE_WEIGHT_DISCOUNT=0.5,
        SCORE_WEIGHT_YIELD=0.4,
        SCORE_WEIGHT_PRICE=0.1,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def make_listing(
    district="Testowo",
    neighbourhood="Testowo",
    price_pln=400000.0,
    area_m2=50.0,
    rooms=2,
    condition="do zamieszkania",
    transaction_type="sale",
    url_suffix="1",
):
    return {
        "id": 1,
        "url": f"http://example.com/{url_suffix}",
        "title": "Test listing",
        "transaction_type": transaction_type,
        "district": district,
        "neighbourhood": neighbourhood,
        "price_pln": price_pln,
        "area_m2": area_m2,
        "rooms": rooms,
        "floor": 1,
        "year_built": 2000,
        "finishing_condition": condition,
        "lat": None,
        "lng": None,
        "scraped_at": "2024-01-01T00:00:00",
    }


def make_stats(median_sale=7500.0, mean_rent=42.0, sale_count=6, rent_count=3):
    return NeighbourhoodStats(
        median_sale_price_per_m2=median_sale,
        mean_rent_per_m2=mean_rent,
        sale_count=sale_count,
        rent_count=rent_count,
    )


def make_metrics(discount, net_yield, price_per_m2):
    return ListingMetrics(
        price_per_m2=price_per_m2,
        reno_cost=0.0,
        all_in_cost=price_per_m2 * 50,
        all_in_price_per_m2=price_per_m2,
        discount_pct=discount,
        est_monthly_rent=2000.0,
        gross_yield_pct=net_yield + 1,
        net_yield_pct=net_yield,
        deal_score=0.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRenoCost(unittest.TestCase):

    def test_reno_cost_ready_area50(self):
        """READY: 0 PLN/m² × 50 m² = 0."""
        assert compute_reno_cost("ready", 50.0, mock_config()) == 0.0

    def test_reno_cost_finishing_area50(self):
        """FINISHING: 1800 PLN/m² × 50 m² = 90 000."""
        assert compute_reno_cost("finishing", 50.0, mock_config()) == 90_000.0

    def test_reno_cost_renovation_area50(self):
        """RENOVATION: 2800 PLN/m² × 50 m² = 140 000."""
        assert compute_reno_cost("renovation", 50.0, mock_config()) == 140_000.0

    def test_reno_cost_enum_values_accepted(self):
        """compute_reno_cost accepts the canonical enum string values."""
        cfg = mock_config()
        assert compute_reno_cost("ready", 40.0, cfg) == 0.0
        assert approx(compute_reno_cost("finishing", 40.0, cfg), 72_000.0)
        assert approx(compute_reno_cost("renovation", 40.0, cfg), 112_000.0)


class TestRemoveOutliers(unittest.TestCase):

    def test_passthrough_small_list(self):
        values = [1.0, 100.0, 200.0]
        assert _remove_outliers(values) == values

    def test_removes_extreme_value(self):
        """30000 is way above IQR boundary of cluster [7000-7500]."""
        vals = [7000.0, 7200.0, 7300.0, 7400.0, 7500.0, 30000.0]
        cleaned = _remove_outliers(vals)
        assert 30000.0 not in cleaned
        assert len(cleaned) == 5


class TestNeighbourhoodStats(unittest.TestCase):

    def test_basic_median_six_listings(self):
        """6 sale listings → median = (7300+7400)/2 = 7350."""
        ppm2s = [7000, 7200, 7300, 7400, 7500, 7600]
        listings = [
            make_listing(price_pln=50 * p, area_m2=50.0, url_suffix=str(i),
                         neighbourhood="Alpha", district="Alpha")
            for i, p in enumerate(ppm2s)
        ]
        rent_listings = [
            make_listing(price_pln=2000, area_m2=50.0, transaction_type="rent",
                         url_suffix=f"r{i}", neighbourhood="Alpha", district="Alpha")
            for i in range(3)
        ]
        stats = compute_neighbourhood_stats(listings + rent_listings)
        self.assertIn("Alpha", stats)
        self.assertTrue(approx(stats["Alpha"].median_sale_price_per_m2, 7350.0))
        self.assertEqual(stats["Alpha"].sale_count, 6)

    def test_district_fallback_when_fewer_than_min_comps(self):
        """3 listings in neighbourhood → falls back to district median."""
        small_nbhd = [
            make_listing(price_pln=50 * 8000, area_m2=50.0, url_suffix=f"n{i}",
                         neighbourhood="Beta-Nord", district="Beta")
            for i in range(3)
        ]
        other_nbhd = [
            make_listing(price_pln=50 * 7000, area_m2=50.0, url_suffix=f"c{i}",
                         neighbourhood="Beta-Centrum", district="Beta")
            for i in range(3)
        ]
        stats = compute_neighbourhood_stats(small_nbhd + other_nbhd, min_comps=5)
        # District "Beta": 3 @ 8000 + 3 @ 7000 → median = 7500
        district_stats = stats.get("Beta")
        self.assertIsNotNone(district_stats)
        self.assertTrue(approx(district_stats.median_sale_price_per_m2, 7500.0, rel=1e-4))
        # Beta-Nord (3 listings < 5) uses district fallback → same median
        nbhd_stats = stats.get("Beta-Nord")
        self.assertIsNotNone(nbhd_stats)
        self.assertTrue(approx(nbhd_stats.median_sale_price_per_m2, 7500.0, rel=1e-4))

    def test_outlier_excluded_from_median(self):
        """Extreme outlier (30000 vs cluster ~7000-7500) excluded; median = 7300."""
        price_per_m2s = [7000, 7200, 7300, 7400, 7500, 30000]
        listings = [
            make_listing(price_pln=50 * p, area_m2=50.0, url_suffix=str(i),
                         neighbourhood="Gamma", district="Gamma")
            for i, p in enumerate(price_per_m2s)
        ]
        stats = compute_neighbourhood_stats(listings)
        self.assertIn("Gamma", stats)
        self.assertTrue(approx(stats["Gamma"].median_sale_price_per_m2, 7300.0))
        self.assertEqual(stats["Gamma"].sale_count, 5)

    def test_empty_returns_empty_dict(self):
        self.assertEqual(compute_neighbourhood_stats([]), {})


class TestListingMetrics(unittest.TestCase):

    def test_ready_flat_full_pipeline(self):
        """READY: reno=0, all-in = purchase price, verify every derived metric."""
        cfg = mock_config()
        # area=60, price=420000 → price/m²=7000; median=7500, rent=42/m²
        listing = make_listing(price_pln=420_000.0, area_m2=60.0, condition="ready")
        stats = make_stats(median_sale=7500.0, mean_rent=42.0)

        m = compute_listing_metrics(listing, stats, cfg)

        self.assertTrue(approx(m.price_per_m2, 7000.0))
        self.assertEqual(m.reno_cost, 0.0)
        self.assertTrue(approx(m.all_in_cost, 420_000.0))
        self.assertTrue(approx(m.all_in_price_per_m2, 7000.0))

        # discount_pct = (7500-7000)/7500*100 = 6.6667%
        expected_discount = 500.0 / 7500.0 * 100
        self.assertTrue(approx(m.discount_pct, expected_discount, rel=1e-5))

        # est_monthly_rent = 42 * 60 = 2520
        self.assertTrue(approx(m.est_monthly_rent, 2520.0))

        # gross_yield = 2520*12/420000*100
        expected_gross = 2520.0 * 12 / 420_000.0 * 100
        self.assertTrue(approx(m.gross_yield_pct, expected_gross))

        # net = 2520 * 0.92 * 0.80 * 12 / 420000 * 100
        expected_net = 2520.0 * 0.92 * 0.80 * 12 / 420_000.0 * 100
        self.assertTrue(approx(m.net_yield_pct, expected_net))

    def test_renovation_flat_all_in_includes_reno(self):
        """RENOVATION: reno=126000, all-in=326000; yield denom = all-in cost."""
        cfg = mock_config()
        listing = make_listing(price_pln=200_000.0, area_m2=45.0, condition="renovation")
        stats = make_stats(median_sale=7500.0, mean_rent=42.0)

        m = compute_listing_metrics(listing, stats, cfg)

        self.assertTrue(approx(m.reno_cost, 126_000.0))
        self.assertTrue(approx(m.all_in_cost, 326_000.0))
        self.assertTrue(approx(m.all_in_price_per_m2, 326_000.0 / 45.0))

        expected_discount = (7500.0 - 326_000.0 / 45.0) / 7500.0 * 100
        self.assertTrue(approx(m.discount_pct, expected_discount, rel=1e-5))

        # est_monthly_rent = 42 * 45 = 1890
        self.assertTrue(approx(m.est_monthly_rent, 1890.0))

        # net yield denominator = 326000
        net_monthly = 1890.0 * 0.92 * 0.80
        expected_net = net_monthly * 12 / 326_000.0 * 100
        self.assertTrue(approx(m.net_yield_pct, expected_net))

    def test_finishing_flat_reno_cost(self):
        """FINISHING: reno = 1800 * 50 = 90 000, all-in = 390 000."""
        cfg = mock_config()
        listing = make_listing(price_pln=300_000.0, area_m2=50.0, condition="finishing")
        stats = make_stats(median_sale=7500.0, mean_rent=42.0)

        m = compute_listing_metrics(listing, stats, cfg)

        self.assertTrue(approx(m.reno_cost, 90_000.0))
        self.assertTrue(approx(m.all_in_cost, 390_000.0))
        self.assertTrue(approx(m.all_in_price_per_m2, 390_000.0 / 50.0))


class TestNormalizeAndScore(unittest.TestCase):

    def _three_listings(self):
        return [
            make_metrics(discount=10, net_yield=7, price_per_m2=6000),
            make_metrics(discount=5,  net_yield=5, price_per_m2=7500),
            make_metrics(discount=2,  net_yield=3, price_per_m2=9000),
        ]

    def test_ranking_order_best_to_worst(self):
        """A (best on all axes) > B > C; A=1.0, C=0.0."""
        metrics = self._three_listings()
        normalize_and_score(metrics, mock_config())
        scores = [m.deal_score for m in metrics]
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[1], scores[2])
        self.assertTrue(approx(scores[0], 1.0))
        self.assertTrue(approx(scores[2], 0.0))

    def test_weight_formula_middle_listing(self):
        """Middle listing score = 0.5×0.375 + 0.4×0.5 + 0.1×0.5 = 0.4375."""
        metrics = self._three_listings()
        normalize_and_score(metrics, mock_config(
            w_discount=0.5, w_yield=0.4, w_price=0.1
        ))
        # norm_discount B = (5-2)/(10-2) = 0.375
        # norm_yield B   = (5-3)/(7-3)  = 0.5
        # norm_price_inv B = (9000-7500)/(9000-6000) = 0.5
        self.assertTrue(approx(metrics[1].deal_score, 0.4375))

    def test_single_listing_scores_half(self):
        """Single listing: lo==hi on all axes → score = 0.5."""
        m = make_metrics(discount=5.0, net_yield=5.0, price_per_m2=7000.0)
        normalize_and_score([m], mock_config())
        self.assertTrue(approx(m.deal_score, 0.5))

    def test_empty_list_returns_empty(self):
        self.assertEqual(normalize_and_score([], mock_config()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
