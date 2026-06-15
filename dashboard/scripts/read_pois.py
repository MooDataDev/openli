from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "processed"
ETL_ROOT = ROOT_DIR / "etl"
sys.path.insert(0, str(ETL_ROOT))

from openli_etl.geo_normalization import (
    continent_from_country,
    continent_from_snapshot_path,
    country_from_code_or_name,
    country_from_snapshot_path,
)


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
    return country_from_snapshot_path(path)


def country_from_value(value: object, fallback: str) -> str:
    return country_from_code_or_name(value, fallback=fallback)


def get_series(dataframe: pd.DataFrame, column: str, default: object = None) -> pd.Series:
    if column in dataframe.columns:
        return dataframe[column]
    return pd.Series(default, index=dataframe.index, dtype="object")


def any_present(dataframe: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [column for column in columns if column in dataframe.columns]
    if not available:
        return pd.Series(False, index=dataframe.index)
    return dataframe[available].notna().any(axis=1)


def first_present(dataframe: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series(None, index=dataframe.index, dtype="object")
    for column in columns:
        if column in dataframe.columns:
            result = result.combine_first(dataframe[column])
    return result


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


def read_latest_pois() -> dict[str, object]:
    files = sorted(Path(path) for path in glob.glob(str(DATA_DIR / "*_snapshot_latest.parquet")))
    pois: list[dict[str, object]] = []
    snapshot_dates: set[str] = set()

    for file_path in files:
        fallback_country = country_from_path(file_path)
        dataframe = pd.read_parquet(file_path)
        dataframe = dataframe[dataframe["lat"].notna() & dataframe["lon"].notna()].copy()

        if "cuisine_tokens" not in dataframe.columns or "cuisine_group" not in dataframe.columns:
            from openli_etl.cuisine_normalization import add_cuisine_columns

            dataframe = add_cuisine_columns(dataframe)

        if "snapshot_date" in dataframe.columns:
            snapshot_dates.update(
                value for value in dataframe["snapshot_date"].dropna().astype(str).unique().tolist() if value
            )

        country_codes = get_series(dataframe, "addr_country")
        country_series = country_codes.map(lambda value: country_from_value(value, fallback_country))
        fallback_continent = continent_from_snapshot_path(file_path)
        continent_series = get_series(dataframe, "continent").combine_first(
            country_series.map(lambda value: continent_from_country(value, fallback=fallback_continent))
        )
        city_series = get_series(dataframe, "addr_city").combine_first(get_series(dataframe, "addr_suburb"))
        cuisine_tokens = get_series(dataframe, "cuisine_tokens", "").fillna("").map(
            lambda value: [token for token in str(value).split("|") if token]
        )

        selected = pd.DataFrame(
            {
                "osmId": get_series(dataframe, "osm_id"),
                "osmType": get_series(dataframe, "osm_type"),
                "name": get_series(dataframe, "name").fillna("Unnamed place"),
                "continent": continent_series.fillna("Unknown"),
                "country": country_series,
                "city": city_series.fillna("Unknown"),
                "amenity": get_series(dataframe, "amenity").fillna("unknown"),
                "cuisine": get_series(dataframe, "cuisine"),
                "cuisineRaw": get_series(dataframe, "cuisine_raw").combine_first(get_series(dataframe, "cuisine")),
                "cuisineTokens": cuisine_tokens,
                "cuisinePrimary": get_series(dataframe, "cuisine_primary"),
                "cuisinePrimaryType": get_series(dataframe, "cuisine_primary_type").fillna("unknown"),
                "cuisineCountry": get_series(dataframe, "cuisine_country"),
                "cuisineGroup": get_series(dataframe, "cuisine_group"),
                "cuisineGroupKey": get_series(dataframe, "cuisine_group_key"),
                "cuisineGroupType": get_series(dataframe, "cuisine_group_type").fillna("unknown"),
                "hasWebsite": any_present(dataframe, ["website_url", "website", "contact_website"]),
                "hasMenuUrl": any_present(dataframe, ["menu_url", "website_menu"]),
                "websiteUrl": first_present(dataframe, ["website_url", "website", "contact_website"]),
                "menuUrl": first_present(dataframe, ["menu_url", "website_menu"]),
                "lat": dataframe["lat"].astype(float),
                "lon": dataframe["lon"].astype(float),
            }
        )

        for record in selected.to_dict(orient="records"):
            record = {key: json_clean(value) for key, value in record.items()}
            record["id"] = f"{record['country']}:{record['osmType']}:{record['osmId']}"
            pois.append(record)

    countries = sorted({poi["country"] for poi in pois})
    continents = sorted({poi["continent"] for poi in pois if poi["continent"] != "Unknown"})
    cities = sorted({poi["city"] for poi in pois if poi["city"] != "Unknown"})
    amenities = sorted({poi["amenity"] for poi in pois})
    cuisine_values = {str(poi["cuisineGroup"]).strip() for poi in pois if clean(poi.get("cuisineGroup"))}

    return {
        "files": [str(path.relative_to(ROOT_DIR)) for path in files],
        "snapshotDate": max(snapshot_dates) if snapshot_dates else None,
        "pois": pois,
        "continents": continents,
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
