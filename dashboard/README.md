# OpenLI Restaurant Intelligence Dashboard

Map-first MVP dashboard for local OpenStreetMap restaurant POI snapshots.

## Setup

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Data

The dashboard API first reads the optimized cache:

```text
../data/processed/dashboard_pois_latest.json.gz
```

If the cache is missing, it falls back to reading all latest Parquet snapshots:

```text
../data/processed/*_snapshot_latest.parquet
```

Generate fresh data from the repository root:

```bash
./etl.sh --parallel 3
```

`etl.sh` rebuilds the dashboard cache after extraction. You can also rebuild only the cache:

```bash
.venv/bin/python dashboard/scripts/build_dashboard_cache.py
```

For a quick development sample:

```bash
./etl.sh --parallel 3 --max-extract 100
```

## Notes

- The app uses a local Next.js API route and a precomputed gzip JSON cache for fast startup.
- The Python/pyarrow Parquet reader remains available as a fallback when the cache is missing.
- Set `OPENLI_PYTHON=/path/to/python` if `.venv/bin/python` is not available in the repository root.
- MapLibre uses external public dark map tiles.
