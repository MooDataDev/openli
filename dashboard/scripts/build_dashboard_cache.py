from __future__ import annotations

import json

from read_pois import CACHE_GZIP_PATH, CACHE_JSON_PATH, read_latest_pois, write_dashboard_cache


def main() -> int:
    payload = read_latest_pois()
    write_dashboard_cache(payload)

    json_size = CACHE_JSON_PATH.stat().st_size
    gzip_size = CACHE_GZIP_PATH.stat().st_size
    print(
        json.dumps(
            {
                "pois": len(payload["pois"]),
                "jsonPath": str(CACHE_JSON_PATH),
                "gzipPath": str(CACHE_GZIP_PATH),
                "jsonBytes": json_size,
                "gzipBytes": gzip_size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
