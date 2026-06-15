from __future__ import annotations

import argparse
import json
import logging
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterable

import osmium
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from shapely import wkb
from shapely.geometry import LineString, Point, Polygon
from tqdm import tqdm

from openli_etl.cuisine_normalization import add_cuisine_columns
from openli_etl.geo_normalization import add_continent_column, continent_from_country, continent_from_snapshot_path


LOGGER = logging.getLogger("openli_etl.osm_food_pois")

DEFAULT_CATEGORIES = ("restaurant",)

RAW_TAG_COLUMNS = {
    "name": "name",
    "amenity": "amenity",
    "cuisine": "cuisine",
    "brand": "brand",
    "operator": "operator",
    "website": "website",
    "contact:website": "contact_website",
    "website:menu": "website_menu",
    "image": "image",
    "phone": "phone",
    "contact:phone": "contact_phone",
    "email": "email",
    "contact:email": "contact_email",
    "opening_hours": "opening_hours",
    "addr:street": "addr_street",
    "addr:housenumber": "addr_housenumber",
    "addr:postcode": "addr_postcode",
    "addr:city": "addr_city",
    "addr:suburb": "addr_suburb",
    "addr:country": "addr_country",
    "wheelchair": "wheelchair",
    "outdoor_seating": "outdoor_seating",
    "takeaway": "takeaway",
    "delivery": "delivery",
    "smoking": "smoking",
}

MENU_TAGS = ("menu", "menu:url", "website:menu", "contact:menu")
WEBSITE_TAGS = ("website", "contact:website")
PHONE_TAGS = ("phone", "contact:phone")
EMAIL_TAGS = ("email", "contact:email")

OUTPUT_COLUMNS = [
    "osm_id",
    "osm_type",
    "name",
    "amenity",
    "cuisine",
    "cuisine_raw",
    "cuisine_tokens",
    "cuisine_primary",
    "cuisine_primary_type",
    "cuisine_country",
    "cuisine_country_code",
    "cuisine_is_multi",
    "cuisine_token_count",
    "brand",
    "operator",
    "website",
    "contact_website",
    "menu_url",
    "website_menu",
    "website_url",
    "image",
    "phone",
    "contact_phone",
    "phone_number",
    "email",
    "contact_email",
    "email_address",
    "opening_hours",
    "addr_street",
    "addr_housenumber",
    "addr_postcode",
    "addr_city",
    "addr_suburb",
    "addr_country",
    "continent",
    "wheelchair",
    "outdoor_seating",
    "takeaway",
    "delivery",
    "smoking",
    "lat",
    "lon",
    "geometry",
    "source_file",
    "extraction_timestamp",
    "snapshot_date",
]


def snake_case(value: str) -> str:
    value = value.strip().replace(":", "_").replace("-", "_")
    value = re.sub(r"[^0-9a-zA-Z_]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def first_non_empty(tags: dict[str, str], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value:
            return value
    return None


def parse_categories(value: str | None) -> set[str]:
    if not value:
        return set(DEFAULT_CATEGORIES)
    categories = {item.strip() for item in value.split(",") if item.strip()}
    if not categories:
        raise ValueError("--categories must contain at least one category")
    return categories


def parse_snapshot_date(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(UTC).date()


def point_wkb(lon: float, lat: float) -> bytes:
    return Point(lon, lat).wkb


def centroid_from_wkb(geometry_wkb: bytes | None) -> tuple[float | None, float | None]:
    if not geometry_wkb:
        return None, None
    geometry = wkb.loads(geometry_wkb)
    if geometry.is_empty:
        return None, None
    representative = geometry.representative_point()
    return float(representative.y), float(representative.x)


@dataclass(frozen=True)
class ExtractionConfig:
    input_path: Path
    output_path: Path
    snapshot_date: date
    categories: set[str]
    show_progress: bool = True
    max_extract: int | None = None
    estimate_total_objects: bool = True


class MaxExtractReached(Exception):
    """Stop OSM scanning after the configured number of matched POIs."""


def estimate_total_osm_objects(input_path: Path) -> int | None:
    command = ["osmium", "fileinfo", "-e", str(input_path)]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        LOGGER.warning("Could not estimate total objects because the osmium CLI is not installed.")
        return None
    except subprocess.CalledProcessError as exc:
        LOGGER.warning("Could not estimate total objects with osmium fileinfo: %s", exc.stderr.strip())
        return None

    output = f"{result.stdout}\n{result.stderr}"
    counts = []
    for label in ("nodes", "ways", "relations"):
        match = re.search(rf"Number of {label}:\s+([0-9]+)", output)
        if not match:
            LOGGER.warning("Could not parse number of %s from osmium fileinfo output.", label)
            return None
        counts.append(int(match.group(1)))

    return sum(counts)


class RestaurantPoiHandler(osmium.SimpleHandler):
    def __init__(
        self,
        categories: set[str],
        source_file: Path,
        snapshot_date: date,
        max_extract: int | None = None,
        progress_bar: tqdm | None = None,
    ) -> None:
        super().__init__()
        self.categories = categories
        self.source_file = str(source_file)
        self.snapshot_date = snapshot_date.isoformat()
        self.extraction_timestamp = datetime.now(UTC).isoformat()
        self.max_extract = max_extract
        self.records: list[dict[str, object]] = []
        self.progress_bar = progress_bar
        self.scanned_objects = 0
        self.matched_objects = 0

    def node(self, node: osmium.osm.Node) -> None:
        self._tick_progress()
        tags = dict(node.tags)
        if not self._is_target(tags):
            return

        lat = float(node.location.lat)
        lon = float(node.location.lon)
        record = self._base_record(
            osm_id=str(node.id),
            osm_type="node",
            tags=tags,
            lat=lat,
            lon=lon,
            geometry_wkb=point_wkb(lon, lat),
        )
        self.records.append(record)
        self._record_match()

    def way(self, way: osmium.osm.Way) -> None:
        self._tick_progress()
        tags = dict(way.tags)
        if not self._is_target(tags):
            return

        geometry = self._way_geometry_wkb(way)
        lat, lon = centroid_from_wkb(geometry)
        record = self._base_record(
            osm_id=str(way.id),
            osm_type="way",
            tags=tags,
            lat=lat,
            lon=lon,
            geometry_wkb=geometry,
        )
        self.records.append(record)
        self._record_match()

    def relation(self, relation: osmium.osm.Relation) -> None:
        self._tick_progress()

    def _tick_progress(self) -> None:
        self.scanned_objects += 1
        if self.progress_bar is None:
            return
        self.progress_bar.update(1)
        if self.scanned_objects % 100_000 == 0:
            self.progress_bar.set_postfix_str(f"matches={self.matched_objects:,}", refresh=False)

    def _record_match(self) -> None:
        self.matched_objects += 1
        if self.progress_bar is not None:
            self.progress_bar.set_postfix_str(f"matches={self.matched_objects:,}", refresh=False)
        if self.max_extract is not None and self.matched_objects >= self.max_extract:
            raise MaxExtractReached

    def _is_target(self, tags: dict[str, str]) -> bool:
        return tags.get("amenity") in self.categories

    def _way_geometry_wkb(self, way: osmium.osm.Way) -> bytes | None:
        try:
            coordinates = [(float(node.lon), float(node.lat)) for node in way.nodes]
            if len(coordinates) >= 4 and coordinates[0] == coordinates[-1]:
                return Polygon(coordinates).wkb
            if len(coordinates) >= 2:
                return LineString(coordinates).wkb
            return None
        except Exception as exc:
            LOGGER.debug("Could not build geometry for way %s: %s", way.id, exc)
            return None

    def _base_record(
        self,
        osm_id: str,
        osm_type: str,
        tags: dict[str, str],
        lat: float | None,
        lon: float | None,
        geometry_wkb: bytes | None,
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "osm_id": osm_id,
            "osm_type": osm_type,
            "menu_url": first_non_empty(tags, MENU_TAGS),
            "website_url": first_non_empty(tags, WEBSITE_TAGS),
            "phone_number": first_non_empty(tags, PHONE_TAGS),
            "email_address": first_non_empty(tags, EMAIL_TAGS),
            "lat": lat if lat is not None and math.isfinite(lat) else None,
            "lon": lon if lon is not None and math.isfinite(lon) else None,
            "geometry": geometry_wkb,
            "source_file": self.source_file,
            "extraction_timestamp": self.extraction_timestamp,
            "snapshot_date": self.snapshot_date,
        }

        for raw_key, output_key in RAW_TAG_COLUMNS.items():
            record[output_key] = tags.get(raw_key)

        record["continent"] = continent_from_country(
            record.get("addr_country"),
            fallback=continent_from_snapshot_path(self.source_file),
        )

        return {column: record.get(column) for column in OUTPUT_COLUMNS}


def build_dataframe(records: list[dict[str, object]]) -> pd.DataFrame:
    dataframe = pd.DataFrame.from_records(records, columns=OUTPUT_COLUMNS)
    if dataframe.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    for column in OUTPUT_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[OUTPUT_COLUMNS]
    dataframe["lat"] = pd.to_numeric(dataframe["lat"], errors="coerce")
    dataframe["lon"] = pd.to_numeric(dataframe["lon"], errors="coerce")
    dataframe = add_continent_column(dataframe)
    dataframe = add_cuisine_columns(dataframe)
    return dataframe[OUTPUT_COLUMNS]


def quality_summary(dataframe: pd.DataFrame) -> dict[str, object]:
    total = int(len(dataframe))
    if total == 0:
        return {
            "total_pois": 0,
            "count_by_amenity": {},
            "share_with_website": 0.0,
            "share_with_menu_url": 0.0,
            "share_with_cuisine": 0.0,
            "share_with_coordinates": 0.0,
        }

    has_website = dataframe["website_url"].notna() | dataframe["website"].notna() | dataframe["contact_website"].notna()
    has_menu_url = dataframe["menu_url"].notna() | dataframe["website_menu"].notna()
    has_coordinates = dataframe["lat"].notna() & dataframe["lon"].notna()

    return {
        "total_pois": total,
        "count_by_amenity": dataframe["amenity"].value_counts(dropna=False).to_dict(),
        "share_with_website": round(float(has_website.mean()), 4),
        "share_with_menu_url": round(float(has_menu_url.mean()), 4),
        "share_with_cuisine": round(float(dataframe["cuisine"].notna().mean()), 4),
        "share_with_coordinates": round(float(has_coordinates.mean()), 4),
    }


def schema_for_output_columns() -> pa.Schema:
    fields = []
    for column in OUTPUT_COLUMNS:
        if column in {"lat", "lon"}:
            fields.append(pa.field(column, pa.float64()))
        elif column == "geometry":
            fields.append(pa.field(column, pa.binary()))
        elif column == "cuisine_is_multi":
            fields.append(pa.field(column, pa.bool_()))
        elif column == "cuisine_token_count":
            fields.append(pa.field(column, pa.int64()))
        else:
            fields.append(pa.field(column, pa.string()))
    return pa.schema(fields)


def write_parquet(dataframe: pd.DataFrame, output_path: Path, show_progress: bool = True) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = schema_for_output_columns()
    with tqdm(
        total=2,
        desc="Writing Parquet",
        unit="step",
        disable=not show_progress,
        file=sys.stderr,
    ) as progress_bar:
        table = pa.Table.from_pandas(dataframe, schema=schema, preserve_index=False)
        progress_bar.update(1)
        pq.write_table(table, output_path, compression="zstd")
        progress_bar.update(1)


def latest_parquet_path(output_path: Path) -> Path:
    if output_path.name.endswith("_snapshot_latest.parquet"):
        return output_path
    latest_name = re.sub(r"_snapshot_\d{8}\.parquet$", "_snapshot_latest.parquet", output_path.name)
    if latest_name == output_path.name:
        latest_name = f"{output_path.stem}_latest{output_path.suffix}"
    return output_path.with_name(latest_name)


def write_latest_parquet_copy(output_path: Path) -> Path:
    latest_path = latest_parquet_path(output_path)
    if latest_path == output_path:
        return latest_path
    shutil.copy2(output_path, latest_path)
    return latest_path


def write_summary(summary: dict[str, object], output_path: Path) -> Path:
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary_path

def latest_write_summary(summary: dict[str, object], output_path: Path) -> Path:
    summary_path = latest_parquet_path(output_path)
    summary_path = summary_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary_path

def extract(config: ExtractionConfig) -> tuple[pd.DataFrame, dict[str, object]]:
    LOGGER.info("Reading OSM file: %s", config.input_path)
    LOGGER.info("Target amenity categories: %s", ", ".join(sorted(config.categories)))
    if config.max_extract is not None:
        LOGGER.info("Max extract limit: %s matched POIs", config.max_extract)

    total_objects = None
    if config.show_progress and config.estimate_total_objects:
        LOGGER.info("Estimating total OSM objects with osmium fileinfo -e.")
        total_objects = estimate_total_osm_objects(config.input_path)
        if total_objects is not None:
            LOGGER.info("Estimated total OSM objects: %s", f"{total_objects:,}")

    with tqdm(
        total=total_objects,
        desc="Reading OSM objects",
        unit="obj",
        unit_scale=True,
        disable=not config.show_progress,
        file=sys.stderr,
    ) as progress_bar:
        handler = RestaurantPoiHandler(
            categories=config.categories,
            source_file=config.input_path,
            snapshot_date=config.snapshot_date,
            max_extract=config.max_extract,
            progress_bar=progress_bar,
        )
        try:
            handler.apply_file(str(config.input_path), locations=True, idx="flex_mem")
        except MaxExtractReached:
            LOGGER.info("Stopped after reaching max extract limit of %s matched POIs.", config.max_extract)
        progress_bar.set_postfix_str(f"matches={handler.matched_objects:,}", refresh=True)

    dataframe = build_dataframe(handler.records)
    summary = quality_summary(dataframe)
    return dataframe, summary


def run(config: ExtractionConfig) -> None:
    dataframe, summary = extract(config)
    write_parquet(dataframe, config.output_path, show_progress=config.show_progress)
    latest_path = write_latest_parquet_copy(config.output_path)
    with tqdm(
        total=1,
        desc="Writing summary",
        unit="file",
        disable=not config.show_progress,
        file=sys.stderr,
    ) as progress_bar:
        _ = write_summary(summary, config.output_path)
        summary_path = latest_write_summary(summary, config.output_path)
        progress_bar.update(1)

    LOGGER.info("Wrote Parquet: %s", config.output_path)
    LOGGER.info("Wrote latest Parquet: %s", latest_path)
    LOGGER.info("Wrote summary: %s", summary_path)
    LOGGER.info("Total POIs: %s", summary["total_pois"])
    LOGGER.info("Count by amenity: %s", summary["count_by_amenity"])
    LOGGER.info("Share with website: %.2f%%", summary["share_with_website"] * 100)
    LOGGER.info("Share with menu URL: %.2f%%", summary["share_with_menu_url"] * 100)
    LOGGER.info("Share with cuisine: %.2f%%", summary["share_with_cuisine"] * 100)
    LOGGER.info("Share with coordinates: %.2f%%", summary["share_with_coordinates"] * 100)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract restaurant POIs from an OpenStreetMap .osm.pbf snapshot into Parquet.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to a Germany .osm.pbf file.")
    parser.add_argument("--output", required=True, type=Path, help="Path to the output Parquet file.")
    parser.add_argument(
        "--snapshot-date",
        type=str,
        default=None,
        help="Snapshot date in YYYY-MM-DD format. Defaults to today's UTC date.",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="restaurant",
        help="Comma-separated amenity categories. MVP default: restaurant.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bars.",
    )
    parser.add_argument(
        "--no-estimate-total",
        dest="estimate_total_objects",
        action="store_false",
        help="Do not run osmium fileinfo before extraction. The reading progress bar is shown without a percentage.",
    )
    parser.add_argument(
        "--max-extract",
        "--max_extract",
        dest="max_extract",
        type=int,
        default=None,
        help="Stop after extracting this many matched POIs. If omitted, all matches are extracted.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = ExtractionConfig(
        input_path=args.input,
        output_path=args.output,
        snapshot_date=parse_snapshot_date(args.snapshot_date),
        categories=parse_categories(args.categories),
        show_progress=not args.no_progress,
        max_extract=args.max_extract,
        estimate_total_objects=args.estimate_total_objects,
    )

    if config.max_extract is not None and config.max_extract <= 0:
        parser.error("--max-extract must be a positive integer")

    if not config.input_path.exists():
        parser.error(f"Input file does not exist: {config.input_path}")

    run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
