# OpenLI - Open Location Intelligence

OpenLI is an MVP for location intelligence and geospatial analytics. The first data product step extracts restaurant POIs from Germany into Parquet files that can later feed analytics, DuckDB/PostGIS workflows, and a dashboard.

## Project structure

```text
openli/
  data/
    raw/                 # local OSM extracts, not committed
    processed/           # generated Parquet outputs, not committed
  docs/
    etl.md               # ETL usage and scaling notes
  etl/
    openli_etl/          # reusable ETL Python package
    scripts/             # command-line entry points
  dashboard/             # future React dashboard
```

## Quick start

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python etl/scripts/extract_food_pois.py \
  --input data/raw/germany-latest.osm.pbf \
  --output data/processed/food_pois_germany_snapshot_20260610.parquet \
  --snapshot-date 2026-06-10
```

See [docs/etl.md](docs/etl.md) for details.
