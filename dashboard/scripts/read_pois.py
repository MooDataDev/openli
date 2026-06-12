from __future__ import annotations

import glob
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "processed"
ETL_ROOT = ROOT_DIR / "etl"
sys.path.insert(0, str(ETL_ROOT))

from openli_etl.cuisine_normalization import normalize_cuisine

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


def clean(value: object) -> str | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def country_from_path(path: Path) -> str:
    match = re.match(r"food_pois_(.+)_snapshot_latest\.parquet$", path.name)
    if not match:
        return "Unknown"
    value = match.group(1)
    return COUNTRY_NAMES.get(value, value.replace("_", " ").replace("-", " ").title())


def country_from_row(row: pd.Series, fallback: str) -> str:
    raw = clean(row.get("addr_country"))
    if raw:
        code = raw.upper()
        if code in COUNTRY_NAMES:
            return COUNTRY_NAMES[code]
        if raw in COUNTRY_NAMES:
            return COUNTRY_NAMES[raw]
    return fallback


def country_from_value(value: object, fallback: str) -> str:
    raw = clean(value)
    if raw:
        code = raw.upper()
        if code in COUNTRY_NAMES:
            return COUNTRY_NAMES[code]
        if raw in COUNTRY_NAMES:
            return COUNTRY_NAMES[raw]
    return fallback


def has_value(*values: object) -> bool:
    return any(clean(value) is not None for value in values)


def get_series(dataframe: pd.DataFrame, column: str, default: object = None) -> pd.Series:
    if column in dataframe.columns:
        return dataframe[column]
    return pd.Series(default, index=dataframe.index, dtype="object")


def any_present(dataframe: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [column for column in columns if column in dataframe.columns]
    if not available:
        return pd.Series(False, index=dataframe.index)
    return dataframe[available].notna().any(axis=1)


def json_clean(value: object) -> object:
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := json_clean(item)) is not None]
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def normalized_cuisine_fields(row: pd.Series) -> dict[str, object]:
    if "cuisine_tokens" in row.index:
        cuisine_tokens = clean(row.get("cuisine_tokens"))
        token_list = cuisine_tokens.split("|") if cuisine_tokens else []
        return {
            "cuisineRaw": clean(row.get("cuisine_raw")) or clean(row.get("cuisine")),
            "cuisineTokens": token_list,
            "cuisinePrimary": clean(row.get("cuisine_primary")),
            "cuisinePrimaryType": clean(row.get("cuisine_primary_type")) or "unknown",
            "cuisineCountry": clean(row.get("cuisine_country")),
        }

    normalized = normalize_cuisine(
        row.get("cuisine"),
        addr_country=row.get("addr_country"),
        source_file=row.get("source_file"),
    )
    return {
        "cuisineRaw": normalized.cuisine_raw,
        "cuisineTokens": normalized.cuisine_tokens.split("|") if normalized.cuisine_tokens else [],
        "cuisinePrimary": normalized.cuisine_primary,
        "cuisinePrimaryType": normalized.cuisine_primary_type,
        "cuisineCountry": normalized.cuisine_country,
    }


def read_latest_pois() -> dict[str, object]:
    files = sorted(Path(path) for path in glob.glob(str(DATA_DIR / "*_snapshot_latest.parquet")))
    pois: list[dict[str, object]] = []
    snapshot_dates: set[str] = set()

    for file_path in files:
        fallback_country = country_from_path(file_path)
        dataframe = pd.read_parquet(file_path)
        dataframe = dataframe[dataframe["lat"].notna() & dataframe["lon"].notna()].copy()

        if "cuisine_tokens" not in dataframe.columns:
            from openli_etl.cuisine_normalization import add_cuisine_columns

            dataframe = add_cuisine_columns(dataframe)

        if "snapshot_date" in dataframe.columns:
            snapshot_dates.update(
                value for value in dataframe["snapshot_date"].dropna().astype(str).unique().tolist() if value
            )

        country_codes = get_series(dataframe, "addr_country")
        country_series = country_codes.map(lambda value: country_from_value(value, fallback_country))
        city_series = get_series(dataframe, "addr_city").combine_first(get_series(dataframe, "addr_suburb"))
        cuisine_tokens = get_series(dataframe, "cuisine_tokens", "").fillna("").map(
            lambda value: [token for token in str(value).split("|") if token]
        )

        selected = pd.DataFrame(
            {
                "osmId": get_series(dataframe, "osm_id"),
                "osmType": get_series(dataframe, "osm_type"),
                "name": get_series(dataframe, "name").fillna("Unnamed place"),
                "country": country_series,
                "city": city_series.fillna("Unknown"),
                "amenity": get_series(dataframe, "amenity").fillna("unknown"),
                "cuisine": get_series(dataframe, "cuisine"),
                "cuisineRaw": get_series(dataframe, "cuisine_raw").combine_first(get_series(dataframe, "cuisine")),
                "cuisineTokens": cuisine_tokens,
                "cuisinePrimary": get_series(dataframe, "cuisine_primary"),
                "cuisinePrimaryType": get_series(dataframe, "cuisine_primary_type").fillna("unknown"),
                "cuisineCountry": get_series(dataframe, "cuisine_country"),
                "hasWebsite": any_present(dataframe, ["website_url", "website", "contact_website"]),
                "hasMenuUrl": any_present(dataframe, ["menu_url", "website_menu"]),
                "lat": dataframe["lat"].astype(float),
                "lon": dataframe["lon"].astype(float),
            }
        )

        for record in selected.to_dict(orient="records"):
            record = {key: json_clean(value) for key, value in record.items()}
            record["id"] = f"{record['country']}:{record['osmType']}:{record['osmId']}"
            pois.append(record)

    countries = sorted({poi["country"] for poi in pois})
    cities = sorted({poi["city"] for poi in pois if poi["city"] != "Unknown"})
    amenities = sorted({poi["amenity"] for poi in pois})
    cuisine_values = {
        str(token).strip()
        for poi in pois
        for token in poi.get("cuisineTokens", [])
        if str(token).strip()
    }

    return {
        "files": [str(path.relative_to(ROOT_DIR)) for path in files],
        "snapshotDate": max(snapshot_dates) if snapshot_dates else None,
        "pois": pois,
        "countries": countries,
        "cities": cities,
        "amenities": amenities,
        "cuisines": sorted(cuisine_values),
        "metrics": {
            "totalPois": len(pois),
            "countriesCovered": len(countries),
            "citiesCovered": len(cities),
            "websiteCoverage": round(sum(1 for poi in pois if poi["hasWebsite"]) / len(pois), 4) if pois else 0,
            "menuCoverage": round(sum(1 for poi in pois if poi["hasMenuUrl"]) / len(pois), 4) if pois else 0,
        },
    }


if __name__ == "__main__":
    print(json.dumps(read_latest_pois(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
