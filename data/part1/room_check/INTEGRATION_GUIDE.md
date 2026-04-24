# Integration Guide — Phase 2 Upgrade

This guide walks through three upgrades to the GridHack 2026 test environment:

1. **Unified runnable** — all five team files integrate into one `main.py`.
2. **Dynamic auto-scoring** — submissions are graded and `teams.score` updates automatically.
3. **Live Inkbird support** — read directly from an IAM-T1 monitor over BLE.

---

## 1. Drop the `room_check/` package into the repo

```
Resilience-Hub-Builder/
└── room_check/              ← NEW
    ├── main.py              # integrated runnable
    ├── inputs.py            # Team 1
    ├── thresholds.json      # Team 2
    ├── room_check.py        # Team 3
    ├── alerts.py            # Team 4
    ├── inkbird.py           # BLE connector (bonus)
    ├── README.md            # Team 5
    ├── sample_data/
    │   └── sensor_log.csv
    └── grading/
        └── auto_grade.py    # auto-scorer
```

Smoke test:

```bash
cd Resilience-Hub-Builder
python room_check/main.py --scenario ventilation_failure
# should print a RED banner, an urgent alert, and a resilience score
```

## 2. Wire dynamic scoring into the API

The existing `POST /api/submissions` stores code but never grades it. Replace the route with the patched version:

```bash
cp api_patches/submissions.ts \
   artifacts/api-server/src/routes/submissions.ts
cp api_patches/inkbird-live.ts \
   artifacts/api-server/src/routes/inkbird-live.ts  # optional
```

Then in `routes/roomcheck.ts` add:

```ts
import { getLiveReading } from "./inkbird-live";
router.get("/live", getLiveReading);
```

Environment variables (add to Replit secrets):

| Var | Default | Purpose |
|---|---|---|
| `GRADER_PATH` | `./room_check/grading/auto_grade.py` | Absolute path to the grader |
| `GRADER_CONFIG` | `./room_check/thresholds.json` | Reference thresholds for Team 3/4 tests |
| `INKBIRD_SCRIPT` | `./room_check/inkbird.py` | Path to the BLE driver |
| `PYTHON_BIN` | `python3` | Which Python to spawn |
| `INKBIRD_SIMULATE` | auto | `1` forces sim, `0` forces real BLE |

Install Python deps in the Replit Nix config:

```nix
pkgs.python311
pkgs.python311Packages.bleak   # for real Inkbird
```

Restart the API. New behavior:

- POST `/api/submissions` → runs grader, stores pass/fail detail in `submissions.feedback`, updates `teams.score` to the **best** grade so far
- POST `/api/submissions/regrade/:id` → re-run grader on an existing submission (judges only)
- GET `/api/submissions/:id` → returns structured `{ passed, failed }` feedback

## 3. Hooking up a real Inkbird IAM-T1

1. Power the monitor on and make sure the Inkbird app can see it (first time only — no pairing needed for BLE advertisements).
2. On the machine running `main.py`, install bleak:
   ```bash
   pip install bleak
   ```
3. Run a scan to confirm:
   ```bash
   python room_check/inkbird.py --scan
   ```
4. Use live mode end-to-end:
   ```bash
   python room_check/main.py --source inkbird --watch --interval 30
   ```

If bleak is missing or no adapter is present, `inkbird.py` falls back to a deterministic simulated device so demos still run. Set `INKBIRD_SIMULATE=0` in production to fail loudly instead.

### Protocol notes

The IAM-T1 broadcasts BLE advertisements with manufacturer data (company IDs `0x0001` / `0x09C7`). The 16-byte payload is little-endian:

| Bytes | Type | Field |
|---|---|---|
| 0–1 | int16 | temperature °C × 100 |
| 2–3 | uint16 | humidity %RH × 100 |
| 4–5 | uint16 | CO₂ ppm |
| 6–7 | uint16 | PM2.5 µg/m³ × 10 |
| 8–9 | uint16 | VOC index |
| 10 | uint8 | battery % |

If your firmware differs, set `INKBIRD_DEBUG=1` to dump raw payloads for reverse engineering.

## 4. Scoring rubric (what the grader checks)

Each team can earn 0–30 points from the auto-grader, judged independently from the Phase-1 rubric.

### Team 1 — `inputs.py` (30 pts)
- `validate_replaces_bad_values` (10) — out-of-range values become `None`
- `csv_reads_last_row` (10) — returns the newest row from a CSV
- `context_flags_after_hours_co2` (10) — elevated CO₂ when building is closed sets `after_hours_flag`

### Team 2 — `thresholds.json` (30 pts)
- `co2_limits_match_ashrae` (5)
- `pm25_limits_match_epa` (5)
- `temp_and_humidity_sane` (5)
- `beps_math_correct` (10) — `gap = latest − target`, `fine_per_year = $500 × 365`
- `phase1_combined_savings` (5) — sum of BAS-1, BAS-2, MECH-1 savings

### Team 3 — `room_check.py` (30 pts)
- `green_when_all_good` (5)
- `red_on_smoke` (5)
- `worst_status_wins` (5)
- `unknown_on_missing` (5)
- `drift_catches_bas1` (10) — flags $37.26/day waste

### Team 4 — `alerts.py` (30 pts)
- `green_alert_is_calm` (5)
- `smoke_alert_says_no_windows` (10) — the hardest one
- `heat_alert_calls_out_vulnerable` (5)
- `resilience_deducts_for_vulnerabilities` (10)

### Team 5 — `README.md` (30 pts)
- `mentions_all_teams` (5)
- `explains_data_flow` (5)
- `mentions_local_backup` (10)
- `explains_library_context` (5)
- `includes_install_instructions` (5)

The leaderboard sum matches what the web UI already shows — nothing to change client-side.

## 5. Demo cheat sheet

```bash
# Phase 2 demo in one minute
python room_check/main.py --scenario smoke_event
# → RED, "Do NOT open windows", resilience drops hard

python room_check/main.py --source csv --file room_check/sample_data/sensor_log.csv
# → YELLOW on CO2, still safe

python room_check/main.py --source inkbird --watch --interval 10 \
   --cloud https://your-replit.repl.co/api/roomcheck/ingest
# → live feed, updates the web dashboard in real time
```
