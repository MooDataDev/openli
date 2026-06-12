import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

type CacheEntry = {
  createdAt: number;
  payload: unknown;
};

let cache: CacheEntry | null = null;
const CACHE_TTL_MS = 5 * 60_000;

function pythonBinary() {
  return (
    process.env.OPENLI_PYTHON ??
    path.resolve(process.cwd(), "..", ".venv", "bin", "python")
  );
}

export async function GET() {
  if (cache && Date.now() - cache.createdAt < CACHE_TTL_MS) {
    return Response.json(cache.payload);
  }

  const scriptPath = path.resolve(process.cwd(), "scripts", "read_pois.py");

  try {
    const { stdout } = await execFileAsync(pythonBinary(), [scriptPath], {
      cwd: process.cwd(),
      maxBuffer: 160 * 1024 * 1024,
      timeout: 60_000,
    });
    const payload = JSON.parse(stdout);
    cache = { createdAt: Date.now(), payload };
    return Response.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return Response.json(
      {
        error: "Failed to load local Parquet snapshots.",
        detail: message,
        pois: [],
        countries: [],
        cities: [],
        amenities: [],
        cuisines: [],
      },
      { status: 500 },
    );
  }
}
