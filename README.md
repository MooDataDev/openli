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

./etl.sh --country germany
```

## ETL commands

The main ETL entry point is:

```bash
./etl.sh
```

It reads countries from:

```text
etl/config/geofabrik_countries.tsv
```

For each country, it downloads the Geofabrik `.osm.pbf` file into `data/raw/` and then extracts restaurant POIs into `data/processed/`.

Example output paths for snapshot date `2026-06-11`:

```text
data/raw/germany-260611.osm.pbf
data/processed/food_pois_germany_snapshot_20260611.parquet
data/processed/food_pois_germany_snapshot_20260611.summary.json
```

Run all configured countries sequentially:

```bash
./etl.sh
```

Run only one country:

```bash
./etl.sh --country germany
```

Preview what would happen without downloading or extracting anything:

```bash
./etl.sh --dry-run --country germany
```

`--dry-run` prints the planned `curl` download command and the planned Python extraction command. It is useful for checking paths, dates, country selection, and options before starting a large download.

Use a fixed snapshot date:

```bash
./etl.sh --country germany --snapshot-date 2026-06-11
```

Force a new download even if the raw file already exists:

```bash
./etl.sh --country germany --force
```

Extract only the first 100 matching restaurants for a quick test:

```bash
./etl.sh --country germany --max-extract 100
```

Run multiple country jobs in parallel:

```bash
./etl.sh --parallel 3
```

Disable progress bars entirely:

```bash
./etl.sh --country germany --no-progress
```

Keep progress bars but skip the initial `osmium fileinfo -e` percentage estimate:

```bash
./etl.sh --country germany --no-estimate-total
```

`--no-tqdm` is accepted as an alias for `--no-estimate-total`.

Use a custom country list:

```bash
./etl.sh --countries-file etl/config/geofabrik_countries.tsv
```

See [docs/etl.md](docs/etl.md) for details.
