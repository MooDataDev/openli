from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


COUNTRY_NAME_BY_CODE = {
    "AL": "Albania",
    "AT": "Austria",
    "DE": "Germany",
    "FR": "France",
    "GR": "Greece",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "Korea",
    "MX": "Mexico",
    "NZ": "New Zealand",
    "TH": "Thailand",
    "TR": "Turkey",
    "US": "United States",
    "VN": "Vietnam",
    "CN": "China",
    "ES": "Spain",
    "BA": "Bosnia and Herzegovina",
    "HR": "Croatia",
}

COUNTRY_CODE_BY_NAME = {name: code for code, name in COUNTRY_NAME_BY_CODE.items()}

COUNTRY_BY_FILENAME = {
    "albania": ("AL", "Albania"),
    "austria": ("AT", "Austria"),
    "germany": ("DE", "Germany"),
    "new-zealand": ("NZ", "New Zealand"),
    "new_zealand": ("NZ", "New Zealand"),
    "thailand": ("TH", "Thailand"),
}

COUNTRY_CUISINES = {
    "albanian": ("AL", "Albania", "Albanian"),
    "american": ("US", "United States", "American"),
    "asian": (None, None, "Asian"),
    "austrian": ("AT", "Austria", "Austrian"),
    "balkan": (None, None, "Balkan"),
    "bavarian": ("DE", "Germany", "Bavarian"),
    "bosnian": ("BA", "Bosnia and Herzegovina", "Bosnian"),
    "chinese": ("CN", "China", "Chinese"),
    "croatian": ("HR", "Croatia", "Croatian"),
    "french": ("FR", "France", "French"),
    "german": ("DE", "Germany", "German"),
    "greek": ("GR", "Greece", "Greek"),
    "indian": ("IN", "India", "Indian"),
    "italian": ("IT", "Italy", "Italian"),
    "japanese": ("JP", "Japan", "Japanese"),
    "korean": ("KR", "Korea", "Korean"),
    "mexican": ("MX", "Mexico", "Mexican"),
    "spanish": ("ES", "Spain", "Spanish"),
    "thai": ("TH", "Thailand", "Thai"),
    "turkish": ("TR", "Turkey", "Turkish"),
    "vietnamese": ("VN", "Vietnam", "Vietnamese"),
}

FOOD_TYPE_LABELS = {
    "barbecue": "Barbecue",
    "bbq": "Barbecue",
    "breakfast": "Breakfast",
    "burger": "Burger",
    "chicken": "Chicken",
    "coffee_shop": "Coffee Shop",
    "fish": "Fish",
    "fries": "Fries",
    "ice_cream": "Ice Cream",
    "kebab": "Kebab",
    "noodle": "Noodle",
    "pizza": "Pizza",
    "salad": "Salad",
    "sandwich": "Sandwich",
    "seafood": "Seafood",
    "steak_house": "Steak House",
    "sushi": "Sushi",
}

GENERIC_LABELS = {
    "international": "International",
    "mediterranean": "Mediterranean",
    "vegetarian": "Vegetarian",
    "vegan": "Vegan",
}

REGIONAL_TOKENS = {"regional", "local", "heuriger", "buschenschank"}

TOKEN_ALIASES = {
    "breakf": "breakfast",
    "burgers": "burger",
    "coffee": "coffee_shop",
    "coffee shop": "coffee_shop",
    "coffee-shop": "coffee_shop",
    "ice cream": "ice_cream",
    "ice-cream": "ice_cream",
    "italian pizza": "italian_pizza",
    "italian-pizza": "italian_pizza",
    "pasta": "italian",
    "pizzeria": "pizza",
    "steak": "steak_house",
    "steakhouse": "steak_house",
}


@dataclass(frozen=True)
class CuisineNormalization:
    cuisine_raw: str | None
    cuisine_tokens: str | None
    cuisine_primary: str | None
    cuisine_primary_type: str
    cuisine_country: str | None
    cuisine_country_code: str | None
    cuisine_is_multi: bool
    cuisine_token_count: int


def clean_value(value: Any) -> str | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def title_from_token(token: str) -> str:
    return token.replace("_", " ").replace("-", " ").title()


def normalize_token(token: str) -> str | None:
    normalized = token.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = TOKEN_ALIASES.get(normalized, normalized)
    normalized = normalized.replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        return None
    return TOKEN_ALIASES.get(normalized, normalized)


def split_cuisine_tokens(cuisine: Any) -> list[str]:
    raw = clean_value(cuisine)
    if raw is None:
        return []
    parts = re.split(r"\s*[;,]\s*", raw)
    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        token = normalize_token(part)
        if token and token not in seen:
            tokens.append(token)
            seen.add(token)
    return tokens


def country_from_context(addr_country: Any = None, source_file: Any = None) -> tuple[str | None, str | None]:
    raw_country = clean_value(addr_country)
    if raw_country:
        code = raw_country.upper()
        if code in COUNTRY_NAME_BY_CODE:
            return code, COUNTRY_NAME_BY_CODE[code]
        if raw_country in COUNTRY_CODE_BY_NAME:
            return COUNTRY_CODE_BY_NAME[raw_country], raw_country

    source = clean_value(source_file)
    if source:
        stem = Path(source).name.lower()
        stem = re.sub(r"-\d{6}\.osm\.pbf$", "", stem)
        stem = stem.replace("-latest.osm.pbf", "")
        if stem in COUNTRY_BY_FILENAME:
            return COUNTRY_BY_FILENAME[stem]
        for key, country in COUNTRY_BY_FILENAME.items():
            if key in stem:
                return country

    return None, None


def regional_label(country_name: str | None) -> str:
    if country_name == "Germany":
        return "German Regional"
    if country_name == "Austria":
        return "Austrian Regional"
    if country_name == "Thailand":
        return "Thai Regional"
    if country_name == "New Zealand":
        return "New Zealand Regional"
    if country_name == "Albania":
        return "Albanian Regional"
    return "Regional"


def classify_token(token: str, addr_country: Any = None, source_file: Any = None) -> tuple[str, str, str | None, str | None]:
    if token == "italian_pizza":
        return "Italian", "country", "Italy", "IT"

    if token in COUNTRY_CUISINES:
        code, country, label = COUNTRY_CUISINES[token]
        return label, "country", country, code

    if token in FOOD_TYPE_LABELS:
        return FOOD_TYPE_LABELS[token], "food_type", None, None

    if token in GENERIC_LABELS:
        return GENERIC_LABELS[token], "generic", None, None

    if token in REGIONAL_TOKENS:
        country_code, country_name = country_from_context(addr_country, source_file)
        return regional_label(country_name), "regional", country_name, country_code

    return title_from_token(token), "generic", None, None


def normalize_cuisine(cuisine: Any, addr_country: Any = None, source_file: Any = None) -> CuisineNormalization:
    cuisine_raw = clean_value(cuisine)
    tokens = split_cuisine_tokens(cuisine)
    if not tokens:
        return CuisineNormalization(
            cuisine_raw=cuisine_raw,
            cuisine_tokens=None,
            cuisine_primary=None,
            cuisine_primary_type="unknown",
            cuisine_country=None,
            cuisine_country_code=None,
            cuisine_is_multi=False,
            cuisine_token_count=0,
        )

    primary_token = None
    if tokens[0] in REGIONAL_TOKENS and len(tokens) > 1:
        primary_token = next((token for token in tokens[1:] if token not in REGIONAL_TOKENS), tokens[0])
    else:
        primary_token = tokens[0]

    label, primary_type, cuisine_country, cuisine_country_code = classify_token(
        primary_token,
        addr_country=addr_country,
        source_file=source_file,
    )

    return CuisineNormalization(
        cuisine_raw=cuisine_raw,
        cuisine_tokens="|".join(tokens),
        cuisine_primary=label,
        cuisine_primary_type=primary_type,
        cuisine_country=cuisine_country,
        cuisine_country_code=cuisine_country_code,
        cuisine_is_multi=len(tokens) > 1,
        cuisine_token_count=len(tokens),
    )


def add_cuisine_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    normalizations = [
        normalize_cuisine(
            row.get("cuisine"),
            addr_country=row.get("addr_country"),
            source_file=row.get("source_file"),
        )
        for _, row in result.iterrows()
    ]

    result["cuisine_raw"] = [item.cuisine_raw for item in normalizations]
    result["cuisine_tokens"] = [item.cuisine_tokens for item in normalizations]
    result["cuisine_primary"] = [item.cuisine_primary for item in normalizations]
    result["cuisine_primary_type"] = [item.cuisine_primary_type for item in normalizations]
    result["cuisine_country"] = [item.cuisine_country for item in normalizations]
    result["cuisine_country_code"] = [item.cuisine_country_code for item in normalizations]
    result["cuisine_is_multi"] = [item.cuisine_is_multi for item in normalizations]
    result["cuisine_token_count"] = [item.cuisine_token_count for item in normalizations]
    return result
