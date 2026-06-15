from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ETL_ROOT = PROJECT_ROOT / "etl"
sys.path.insert(0, str(ETL_ROOT))

from openli_etl.cuisine_normalization import add_cuisine_columns
from openli_etl.geo_normalization import add_continent_column
from openli_etl.osm_food_pois import write_parquet, write_summary, quality_summary, latest_parquet_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add normalized cuisine columns to existing OpenLI Parquet files.")
    parser.add_argument(
        "--input-glob",
        default="data/processed/*_snapshot_latest.parquet",
        help="Glob of Parquet files to update in place.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print files that would be processed without writing changes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = sorted(PROJECT_ROOT.glob(args.input_glob))
    if not files:
        print(f"No files matched: {args.input_glob}", file=sys.stderr)
        return 1

    for path in files:
        print(f"Processing {path.relative_to(PROJECT_ROOT)}")
        if args.dry_run:
            continue

        dataframe = pd.read_parquet(path)
        row_count = len(dataframe)
        enriched = add_continent_column(dataframe, source_path=path)
        enriched = add_cuisine_columns(enriched)
        if len(enriched) != row_count:
            raise RuntimeError(f"Row count changed for {path}: {row_count} -> {len(enriched)}")

        write_parquet(enriched, path, show_progress=False)
        summary_path = path.with_suffix(".summary.json")
        write_summary(quality_summary(enriched), path)

        latest_path = latest_parquet_path(path)
        if latest_path != path:
            write_parquet(enriched, latest_path, show_progress=False)

        print(f"Wrote {path.relative_to(PROJECT_ROOT)} and {summary_path.relative_to(PROJECT_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
