import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

type CacheEntry = {
  createdAt: number;
  body: BodyInit;
  headers: HeadersInit;
};

type ApiBody = {
  body: BodyInit;
  headers: HeadersInit;
};

let cache: CacheEntry | null = null;
const CACHE_TTL_MS = 60 * 60_000;

function pythonBinary() {
  return (
    process.env.OPENLI_PYTHON ??
    path.resolve(process.cwd(), "..", ".venv", "bin", "python")
  );
}

function dashboardCachePath(compressed = false) {
  if (compressed) {
    return path.resolve(process.cwd(), "..", "data", "processed", "dashboard_pois_latest.json.gz");
  }
  return path.resolve(process.cwd(), "..", "data", "processed", "dashboard_pois_latest.json");
}

async function readDashboardCache() {
  try {
    const compressed = await readFile(dashboardCachePath(true));
    const body = compressed.buffer.slice(
      compressed.byteOffset,
      compressed.byteOffset + compressed.byteLength,
    ) as ArrayBuffer;
    const headers: HeadersInit = {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Encoding": "gzip",
      "Cache-Control": "public, max-age=3600",
      "X-OpenLI-Data-Source": "dashboard-cache-gzip",
    };
    return {
      body,
      headers,
    };
  } catch {
    const contents = await readFile(dashboardCachePath(), "utf8");
    const headers: HeadersInit = {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
      "X-OpenLI-Data-Source": "dashboard-cache-json",
    };
    return {
      body: contents,
      headers,
    };
  }
}

async function readViaPython() {
  const scriptPath = path.resolve(process.cwd(), "scripts", "read_pois.py");
  const { stdout } = await execFileAsync(pythonBinary(), [scriptPath], {
    cwd: process.cwd(),
    maxBuffer: 100 * 1024 * 1024,
    timeout: 60_000,
  });
  const headers: HeadersInit = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-cache",
    "X-OpenLI-Data-Source": "python-fallback",
  };
  return {
    body: stdout,
    headers,
  };
}

export async function GET() {
  if (cache && Date.now() - cache.createdAt < CACHE_TTL_MS) {
    return new Response(cache.body, { headers: cache.headers });
  }

  try {
    let result: ApiBody;
    try {
      result = await readDashboardCache();
    } catch {
      result = await readViaPython();
    }
    cache = { createdAt: Date.now(), body: result.body, headers: result.headers };
    return new Response(result.body, { headers: result.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return Response.json(
      {
        error: "Failed to load local Parquet snapshots.",
        detail: message,
        pois: [],
        continents: [],
        countries: [],
        cities: [],
        amenities: [],
        cuisines: [],
      },
      { status: 500 },
    );
  }
}
