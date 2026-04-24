# Room Check

Open-source air-quality safety tool for **Montgomery County Library** and other Maryland resilience hubs. Built during GridHack 2026 (bwtech@UMBC, April 24 2026).

Room Check takes raw sensor readings from an Inkbird indoor-air-quality monitor (or any CSV/manual input), evaluates them against real published safety standards (ASHRAE, EPA, OSHA), and tells the librarian in plain language what to do.

---

## Why it exists

The library has 436 daily visitors, no backup generator, R-22 chillers that can't be recharged, AHUs from 1994, and no air purifiers. A $25 sensor can only tell you a number — this project tells you what that number *means* in this specific building and what it's *costing* you in BEPS penalties.

## How it's built — Team 1 through Team 5

All five teams ship files that plug into one runnable script, `main.py`:

| Team | File | Role | What it does |
|---|---|---|---|
| Team 1 | `inputs.py` | The Translator | Reads data (manual / CSV / Inkbird BLE), validates ranges, tags readings with open/closed building context. |
| Team 2 | `thresholds.json` | The Rule Book | Real safety thresholds with citations. BEPS math. Drift rules. Known vulnerabilities. |
| Team 3 | `room_check.py` | The Detective | GREEN/YELLOW/RED decision engine + drift detection (catches BAS-1 weekend waste at $37.26/day). |
| Team 4 | `alerts.py` | The First Responder | Plain-language alerts (smoke → "don't open windows") + Community Resilience Index 0–100. |
| Team 5 | `README.md` + backup logger | The Messenger | This doc + `local_backup.csv` recorder that keeps working when WiFi dies. |

### Data flow / architecture

```
  ┌────────────────┐
  │ Inkbird IAM-T1 │──BLE──▶  inkbird.py ──┐
  └────────────────┘                        │
  ┌────────────────┐                        ├─▶ inputs.py ──▶ validate ──▶ add_context
  │ CSV / manual   │──────────────────────▶─┘                                   │
  └────────────────┘                                                             ▼
                                                                     thresholds.json (Team 2)
                                                                               │
                                                                               ▼
                                                             room_check.py (evaluate + drift)
                                                                               │
                                                                               ▼
                                                             alerts.py (message + resilience)
                                                                               │
                                         ┌─────────────────────────────────────┤
                                         ▼                                     ▼
                          POST /api/roomcheck/live              local_backup.csv   ◀── offline-safe
                          (EcoGuard cloud dashboard)            (keeps logging if WiFi dies)
```

## Getting started

```bash
# Optional: install the Inkbird BLE driver (skip to use CSV/manual only)
pip install bleak

# Run with a canned scenario (no hardware)
python main.py --scenario ventilation_failure

# Run with a CSV log
python main.py --source csv --file sample_data/sensor_log.csv

# Run with a live Inkbird, fall back to CSV if the monitor isn't visible
python main.py --source inkbird --fallback csv --file sample_data/sensor_log.csv

# Run continuously, pushing to the EcoGuard dashboard
export ROOMCHECK_CLOUD_URL=https://your-replit-url/api/roomcheck/ingest
python main.py --source inkbird --watch --interval 30 --cloud "$ROOMCHECK_CLOUD_URL"
```

Exit code encodes the status: `0` GREEN, `1` YELLOW, `2` RED, `3` UNKNOWN — useful for CI or a Grafana check.

## Local backup (offline-safe)

Every run appends one row to `local_backup.csv`. During a power outage, WiFi goes down first — but a laptop on battery and a USB-powered Inkbird will keep running and the CSV will keep growing. When power comes back, a single `scp` proves the building was monitored the whole time.

## Dynamic scoring (judges)

Submissions are auto-graded by `grading/auto_grade.py`. Each team can score up to 30 points; the API keeps the team's best-ever score so students can iterate.

```bash
# Grade one file manually
python grading/auto_grade.py --team 3 --file student_submission.py --json
```

Wire into the server by swapping in `api_patches/submissions.ts` for `artifacts/api-server/src/routes/submissions.ts`. Every POST /api/submissions now runs the grader and updates `teams.score` automatically.

## License

MIT. Use it, remix it, ship it to your county.
