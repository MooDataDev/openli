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

The dashboard reads all latest Parquet snapshots from the project data folder:

```text
../data/processed/*latest.parquet
```

Generate fresh data from the repository root:

```bash
./etl.sh --parallel 3
```

For a quick development sample:

```bash
./etl.sh --parallel 3 --max-extract 100
```

## Notes

- The app uses local Next.js API routes to read Parquet via the existing Python/pyarrow environment.
- Set `OPENLI_PYTHON=/path/to/python` if `.venv/bin/python` is not available in the repository root.
- MapLibre uses external public dark map tiles.
