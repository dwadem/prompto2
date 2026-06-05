"""Unit tests for json_cache loader helpers — stdlib unittest only."""
from __future__ import annotations

import os
import sys
import unittest

# Make sure app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.datasources.json_cache import (
    _clean_number,
    _clean_record,
    _normalize_keys,
    _records_from_csv,
    _records_from_json,
    _records_from_ndjson,
)


class TestNormalizeKeys(unittest.TestCase):
    def test_polish_aliases_mapped(self):
        rec = {"cena": 450000, "powierzchnia": 62.5, "dzielnica": "Śródmieście"}
        out = _normalize_keys(rec)
        self.assertEqual(out["price_pln"], 450000)
        self.assertEqual(out["area_m2"], 62.5)
        self.assertEqual(out["district"], "Śródmieście")

    def test_english_aliases_mapped(self):
        rec = {"price": 1, "area": 2, "link": "http://x", "rooms_count": 3}
        out = _normalize_keys(rec)
        self.assertEqual(out["price_pln"], 1)
        self.assertEqual(out["area_m2"], 2)
        self.assertEqual(out["url"], "http://x")
        self.assertEqual(out["rooms"], 3)

    def test_canonical_keys_passthrough(self):
        rec = {"url": "u", "price_pln": 5}
        out = _normalize_keys(rec)
        self.assertEqual(out["url"], "u")
        self.assertEqual(out["price_pln"], 5)

    def test_existing_canonical_not_clobbered_by_alias(self):
        # price_pln already set; alias "cena" should not overwrite it.
        rec = {"price_pln": 100, "cena": 999}
        out = _normalize_keys(rec)
        self.assertEqual(out["price_pln"], 100)

    def test_keys_stripped_and_lowercased(self):
        rec = {"  Cena  ": 7}
        out = _normalize_keys(rec)
        self.assertEqual(out["price_pln"], 7)


class TestCleanNumber(unittest.TestCase):
    def test_strips_currency_and_spaces(self):
        self.assertEqual(_clean_number("450 000 zł"), "450000")

    def test_non_breaking_space(self):
        self.assertEqual(_clean_number("1 200 000 PLN"), "1200000")

    def test_decimal_comma_to_dot(self):
        self.assertEqual(_clean_number("62,5 m²"), "62.5")

    def test_plain_number_passthrough(self):
        self.assertEqual(_clean_number("3"), "3")

    def test_non_string_untouched(self):
        self.assertEqual(_clean_number(450000), 450000)
        self.assertEqual(_clean_number(62.5), 62.5)

    def test_empty_string_to_none(self):
        self.assertIsNone(_clean_number(""))
        self.assertIsNone(_clean_number("   "))

    def test_negative_preserved(self):
        self.assertEqual(_clean_number("-3,5%"), "-3.5")

    def test_trailing_dot_stripped(self):
        self.assertEqual(_clean_number("100 m."), "100")


class TestCleanRecord(unittest.TestCase):
    def test_aliases_and_numbers_together(self):
        rec = {"cena": "450 000 zł", "powierzchnia": "62,5 m²", "link": "http://x"}
        out = _clean_record(rec)
        self.assertEqual(out["price_pln"], "450000")
        self.assertEqual(out["area_m2"], "62.5")
        self.assertEqual(out["url"], "http://x")

    def test_non_numeric_fields_untouched(self):
        rec = {"district": "Baranówka", "price_pln": "300000"}
        out = _clean_record(rec)
        self.assertEqual(out["district"], "Baranówka")
        self.assertEqual(out["price_pln"], "300000")


class TestRecordsFromJson(unittest.TestCase):
    def test_list(self):
        self.assertEqual(_records_from_json('[{"a":1},{"b":2}]'), [{"a": 1}, {"b": 2}])

    def test_listings_wrapper(self):
        self.assertEqual(_records_from_json('{"listings":[{"a":1}]}'), [{"a": 1}])

    def test_single_object(self):
        self.assertEqual(_records_from_json('{"url":"u"}'), [{"url": "u"}])

    def test_filters_non_dicts_in_list(self):
        self.assertEqual(_records_from_json('[{"a":1}, 5, "x"]'), [{"a": 1}])


class TestRecordsFromNdjson(unittest.TestCase):
    def test_basic(self):
        text = '{"a":1}\n{"b":2}\n'
        self.assertEqual(_records_from_ndjson(text), [{"a": 1}, {"b": 2}])

    def test_blank_lines_skipped(self):
        text = '{"a":1}\n\n  \n{"b":2}'
        self.assertEqual(_records_from_ndjson(text), [{"a": 1}, {"b": 2}])

    def test_malformed_line_skipped(self):
        text = '{"a":1}\nnot json\n{"b":2}'
        self.assertEqual(_records_from_ndjson(text), [{"a": 1}, {"b": 2}])


class TestRecordsFromCsv(unittest.TestCase):
    def test_basic(self):
        text = "url,cena\nhttp://x,450000\nhttp://y,300000\n"
        rows = _records_from_csv(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["url"], "http://x")
        self.assertEqual(rows[0]["cena"], "450000")


if __name__ == "__main__":
    unittest.main()
