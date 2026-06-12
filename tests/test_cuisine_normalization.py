from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "etl"))

from openli_etl.cuisine_normalization import normalize_cuisine


class CuisineNormalizationTest(unittest.TestCase):
    def test_german_regional(self) -> None:
        result = normalize_cuisine("german;regional", addr_country="DE")
        self.assertEqual(result.cuisine_tokens, "german|regional")
        self.assertEqual(result.cuisine_primary, "German")
        self.assertEqual(result.cuisine_primary_type, "country")
        self.assertEqual(result.cuisine_country, "Germany")
        self.assertEqual(result.cuisine_country_code, "DE")

    def test_regional_by_country(self) -> None:
        cases = [
            ("DE", "German Regional", "Germany", "DE"),
            ("AT", "Austrian Regional", "Austria", "AT"),
            ("AL", "Albanian Regional", "Albania", "AL"),
            ("TH", "Thai Regional", "Thailand", "TH"),
            ("NZ", "New Zealand Regional", "New Zealand", "NZ"),
        ]
        for code, label, country, country_code in cases:
            with self.subTest(code=code):
                result = normalize_cuisine("regional", addr_country=code)
                self.assertEqual(result.cuisine_primary, label)
                self.assertEqual(result.cuisine_primary_type, "regional")
                self.assertEqual(result.cuisine_country, country)
                self.assertEqual(result.cuisine_country_code, country_code)

    def test_food_type_multi_cuisine(self) -> None:
        result = normalize_cuisine("pizza;burger;fries;salad")
        self.assertEqual(result.cuisine_tokens, "pizza|burger|fries|salad")
        self.assertEqual(result.cuisine_primary, "Pizza")
        self.assertEqual(result.cuisine_primary_type, "food_type")
        self.assertIsNone(result.cuisine_country)
        self.assertTrue(result.cuisine_is_multi)
        self.assertEqual(result.cuisine_token_count, 4)

    def test_long_food_type_multi_cuisine(self) -> None:
        result = normalize_cuisine("pizza;coffee_shop;sandwich;ice_cream;breakfast")
        self.assertEqual(result.cuisine_tokens, "pizza|coffee_shop|sandwich|ice_cream|breakfast")
        self.assertEqual(result.cuisine_primary, "Pizza")
        self.assertEqual(result.cuisine_primary_type, "food_type")

    def test_multi_country_keeps_first_primary(self) -> None:
        result = normalize_cuisine(" french;german")
        self.assertEqual(result.cuisine_tokens, "french|german")
        self.assertEqual(result.cuisine_primary, "French")
        self.assertEqual(result.cuisine_primary_type, "country")
        self.assertEqual(result.cuisine_country, "France")
        self.assertEqual(result.cuisine_country_code, "FR")

    def test_empty_cuisine(self) -> None:
        result = normalize_cuisine(None)
        self.assertIsNone(result.cuisine_raw)
        self.assertIsNone(result.cuisine_tokens)
        self.assertIsNone(result.cuisine_primary)
        self.assertEqual(result.cuisine_primary_type, "unknown")
        self.assertFalse(result.cuisine_is_multi)
        self.assertEqual(result.cuisine_token_count, 0)


if __name__ == "__main__":
    unittest.main()
