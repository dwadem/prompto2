"""Unit tests for the Playwright scraper's pure parsing helpers.

These exercise the JSON -> canonical-dict transformation without launching a
browser or hitting the network (Playwright itself is never imported here).
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.datasources.playwright_scraper import (
    _extract_condition,
    _extract_location,
    _extract_next_data,
    _find_listing_items,
    _num,
    _parse_item,
    _rooms_to_int,
)

BASE = "https://www.otodom.pl"

# A trimmed-down fixture shaped like Otodom's __NEXT_DATA__ search payload.
_ITEM = {
    "id": 123,
    "title": "Mieszkanie 3 pokoje, Śródmieście",
    "slug": "mieszkanie-3-pokoje-srodmiescie-abc123",
    "transaction": "SELL",
    "totalPrice": {"value": 480000, "currency": "PLN"},
    "areaInSquareMeters": 52.0,
    "roomsNumber": "THREE",
    "floorNumber": 3,
    "buildYear": 2005,
    "constructionStatus": "READY_TO_USE",
    "location": {
        "coordinates": {"latitude": 50.0413, "longitude": 22.0047},
        "reverseGeocoding": {
            "locations": [
                {"name": "podkarpackie"},
                {"name": "Rzeszów"},
                {"name": "Śródmieście"},
                {"name": "Centrum"},
            ]
        },
    },
}

_NEXT_DATA = {"props": {"pageProps": {"data": {"searchAds": {"items": [_ITEM]}}}}}


class TestExtractNextData(unittest.TestCase):
    def test_extracts_json_from_script(self):
        html = (
            '<html><body><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(_NEXT_DATA)
            + "</script></body></html>"
        )
        self.assertEqual(_extract_next_data(html), _NEXT_DATA)

    def test_missing_script_returns_empty(self):
        self.assertEqual(_extract_next_data("<html></html>"), {})

    def test_malformed_json_returns_empty(self):
        html = '<script id="__NEXT_DATA__">{not valid}</script>'
        self.assertEqual(_extract_next_data(html), {})


class TestFindListingItems(unittest.TestCase):
    def test_known_path(self):
        self.assertEqual(_find_listing_items(_NEXT_DATA), [_ITEM])

    def test_recursive_fallback(self):
        # Items present but under an unexpected path.
        buried = {"a": {"b": {"weird": {"results": [_ITEM, _ITEM]}}}}
        found = _find_listing_items(buried)
        self.assertEqual(len(found), 2)

    def test_empty_when_nothing_listinglike(self):
        self.assertEqual(_find_listing_items({"foo": [{"bar": 1}]}), [])


class TestNum(unittest.TestCase):
    def test_int_float(self):
        self.assertEqual(_num(5), 5.0)
        self.assertEqual(_num(2.5), 2.5)

    def test_money_object(self):
        self.assertEqual(_num({"value": 480000, "currency": "PLN"}), 480000.0)

    def test_string(self):
        self.assertEqual(_num("450 000 zł"), 450000.0)
        self.assertEqual(_num("62,5"), 62.5)

    def test_bool_is_none(self):
        self.assertIsNone(_num(True))

    def test_junk_is_none(self):
        self.assertIsNone(_num("abc"))
        self.assertIsNone(_num(None))


class TestRoomsToInt(unittest.TestCase):
    def test_word(self):
        self.assertEqual(_rooms_to_int("THREE"), 3)

    def test_numeric(self):
        self.assertEqual(_rooms_to_int(2), 2)
        self.assertEqual(_rooms_to_int("4"), 4)

    def test_unknown_is_none(self):
        self.assertIsNone(_rooms_to_int("ELEVEN"))
        self.assertIsNone(_rooms_to_int(None))


class TestExtractLocation(unittest.TestCase):
    def test_district_and_neighbourhood(self):
        district, neighbourhood = _extract_location(_ITEM)
        self.assertEqual(district, "Śródmieście")
        self.assertEqual(neighbourhood, "Centrum")

    def test_drops_region_and_city_noise(self):
        item = {"location": {"reverseGeocoding": {"locations": [
            {"name": "podkarpackie"}, {"name": "Rzeszów"},
        ]}}}
        self.assertEqual(_extract_location(item), ("", ""))

    def test_empty_location(self):
        self.assertEqual(_extract_location({}), ("", ""))


class TestExtractCondition(unittest.TestCase):
    def test_mapped_status(self):
        self.assertEqual(_extract_condition({"constructionStatus": "READY_TO_USE"}), "do zamieszkania")
        self.assertEqual(_extract_condition({"constructionStatus": "TO_COMPLETION"}), "stan deweloperski")
        self.assertEqual(_extract_condition({"constructionStatus": "TO_RENOVATION"}), "do remontu")

    def test_unmapped_status_passthrough(self):
        self.assertEqual(_extract_condition({"state": "do zamieszkania"}), "do zamieszkania")

    def test_missing_is_none(self):
        self.assertIsNone(_extract_condition({}))


class TestParseItem(unittest.TestCase):
    def test_full_item(self):
        out = _parse_item(_ITEM, "sale", BASE)
        self.assertEqual(out["url"], f"{BASE}/pl/oferta/{_ITEM['slug']}")
        self.assertEqual(out["title"], _ITEM["title"])
        self.assertEqual(out["transaction_type"], "sale")
        self.assertEqual(out["district"], "Śródmieście")
        self.assertEqual(out["neighbourhood"], "Centrum")
        self.assertEqual(out["price_pln"], 480000.0)
        self.assertEqual(out["area_m2"], 52.0)
        self.assertEqual(out["rooms"], 3)
        self.assertEqual(out["floor"], 3.0)
        self.assertEqual(out["year_built"], 2005.0)
        self.assertEqual(out["finishing_condition"], "do zamieszkania")
        self.assertEqual(out["lat"], 50.0413)
        self.assertEqual(out["lng"], 22.0047)

    def test_missing_price_dropped(self):
        item = dict(_ITEM)
        item.pop("totalPrice")
        self.assertIsNone(_parse_item(item, "sale", BASE))

    def test_missing_area_dropped(self):
        item = dict(_ITEM)
        item.pop("areaInSquareMeters")
        self.assertIsNone(_parse_item(item, "sale", BASE))

    def test_no_url_or_slug_dropped(self):
        item = {k: v for k, v in _ITEM.items() if k != "slug"}
        self.assertIsNone(_parse_item(item, "sale", BASE))

    def test_url_used_directly_if_present(self):
        item = dict(_ITEM)
        item["url"] = "https://www.otodom.pl/pl/oferta/explicit-url"
        out = _parse_item(item, "sale", BASE)
        self.assertEqual(out["url"], "https://www.otodom.pl/pl/oferta/explicit-url")

    def test_rooms_defaults_to_one(self):
        item = dict(_ITEM)
        item.pop("roomsNumber")
        out = _parse_item(item, "sale", BASE)
        self.assertEqual(out["rooms"], 1)


if __name__ == "__main__":
    unittest.main()
