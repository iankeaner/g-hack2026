/**
 * Optional API route: GET /api/roomcheck/live
 *
 * Shells out to the Inkbird driver to return the freshest reading
 * from whichever monitor is physically near the server. Wire this
 * into `artifacts/api-server/src/routes/roomcheck.ts` next to the
 * /simulate route if you want the web UI to show live data.
 *
 * Expects `room_check/inkbird.py` to be on disk at GRADER-adjacent path.
 */

import { spawn } from "node:child_process";
import { join } from "node:path";
import type { Request, Response } from "express";

const INKBIRD = process.env.INKBIRD_SCRIPT ??
  join(process.cwd(), "room_check", "inkbird.py");
const PYTHON = process.env.PYTHON_BIN ?? "python3";

export async function getLiveReading(_req: Request, res: Response) {
  const proc = spawn(PYTHON, [INKBIRD], { stdio: ["ignore", "pipe", "pipe"] });

  let stdout = "";
  let stderr = "";
  proc.stdout.on("data", (d) => (stdout += d));
  proc.stderr.on("data", (d) => (stderr += d));

  const timeout = setTimeout(() => proc.kill("SIGKILL"), 10_000);

  proc.on("close", (code) => {
    clearTimeout(timeout);
    if (code !== 0) {
      return res.status(502).json({ error: "Inkbird unreachable", stderr });
    }
    try {
      const reading = JSON.parse(stdout);
      res.json(reading);
    } catch {
      res.status(502).json({ error: "Malformed Inkbird output", stdout });
    }
  });
}

// ── Wire it up in routes/roomcheck.ts ──
// import { getLiveReading } from "./inkbird-live";
// router.get("/live", getLiveReading);
