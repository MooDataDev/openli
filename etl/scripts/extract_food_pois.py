from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ETL_ROOT = PROJECT_ROOT / "etl"
sys.path.insert(0, str(ETL_ROOT))

from openli_etl.osm_food_pois import main


if __name__ == "__main__":
    raise SystemExit(main())
