# Restaurant POI ETL

This ETL extracts restaurant POIs from a Germany OpenStreetMap `.osm.pbf` snapshot and writes a Parquet file for analytics.

## Installation

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Input

Download a Germany `.osm.pbf` extract, for example from Geofabrik, and place it under `data/raw/`:

```text
data/raw/germany-latest.osm.pbf
```

Large raw data files should stay out of Git.

## Usage

```bash
.venv/bin/python etl/scripts/extract_food_pois.py \
  --input data/raw/germany-latest.osm.pbf \
  --output data/processed/food_pois_germany_snapshot_20260610.parquet \
  --snapshot-date 2026-06-10
```

The MVP defaults to:

```text
amenity=restaurant
```

You can pass categories explicitly:

```bash
.venv/bin/python etl/scripts/extract_food_pois.py \
  --input data/raw/germany-latest.osm.pbf \
  --output data/processed/food_pois_germany_snapshot_20260610.parquet \
  --snapshot-date 2026-06-10 \
  --categories restaurant
```

## Output

The Parquet output contains stable columns for snapshot comparison:

- `osm_id`, `osm_type`
- name and restaurant tags such as `name`, `amenity`, `cuisine`, `brand`, `operator`
- website, menu, phone, email, address, access, and seating fields
- `lat`, `lon`
- `geometry`, a WKB geometry column in EPSG:4326
- `source_file`, `extraction_timestamp`, `snapshot_date`

A JSON summary is written next to the Parquet file with counts and data quality metrics.

## Scaling notes

For larger countries or repeated scheduled snapshots:

- Keep raw OSM snapshots immutable and partition processed outputs by `snapshot_date`.
- Use DuckDB for local analysis directly on Parquet:

```sql
SELECT snapshot_date, cuisine, COUNT(*)
FROM 'data/processed/food_pois_germany_snapshot_*.parquet'
WHERE amenity = 'restaurant'
GROUP BY snapshot_date, cuisine;
```

- Use PostGIS when you need spatial joins against districts, neighborhoods, or custom polygons at serving time.
- Store `geometry` as WKB in Parquet and import with `ST_GeomFromWKB`.
- Add administrative boundary enrichment as a separate ETL step so restaurant extraction remains simple and reproducible.
