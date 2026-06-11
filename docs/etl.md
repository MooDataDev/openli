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

Run the full download and extraction workflow:

```bash
./etl.sh
```

Countries are configured in:

```text
etl/config/geofabrik_countries.tsv
```

The script downloads raw PBF files to `data/raw/` using compact snapshot dates:

```text
data/raw/germany-260610.osm.pbf
```

It then writes processed Parquet files to `data/processed/`:

```text
data/processed/food_pois_germany_snapshot_20260610.parquet
data/processed/food_pois_germany_snapshot_latest.parquet
```

Run only one country:

```bash
./etl.sh --country germany
```

Force a re-download even if the raw file already exists:

```bash
./etl.sh --country germany --force
```

Run multiple country jobs in parallel:

```bash
./etl.sh --parallel 3
```

Preview the commands without downloading or extracting:

```bash
./etl.sh --dry-run --country germany --max-extract 100
```

Use a custom countries file:

```bash
./etl.sh --countries-file etl/config/geofabrik_countries.tsv
```

## Direct Python Usage

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

Limit extraction for quick tests:

```bash
.venv/bin/python etl/scripts/extract_food_pois.py \
  --input data/raw/germany-latest.osm.pbf \
  --output data/processed/food_pois_germany_sample_100.parquet \
  --snapshot-date 2026-06-10 \
  --max-extract 100
```

`--max_extract 100` is also accepted. If the option is omitted, all matching POIs are extracted.

Progress bars are enabled by default:

```text
Reading OSM objects  12%|...| 61.2M/506M [08:33, 119kobj/s, matches=2,431]
Writing Parquet    100%|...
Writing summary    100%|...
```

By default, the ETL runs `osmium fileinfo -e` first to estimate the total number of OSM objects. This enables a percentage-based reading progress bar.

Skip the estimate and keep the open-ended progress bar:

```bash
.venv/bin/python etl/scripts/extract_food_pois.py \
  --input data/raw/germany-latest.osm.pbf \
  --output data/processed/food_pois_germany_snapshot_20260610.parquet \
  --snapshot-date 2026-06-10 \
  --no-estimate-total
```

`--no-estimate-total` is also accepted and is the clearer option name.

Disable progress bars entirely for non-interactive runs:

```bash
.venv/bin/python etl/scripts/extract_food_pois.py \
  --input data/raw/germany-latest.osm.pbf \
  --output data/processed/food_pois_germany_snapshot_20260610.parquet \
  --snapshot-date 2026-06-10 \
  --no-progress
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

For convenience, each run also writes a `snapshot_latest.parquet` copy next to the dated snapshot. Use dated files for historical comparisons and `latest` for dashboards or notebooks that should always read the newest run.

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
