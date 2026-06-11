from __future__ import annotations

import glob
import json
import math
import re
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "processed"

COUNTRY_NAMES = {
    "AL": "Albania",
    "AT": "Austria",
    "DE": "Germany",
    "albania": "Albania",
    "austria": "Austria",
    "germany": "Germany",
}


def clean(value: object) -> str | None:
    if value is None:
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
    return COUNTRY_NAMES.get(value, value.replace("_", " ").title())


def country_from_row(row: pd.Series, fallback: str) -> str:
    raw = clean(row.get("addr_country"))
    if raw:
        return COUNTRY_NAMES.get(raw, raw)
    return fallback


def has_value(*values: object) -> bool:
    return any(clean(value) is not None for value in values)


def read_latest_pois() -> dict[str, object]:
    files = sorted(Path(path) for path in glob.glob(str(DATA_DIR / "*latest.parquet")))
    pois: list[dict[str, object]] = []
    snapshot_dates: set[str] = set()

    for file_path in files:
        fallback_country = country_from_path(file_path)
        dataframe = pd.read_parquet(file_path)
        for _, row in dataframe.iterrows():
            lat = row.get("lat")
            lon = row.get("lon")
            if pd.isna(lat) or pd.isna(lon):
                continue

            snapshot_date = clean(row.get("snapshot_date"))
            if snapshot_date:
                snapshot_dates.add(snapshot_date)

            country = country_from_row(row, fallback_country)
            city = clean(row.get("addr_city")) or clean(row.get("addr_suburb")) or "Unknown"
            amenity = clean(row.get("amenity")) or "unknown"
            cuisine = clean(row.get("cuisine"))
            name = clean(row.get("name")) or "Unnamed place"

            pois.append(
                {
                    "id": f"{country}:{clean(row.get('osm_type'))}:{clean(row.get('osm_id'))}",
                    "osmId": clean(row.get("osm_id")),
                    "osmType": clean(row.get("osm_type")),
                    "name": name,
                    "country": country,
                    "city": city,
                    "amenity": amenity,
                    "cuisine": cuisine,
                    "hasWebsite": has_value(row.get("website_url"), row.get("website"), row.get("contact_website")),
                    "hasMenuUrl": has_value(row.get("menu_url"), row.get("website_menu")),
                    "lat": float(lat),
                    "lon": float(lon),
                }
            )

    countries = sorted({poi["country"] for poi in pois})
    cities = sorted({poi["city"] for poi in pois if poi["city"] != "Unknown"})
    amenities = sorted({poi["amenity"] for poi in pois})
    cuisine_values = {
        token.strip()
        for poi in pois
        for token in str(poi.get("cuisine") or "").replace(";", ",").split(",")
        if token.strip()
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
    print(json.dumps(read_latest_pois(), ensure_ascii=False))
