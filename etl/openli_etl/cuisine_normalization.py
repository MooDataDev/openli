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
    "AF": "Afghanistan",
    "AR": "Argentina",
    "AU": "Australia",
    "BD": "Bangladesh",
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
    "BE": "Belgium",
    "BR": "Brazil",
    "GB": "United Kingdom",
    "HR": "Croatia",
    "IR": "Iran",
    "LB": "Lebanon",
    "NP": "Nepal",
    "PK": "Pakistan",
    "PT": "Portugal",
    "RU": "Russia",
    "SY": "Syria",
    "TW": "Taiwan",
    "UA": "Ukraine",
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
    "afghan": ("AF", "Afghanistan", "Afghan"),
    "albanian": ("AL", "Albania", "Albanian"),
    "argentinian": ("AR", "Argentina", "Argentinian"),
    "american": ("US", "United States", "American"),
    "asian": (None, None, "Asian"),
    "australian": ("AU", "Australia", "Australian"),
    "austrian": ("AT", "Austria", "Austrian"),
    "balkan": (None, None, "Balkan"),
    "bangladeshi": ("BD", "Bangladesh", "Bangladeshi"),
    "bavarian": ("DE", "Germany", "Bavarian"),
    "belgian": ("BE", "Belgium", "Belgian"),
    "bosnian": ("BA", "Bosnia and Herzegovina", "Bosnian"),
    "brazilian": ("BR", "Brazil", "Brazilian"),
    "british": ("GB", "United Kingdom", "British"),
    "chinese": ("CN", "China", "Chinese"),
    "croatian": ("HR", "Croatia", "Croatian"),
    "french": ("FR", "France", "French"),
    "german": ("DE", "Germany", "German"),
    "greek": ("GR", "Greece", "Greek"),
    "indian": ("IN", "India", "Indian"),
    "iranian": ("IR", "Iran", "Iranian"),
    "italian": ("IT", "Italy", "Italian"),
    "japanese": ("JP", "Japan", "Japanese"),
    "korean": ("KR", "Korea", "Korean"),
    "lebanese": ("LB", "Lebanon", "Lebanese"),
    "mexican": ("MX", "Mexico", "Mexican"),
    "nepalese": ("NP", "Nepal", "Nepalese"),
    "new_zealand": ("NZ", "New Zealand", "New Zealand"),
    "pakistani": ("PK", "Pakistan", "Pakistani"),
    "portuguese": ("PT", "Portugal", "Portuguese"),
    "russian": ("RU", "Russia", "Russian"),
    "spanish": ("ES", "Spain", "Spanish"),
    "syrian": ("SY", "Syria", "Syrian"),
    "taiwanese": ("TW", "Taiwan", "Taiwanese"),
    "thai": ("TH", "Thailand", "Thai"),
    "turkish": ("TR", "Turkey", "Turkish"),
    "ukrainian": ("UA", "Ukraine", "Ukrainian"),
    "vietnamese": ("VN", "Vietnam", "Vietnamese"),
}

FOOD_TYPE_LABELS = {
    "barbecue": "Barbecue",
    "bbq": "Barbecue",
    "breakfast": "Breakfast",
    "burger": "Burger",
    "chicken": "Chicken",
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
    "tacos": "Tacos",
    "ramen": "Ramen",
    "falafel": "Falafel",
}

GENERIC_LABELS = {
    "international": "International",
    "mediterranean": "Mediterranean",
    "vegetarian": "Vegetarian",
    "vegan": "Vegan",
}

REGIONAL_TOKENS = {"regional", "local", "heuriger", "buschenschank"}

CUISINE_GROUP_ALIASES = {
    "aethiopian": "ethiopian",
    "afgan": "afghan",
    "afghanisch": "afghan",
    "albanese": "albanian",
    "albania": "albanian",
    "albanisch": "albanian",
    "arab": "arabic",
    "arabian": "arabic",
    "argeninia": "argentinian",
    "argentina": "argentinian",
    "asia": "asian",
    "asia_fusion": "asian",
    "asian_fusion": "asian",
    "asien": "asian",
    "austrian": "austrian",
    "authentic_thai": "thai",
    "badisch": "german",
    "bangalideshi": "bangladeshi",
    "balkans": "balkan",
    "barbeque": "barbecue",
    "bavaria": "bavarian",
    "bayrisch": "bavarian",
    "brasil": "brazilian",
    "brasilianisch": "brazilian",
    "chineese": "chinese",
    "china": "chinese",
    "croatia": "croatian",
    "croatic": "croatian",
    "croation": "croatian",
    "deutsch": "german",
    "deutsche_kche": "german",
    "dner": "kebab",
    "doner": "kebab",
    "ethiopian": "ethiopian",
    "eu": "european",
    "europian": "european",
    "europran": "european",
    "frenc": "french",
    "frnkisch": "german",
    "frnkische": "german",
    "frnkische_kche": "german",
    "greece": "greek",
    "griechisch": "greek",
    "hessian": "german",
    "hessisch": "german",
    "india": "indian",
    "indisch": "indian",
    "italia": "italian",
    "italien": "italian",
    "italiian": "italian",
    "italian_pizza": "italian",
    "japanes_fusion": "japanese",
    "japanese_bbq": "japanese",
    "kanadisch": "canadian",
    "mediteran": "mediterranean",
    "mediterane": "mediterranean",
    "mediterran": "mediterranean",
    "mediterrean": "mediterranean",
    "mongol": "mongolian",
    "mongole": "mongolian",
    "nepal": "nepalese",
    "nepalesian": "nepalese",
    "nepali": "nepalese",
    "newzealandish": "new_zealand",
    "pakistan": "pakistani",
    "pakistanian": "pakistani",
    "pakistanisch": "pakistani",
    "pizza_italian": "italian",
    "polnish": "polish",
    "rumanian": "romanian",
    "rumnisch": "romanian",
    "schwbisch": "german",
    "serbisch": "serbian",
    "shabushabu_japanese": "japanese",
    "sigapore": "singaporean",
    "singaporian": "singaporean",
    "singapur": "singaporean",
    "singapurian": "singaporean",
    "singapurisch": "singaporean",
    "south_indian": "indian",
    "spain": "spanish",
    "srilankan": "sri_lankan",
    "sri_lanka": "sri_lankan",
    "sterreichisch": "austrian",
    "syrisch": "syrian",
    "tailandesa": "thai",
    "tha": "thai",
    "thai_cuisine": "thai",
    "thai_bbq": "thai",
    "thai_food": "thai",
    "thai_street_food": "thai",
    "thai_restaurant": "thai",
    "thaifood": "thai",
    "traditional_italian": "italian",
    "turc": "turkish",
    "tschechisch": "czech",
    "uigurisch": "uyghur",
    "usbek": "uzbek",
    "usbekian": "uzbek",
    "usbekisch": "uzbek",
    "uyghurisch": "uyghur",
    "uygur": "uyghur",
    "vietnames": "vietnamese",
    "vietnam": "vietnamese",
}

EXCLUDED_CUISINE_TOKENS = {
    "alcohol": "beverage",
    "alcoholic_drinks": "beverage",
    "apfelwein": "beverage",
    "bar": "service",
    "beer": "beverage",
    "beer_garden": "service",
    "beers": "beverage",
    "bier": "beverage",
    "biergarten": "service",
    "bistro": "service",
    "brewery": "beverage",
    "buffet": "service",
    "cafe": "service",
    "cafeteria": "service",
    "canteen": "service",
    "cantene": "service",
    "cocktail": "beverage",
    "cocktails": "beverage",
    "coffee": "beverage",
    "coffee_shop": "beverage",
    "coffe_shop": "beverage",
    "craft_beer": "beverage",
    "craftbeer": "beverage",
    "drink": "beverage",
    "drinks": "beverage",
    "espresso": "beverage",
    "full_bar": "beverage",
    "kaffee": "beverage",
    "mensa": "service",
    "michelin": "quality",
    "michelin_star": "quality",
    "pub": "service",
    "restaurant": "service",
    "tea": "beverage",
    "teahouse": "beverage",
    "wein": "beverage",
    "wine": "beverage",
    "wine_bar": "beverage",
    "weingut": "beverage",
}

QUALITY_TOKENS = {
    "authentic",
    "casual_fine_dining",
    "exceptional",
    "exclusive",
    "fine",
    "fine_dining",
    "gastronomic",
    "gehoben",
    "gourmet",
    "haute_cuisine",
    "modern",
    "nouvelle_cuisine",
    "sophisticated",
    "traditional",
    "traditionally",
}

INVALID_TOKENS = {
    "all",
    "all_you_can_eat",
    "everything",
    "food",
    "food_and_drinks",
    "mixed",
    "mo",
    "multi",
    "multi_cusine",
    "no",
    "none",
    "p",
    "various",
    "wechselnd",
    "und",
}

MACRO_REGION_GROUPS = {
    "african": "African",
    "arabic": "Arabic",
    "asian": "Asian",
    "balkan": "Balkan",
    "caribbean": "Caribbean",
    "central_european": "Central European",
    "eastern_european": "Eastern European",
    "european": "European",
    "international": "International",
    "mediterranean": "Mediterranean",
    "middle_eastern": "Middle Eastern",
    "oriental": "Middle Eastern",
    "orientalisch": "Middle Eastern",
    "pan_asian": "Asian",
    "south_american": "South American",
    "south_east_asia": "Southeast Asian",
    "southeast_european": "Southeast European",
    "western": "Western",
}

DIET_GROUPS = {
    "halal": "Halal",
    "vegetarian": "Vegetarian",
    "vegan": "Vegan",
}

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
class CuisineGroup:
    label: str
    key: str
    group_type: str
    country: str | None = None
    country_code: str | None = None


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
    cuisine_group: str | None
    cuisine_group_key: str | None
    cuisine_group_type: str
    cuisine_excluded_reason: str | None


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


def regional_group(country_name: str | None) -> CuisineGroup | None:
    if not country_name:
        return None
    key = normalize_token(country_name) or country_name.lower().replace(" ", "_")
    if country_name == "Germany":
        return CuisineGroup("German", "german", "regional", "Germany", "DE")
    if country_name == "Austria":
        return CuisineGroup("Austrian", "austrian", "regional", "Austria", "AT")
    if country_name == "Thailand":
        return CuisineGroup("Thai", "thai", "regional", "Thailand", "TH")
    if country_name == "Albania":
        return CuisineGroup("Albanian", "albanian", "regional", "Albania", "AL")
    if country_name == "New Zealand":
        return CuisineGroup("New Zealand", "new_zealand", "regional", "New Zealand", "NZ")
    return CuisineGroup(country_name, key, "regional", country_name, COUNTRY_CODE_BY_NAME.get(country_name))


def excluded_reason_for_token(token: str) -> str | None:
    if token in EXCLUDED_CUISINE_TOKENS:
        return EXCLUDED_CUISINE_TOKENS[token]
    if token in QUALITY_TOKENS:
        return "quality"
    if token in INVALID_TOKENS:
        return "invalid"
    if token.startswith("http") or "www" in token:
        return "invalid"
    if re.search(r"(mo|tu|we|th|fr|sa|su)_?\d{3,4}_\d{3,4}", token):
        return "invalid"
    if len(token) > 48:
        return "too_specific"
    return None


def group_from_country_token(token: str) -> CuisineGroup | None:
    if token not in COUNTRY_CUISINES:
        return None
    code, country, label = COUNTRY_CUISINES[token]
    key = normalize_token(label) or token
    group_type = "macro_region" if code is None else "country"
    return CuisineGroup(label=label, key=key, group_type=group_type, country=country, country_code=code)


def group_from_token(token: str, addr_country: Any = None, source_file: Any = None) -> CuisineGroup | None:
    aliased = CUISINE_GROUP_ALIASES.get(token, token)

    if aliased in REGIONAL_TOKENS:
        _, country_name = country_from_context(addr_country, source_file)
        return regional_group(country_name)

    country_group = group_from_country_token(aliased)
    if country_group:
        return country_group

    if aliased in MACRO_REGION_GROUPS:
        return CuisineGroup(MACRO_REGION_GROUPS[aliased], aliased, "macro_region")

    if aliased in DIET_GROUPS:
        return CuisineGroup(DIET_GROUPS[aliased], aliased, "diet")

    if aliased in FOOD_TYPE_LABELS:
        return CuisineGroup(FOOD_TYPE_LABELS[aliased], aliased, "food_type")

    return None


def choose_cuisine_group(tokens: list[str], addr_country: Any = None, source_file: Any = None) -> tuple[CuisineGroup | None, str | None]:
    candidates: list[CuisineGroup] = []
    excluded_reasons: list[str] = []

    for token in tokens:
        reason = excluded_reason_for_token(token)
        if reason:
            excluded_reasons.append(reason)
            continue

        group = group_from_token(token, addr_country=addr_country, source_file=source_file)
        if group:
            candidates.append(group)

    if not candidates:
        return None, excluded_reasons[0] if excluded_reasons else None

    for group_type in ("country", "regional", "macro_region", "diet"):
        for candidate in candidates:
            if candidate.group_type == group_type:
                return candidate, excluded_reasons[0] if excluded_reasons else None

    return candidates[0], excluded_reasons[0] if excluded_reasons else None


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
            cuisine_group=None,
            cuisine_group_key=None,
            cuisine_group_type="unknown",
            cuisine_excluded_reason=None,
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
    cuisine_group, excluded_reason = choose_cuisine_group(
        tokens,
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
        cuisine_group=cuisine_group.label if cuisine_group else None,
        cuisine_group_key=cuisine_group.key if cuisine_group else None,
        cuisine_group_type=cuisine_group.group_type if cuisine_group else "unknown",
        cuisine_excluded_reason=excluded_reason,
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
    result["cuisine_group"] = [item.cuisine_group for item in normalizations]
    result["cuisine_group_key"] = [item.cuisine_group_key for item in normalizations]
    result["cuisine_group_type"] = [item.cuisine_group_type for item in normalizations]
    result["cuisine_excluded_reason"] = [item.cuisine_excluded_reason for item in normalizations]
    return result
