from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


COUNTRY_NAMES = {
    "AL": "Albania",
    "AT": "Austria",
    "BA": "Bosnia and Herzegovina",
    "BE": "Belgium",
    "CH": "Switzerland",
    "CZ": "Czechia",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "LU": "Luxembourg",
    "NL": "Netherlands",
    "NZ": "New Zealand",
    "PL": "Poland",
    "SI": "Slovenia",
    "TH": "Thailand",
    "albania": "Albania",
    "austria": "Austria",
    "germany": "Germany",
    "new-zealand": "New Zealand",
    "new_zealand": "New Zealand",
    "thailand": "Thailand",
}

COUNTRY_CONTINENTS = {
    "Albania": "Europe",
    "Austria": "Europe",
    "Belgium": "Europe",
    "Bosnia and Herzegovina": "Europe",
    "Czechia": "Europe",
    "France": "Europe",
    "Germany": "Europe",
    "Italy": "Europe",
    "Luxembourg": "Europe",
    "Netherlands": "Europe",
    "Poland": "Europe",
    "Slovenia": "Europe",
    "Switzerland": "Europe",
    "New Zealand": "Australia and Oceania",
    "Thailand": "Asia",
}


def country_from_code_or_name(value: object, fallback: str = "Unknown") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    raw = str(value).strip()
    if not raw:
        return fallback

    code = raw.upper()
    if code in COUNTRY_NAMES:
        return COUNTRY_NAMES[code]
    if raw in COUNTRY_NAMES:
        return COUNTRY_NAMES[raw]
    return raw


def country_from_snapshot_path(path: str | Path, fallback: str = "Unknown") -> str:
    file_name = Path(path).name
    match = re.match(r"food_pois_(.+)_snapshot_(?:latest|\d{8})\.parquet$", file_name)
    if not match:
        match = re.match(r"(.+)-\d{6}\.osm\.pbf$", file_name)
    if not match:
        return fallback

    value = match.group(1)
    return COUNTRY_NAMES.get(value, value.replace("_", " ").replace("-", " ").title())


def continent_from_country(country: object, fallback: str = "Unknown") -> str:
    normalized_country = country_from_code_or_name(country, fallback="")
    return COUNTRY_CONTINENTS.get(normalized_country, fallback)


def continent_from_snapshot_path(path: str | Path, fallback: str = "Unknown") -> str:
    return continent_from_country(country_from_snapshot_path(path), fallback=fallback)


def add_continent_column(dataframe: pd.DataFrame, source_path: str | Path | None = None) -> pd.DataFrame:
    enriched = dataframe.copy()
    fallback_continent = continent_from_snapshot_path(source_path, fallback="Unknown") if source_path else "Unknown"

    if "addr_country" in enriched.columns:
        continents = enriched["addr_country"].map(lambda value: continent_from_country(value, fallback=fallback_continent))
    else:
        continents = pd.Series(fallback_continent, index=enriched.index, dtype="object")

    if "continent" in enriched.columns:
        enriched["continent"] = enriched["continent"].combine_first(continents)
    else:
        enriched["continent"] = continents

    return enriched
