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
        self.assertEqual(result.cuisine_group, "German")
        self.assertEqual(result.cuisine_group_key, "german")
        self.assertEqual(result.cuisine_group_type, "country")

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
                self.assertNotIn("Regional", result.cuisine_group or "")

    def test_food_type_multi_cuisine(self) -> None:
        result = normalize_cuisine("pizza;burger;fries;salad")
        self.assertEqual(result.cuisine_tokens, "pizza|burger|fries|salad")
        self.assertEqual(result.cuisine_primary, "Pizza")
        self.assertEqual(result.cuisine_primary_type, "food_type")
        self.assertEqual(result.cuisine_group, "Pizza")
        self.assertEqual(result.cuisine_group_type, "food_type")
        self.assertIsNone(result.cuisine_country)
        self.assertTrue(result.cuisine_is_multi)
        self.assertEqual(result.cuisine_token_count, 4)

    def test_long_food_type_multi_cuisine(self) -> None:
        result = normalize_cuisine("pizza;coffee_shop;sandwich;ice_cream;breakfast")
        self.assertEqual(result.cuisine_tokens, "pizza|coffee_shop|sandwich|ice_cream|breakfast")
        self.assertEqual(result.cuisine_primary, "Pizza")
        self.assertEqual(result.cuisine_primary_type, "food_type")
        self.assertEqual(result.cuisine_group, "Pizza")
        self.assertEqual(result.cuisine_excluded_reason, "beverage")

    def test_multi_country_keeps_first_primary(self) -> None:
        result = normalize_cuisine(" french;german")
        self.assertEqual(result.cuisine_tokens, "french|german")
        self.assertEqual(result.cuisine_primary, "French")
        self.assertEqual(result.cuisine_primary_type, "country")
        self.assertEqual(result.cuisine_country, "France")
        self.assertEqual(result.cuisine_country_code, "FR")
        self.assertEqual(result.cuisine_group, "French")

    def test_empty_cuisine(self) -> None:
        result = normalize_cuisine(None)
        self.assertIsNone(result.cuisine_raw)
        self.assertIsNone(result.cuisine_tokens)
        self.assertIsNone(result.cuisine_primary)
        self.assertEqual(result.cuisine_primary_type, "unknown")
        self.assertFalse(result.cuisine_is_multi)
        self.assertEqual(result.cuisine_token_count, 0)
        self.assertIsNone(result.cuisine_group)
        self.assertEqual(result.cuisine_group_type, "unknown")

    def test_afghan_aliases(self) -> None:
        for value in ("afgan", "afghan", "afghanisch"):
            with self.subTest(value=value):
                result = normalize_cuisine(value)
                self.assertEqual(result.cuisine_group, "Afghan")
                self.assertEqual(result.cuisine_group_key, "afghan")
                self.assertEqual(result.cuisine_group_type, "country")

    def test_beverages_are_excluded_from_group(self) -> None:
        for value in ("apfelwein", "beers", "wine"):
            with self.subTest(value=value):
                result = normalize_cuisine(value)
                self.assertIsNone(result.cuisine_group)
                self.assertEqual(result.cuisine_group_type, "unknown")
                self.assertEqual(result.cuisine_excluded_reason, "beverage")

    def test_thai_aliases(self) -> None:
        for value in ("thai_food", "thai_cuisine", "authentic_thai"):
            with self.subTest(value=value):
                result = normalize_cuisine(value)
                self.assertEqual(result.cuisine_group, "Thai")
                self.assertEqual(result.cuisine_group_key, "thai")

    def test_compound_country_preferred_over_food_type(self) -> None:
        for value, expected in (
            ("italian_pizza", "Italian"),
            ("traditional_italian", "Italian"),
            ("thai_bbq", "Thai"),
            ("thai_street_food", "Thai"),
            ("japanese_bbq", "Japanese"),
            ("shabushabu_japanese", "Japanese"),
        ):
            with self.subTest(value=value):
                result = normalize_cuisine(value)
                self.assertEqual(result.cuisine_group, expected)

    def test_excluded_tokens_are_skipped_for_group_choice(self) -> None:
        result = normalize_cuisine("beer;german;regional", addr_country="DE")
        self.assertEqual(result.cuisine_tokens, "beer|german|regional")
        self.assertEqual(result.cuisine_group, "German")
        self.assertEqual(result.cuisine_excluded_reason, "beverage")

    def test_noisy_value_has_no_group(self) -> None:
        for value in ("none", "no", "all", "https://example.com/menu", "th_sa_1600_2100"):
            with self.subTest(value=value):
                result = normalize_cuisine(value)
                self.assertIsNone(result.cuisine_group)
                self.assertEqual(result.cuisine_group_type, "unknown")


if __name__ == "__main__":
    unittest.main()
